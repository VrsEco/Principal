import json
import re
import unicodedata
import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_, func

from models import db
from models.agent_menu import AgentMenuOption, AgentMenuSession
from src.intelligence.workflows.company_selection import (
    COMPANY_SELECTION_ROUTE_ADVANCE,
    COMPANY_SELECTION_ROUTE_PROMPT,
    OperationCompanySelectionCoordinator,
)
from src.intelligence.workflows.confidence import (
    DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS,
    DISCOVERY_CONFIDENCE_ROUTE_NO_MATCH,
    DISCOVERY_CONFIDENCE_ROUTE_SELECT,
    WorkflowDiscoveryConfidencePolicy,
)
from src.intelligence.workflows.confirmation import (
    CONFIRMATION_ROUTE_CANCELLED,
    CONFIRMATION_ROUTE_DIRECT_RESPONSE,
    CONFIRMATION_ROUTE_EXECUTION_PROMPT,
    ConfirmationCoordinator,
)
from src.intelligence.workflows.direct_execution import (
    DirectExecutionDispatcher,
    DirectExecutionRequest,
    DirectExecutionResult,
    build_handler_executor,
)
from src.intelligence.workflows.policy import WorkflowApprovalPolicyGuard
from src.intelligence.workflows.field_collection import (
    FIELD_COLLECTION_ROUTE_PROMPT_MISSING,
    FieldCollectionCoordinator,
    adjust_required_fields_for_context as adjust_workflow_required_fields_for_context,
    extract_numbered_fields_from_text as extract_workflow_numbered_fields_from_text,
    missing_required_fields as find_workflow_missing_required_fields,
)
from src.intelligence.workflows.handlers import (
    AgentActionListPendingExecutionHandler,
    AgentActionListPendingRequest,
    AgentActionOperationExecutionHandler,
    AgentActionOperationRequest,
    CollaboratorOccupancyExecutionHandler,
    CollaboratorOccupancyRequest,
    CompanyAccessExecutionHandler,
    CompanyAccessExecutionRequest,
    FinancialReceiptIngestExecutionHandler,
    FinancialReceiptIngestRequest,
    MeetingCloseExecutionHandler,
    MeetingCloseRequest,
    MeetingScheduleExecutionHandler,
    MeetingScheduleRequest,
    MeetingSendSummaryEmailExecutionHandler,
    MeetingSendSummaryEmailRequest,
    MeetingSendSummaryWhatsAppExecutionHandler,
    MeetingSendSummaryWhatsAppRequest,
    MeetingStartExecutionHandler,
    MeetingStartRequest,
    MeetingSummarizeExecutionHandler,
    MeetingSummarizeRequest,
    MyWorkExecutionHandler,
    MyWorkExecutionRequest,
    OnboardingDiagnoseExecutionHandler,
    OnboardingDiagnoseRequest,
    OnboardingGoLiveCheckExecutionHandler,
    OnboardingGoLiveCheckRequest,
    OnboardingStartExecutionHandler,
    OnboardingStartRequest,
    OnboardingStatusExecutionHandler,
    OnboardingStatusRequest,
    ProcessInstanceCompleteExecutionHandler,
    ProcessInstanceCompleteRequest,
    ProjectTaskAuditExecutionHandler,
    ProjectTaskAuditRequest,
    ProjectTaskCompleteExecutionHandler,
    ProjectTaskCompleteRequest,
    ProjectTaskCreateExecutionHandler,
    ProjectTaskCreateRequest,
    ProjectTaskUpdateExecutionHandler,
    ProjectTaskUpdateRequest,
    RoutineConsultExecutionHandler,
    RoutineConsultExecutionRequest,
    SummaryExecutionRequest,
    SummaryWorkflowExecutionHandler,
)
from src.intelligence.workflows.presenters import (
    WorkflowDisplayOption,
    build_collaborator_occupancy_report,
    build_my_work_report,
    build_confirmation_display_items,
    build_confirmation_text,
    build_workflow_selection_confirmation,
    build_item_selection_prompt,
    build_missing_fields_prompt,
    build_operation_company_prompt,
    build_recovery_message,
    build_root_menu_message,
    build_submenu_message,
    build_ambiguous_options_message,
    describe_my_work_period,
    get_bullet_style,
    group_my_work_by_company,
    resolve_my_work_collaborator_label,
    sanitize_for_channel,
    build_summary_collaborator_prompt,
    build_summary_company_prompt,
    build_summary_period_prompt,
    build_summary_status_prompt,
)
from src.intelligence.workflows.runtime import WorkflowRuntime
from src.intelligence.workflows.schemas import WorkflowRequiredField
from src.intelligence.workflows.selection import (
    SELECTION_ROUTE_ADVANCE,
    SELECTION_ROUTE_CONFIRM,
    AssistedSelectionCoordinator,
    build_assisted_selection_payload,
)
from src.intelligence.workflows.session import WorkflowSessionState
from src.intelligence.workflows.session_runtime import (
    SessionNavigationRuntime,
    SessionPromptRenderer,
    build_session_snapshot as build_workflow_session_snapshot,
    extract_navigation_stack as extract_workflow_navigation_stack,
    payload_without_navigation as workflow_payload_without_navigation,
)
from src.intelligence.workflows.summary import (
    SUMMARY_ACTION_PERIOD_MAP,
    SUMMARY_ROUTE_COMPLETED,
    SUMMARY_ROUTE_PROMPT_COLLABORATOR,
    SUMMARY_ROUTE_PROMPT_COMPANY,
    SUMMARY_ROUTE_PROMPT_DATES,
    SUMMARY_ROUTE_PROMPT_STATUS,
    SUMMARY_ROUTE_EMAIL_CONFIRMATION,
    SUMMARY_ROUTE_ERROR,
    SUMMARY_ROUTE_RESET,
    SUMMARY_STATUS_AWAITING_DATES,
    SUMMARY_WIZARD_STATUSES,
    SummaryWorkflowCoordinator,
)
from src.intelligence.workflows.telemetry import (
    attach_confidence_decision_to_trace,
    build_explicit_workflow_trace,
    build_workflow_discovery_trace,
)

logger = logging.getLogger(__name__)


@dataclass
class MenuInterceptResult:
    handled: bool = False
    response_text: Optional[str] = None
    override_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _merge_menu_metadata(
    base_metadata: Optional[Dict[str, Any]],
    extra_metadata: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    merged = dict(base_metadata or {})
    extra = dict(extra_metadata or {})
    if not extra:
        return merged or None

    merged_menu = dict(merged.get("menu_engine") or {})
    merged_menu.update(dict(extra.get("menu_engine") or {}))
    if merged_menu:
        merged["menu_engine"] = merged_menu

    for key, value in extra.items():
        if key == "menu_engine":
            continue
        merged[key] = value
    return merged or None


def _build_menu_intercept_metadata(
    *,
    session: Optional[AgentMenuSession],
    option: Optional[AgentMenuOption],
    intercept_stage: Optional[str],
    discovery_trace: Optional[Dict[str, Any]] = None,
    handled: bool = True,
) -> Dict[str, Any]:
    selected_option = option or getattr(session, "selected_option", None)
    menu_engine_metadata: Dict[str, Any] = {
        "handled": bool(handled),
        "intercept_stage": str(intercept_stage or getattr(session, "status", "idle") or "idle"),
        "session_status": str(getattr(session, "status", "idle") or "idle"),
    }
    if session is not None:
        menu_engine_metadata["channel"] = str(getattr(session, "channel", "") or "")
        menu_engine_metadata["thread_id"] = str(getattr(session, "thread_id", "") or "")
        menu_engine_metadata["user_id"] = int(getattr(session, "user_id", 0) or 0)
        if getattr(session, "company_id", None) is not None:
            menu_engine_metadata["company_id"] = int(session.company_id)

    if selected_option is not None:
        menu_engine_metadata["selected_option_code"] = str(selected_option.code or "").strip()
        menu_engine_metadata["selected_action_key"] = str(selected_option.action_key or "").strip()

    metadata: Dict[str, Any] = {"menu_engine": menu_engine_metadata}
    if discovery_trace:
        metadata["workflow_discovery"] = dict(discovery_trace)
    return metadata


def _attach_menu_intercept_metadata(
    result: MenuInterceptResult,
    *,
    session: Optional[AgentMenuSession],
    option: Optional[AgentMenuOption],
    intercept_stage: Optional[str],
    discovery_trace: Optional[Dict[str, Any]] = None,
) -> MenuInterceptResult:
    result.metadata = _merge_menu_metadata(
        result.metadata,
        _build_menu_intercept_metadata(
            session=session,
            option=option,
            intercept_stage=intercept_stage,
            discovery_trace=discovery_trace,
        ),
    )
    return result


def _safe_selected_option(session: Any) -> Optional[AgentMenuOption]:
    return getattr(session, "selected_option", None)


MENU_WORDS = ("menu", "opcao", "opção", "opcoes", "opções", "fluxo")
CONFIRM_WORDS = {"sim", "confirmo", "ok", "pode", "confirmar"}
BACK_WORDS = {"voltar", "volta", "retornar", "retorna", "anterior"}
CANCEL_WORDS = {
    "nao",
    "não",
    "cancelar",
    "cancela",
    "parar",
    "fim",
    "finalizar",
    "finaliza",
    "encerrar",
    "encerra",
    "sair",
}
EXECUTE_HINTS = ("executar", "fazer", "iniciar", "finalizar", "cadastrar", "editar")
COMMAND_HINTS = ("cadastrar", "criar", "iniciar", "finalizar", "editar", "executar", "resumo", "aprovar", "aprovado", "rejeitar", "revalidar", "colocar", "mudar")
COMMAND_QUERY_HINTS = (
    "liste",
    "quantas",
    "quantos",
    "quais",
    "qual",
    "me informe",
    "informe",
    "me traga",
    "traga",
    "quero saber",
    "gostaria de saber",
    "me diga",
    "listar",
    "lista",
    "analise",
    "analisar",
    "mostrar",
    "mostra",
    "ver",
    "consultar",
    "consulta",
)
COMMAND_SCOPE_HINTS = (
    "projeto",
    "atividade",
    "atividades",
    "tarefa",
    "tarefas",
    "processo",
    "processos",
    "instancia",
    "instancias",
    "instância",
    "instâncias",
    "resumo",
    "relatorio",
    "relatório",
    "colaborador",
    "colaboradores",
    "usuario",
    "usuário",
    "responsavel",
    "responsável",
    "empresa",
    "empresas",
    "solicitacao",
    "solicitação",
    "aprovacao",
    "aprovação",
    "acoes",
    "ações",
    "decisao",
    "decisão",
    "ticket",
    "prazo",
    "dia",
    "ocupacao",
    "ocupação",
    "capacidade",
    "carga",
    "auditoria",
)
COMMAND_STATUS_HINTS = (
    "aberto",
    "abertos",
    "aberta",
    "abertas",
    "pendente",
    "pendentes",
    "vencido",
    "vencidos",
    "vencida",
    "vencidas",
    "atrasado",
    "atrasados",
    "atrasada",
    "atrasadas",
    "hoje",
    "semana",
    "mes",
    "mês",
)
GREETING_ONLY_PHRASES = {
    "oi",
    "ola",
    "ola sapiens",
    "bom dia",
    "boa tarde",
    "boa noite",
    "e ai",
    "fala",
    "opa",
}
COMPANY_ALIAS_PATTERN = re.compile(r"^\s*([A-Za-z]{2,5})(?:\s*-\s*(.+))?\s*$")
SUMMARY_ACTION_PERIOD = dict(SUMMARY_ACTION_PERIOD_MAP)
SUMMARY_EMAIL_CONFIRM_STATUS = "awaiting_summary_email_confirmation"
SUMMARY_EMAIL_CUSTOM_STATUS = "awaiting_summary_email_custom"
CONTEXT_DISAMBIGUATION_STATUS = "awaiting_context_disambiguation"
COMPANY_SELECTION_STATUS = "awaiting_operation_company"
ADDITIONAL_FIELDS_STATUS = "awaiting_additional_fields"
SUMMARY_SELECTION_STATUSES = SUMMARY_WIZARD_STATUSES | {
    SUMMARY_EMAIL_CONFIRM_STATUS,
    SUMMARY_EMAIL_CUSTOM_STATUS,
}
SUMMARY_EMAIL_OFFER_SUFFIX = (
    "Quer que eu te envie este relatorio por e-mail?\n"
    "1 - Enviar para meu e-mail cadastrado\n"
    "2 - Informar outro e-mail\n"
    "Responda com 1, 2 ou nao."
)
CONTEXT_DISAMBIGUATION_PROMPT = (
    "Nao consegui ter certeza se voce quer continuar o fluxo anterior ou iniciar um novo pedido.\n"
    "Responda:\n"
    "1 - Nova conversa\n"
    "2 - Continuar a atual"
)


def _build_session_prompt_renderer() -> SessionPromptRenderer:
    return SessionPromptRenderer(
        render_root_menu=_format_root_menu,
        public_payload=_public_payload,
        render_confirmation=_format_confirmation,
        render_missing_fields=_format_missing_fields,
        render_item_selection=_format_item_selection_prompt,
        render_operation_company=_format_operation_company_prompt,
        render_summary_period=_format_summary_period_prompt,
        render_summary_company=_format_summary_company_prompt,
        render_summary_collaborator=_format_summary_collaborator_prompt,
        render_summary_status=_format_summary_status_prompt,
        summary_status_choices=_summary_status_choices,
        company_selection_status=COMPANY_SELECTION_STATUS,
        summary_email_confirm_status=SUMMARY_EMAIL_CONFIRM_STATUS,
        summary_email_custom_status=SUMMARY_EMAIL_CUSTOM_STATUS,
        summary_email_offer_suffix=SUMMARY_EMAIL_OFFER_SUFFIX,
    )


def _build_session_navigation_runtime() -> SessionNavigationRuntime:
    return SessionNavigationRuntime(
        commit_session=lambda: db.session.commit(),
        reset_session=_reset_session,
        prompt_renderer=_build_session_prompt_renderer(),
    )


def _build_workflow_discovery_confidence_policy() -> WorkflowDiscoveryConfidencePolicy:
    return WorkflowDiscoveryConfidencePolicy()


def handle_menu_message(
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
    message: str,
) -> MenuInterceptResult:
    """
    Pré-processa mensagens para menu/sumário de ações persistido em banco.
    """
    text = (message or "").strip()
    if not text:
        return MenuInterceptResult()

    lower = _normalize_text(text)
    first_word = lower.split(" ")[0] if lower else ""

    try:
        _ensure_default_menu_seed()
        session = _get_or_create_session(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
        )

        explicit_code = _extract_explicit_code(text, lower)
        if session.status == CONTEXT_DISAMBIGUATION_STATUS and _is_context_disambiguation_reply(text, lower):
            explicit_code = None
        is_item_selection_reply = (
            session.status == "awaiting_item_selection"
            and _parse_selection_number_date(text) is not None
        )
        is_company_selection_reply = (
            session.status == COMPANY_SELECTION_STATUS
            and _parse_selection_number_date(text) is not None
        )
        is_summary_selection_reply = (
            session.status in SUMMARY_SELECTION_STATUSES
            and _parse_selection_number_date(text) is not None
        )
        is_missing_fields_reply = (
            session.status in {"awaiting_fields", ADDITIONAL_FIELDS_STATUS}
            and bool(
                _extract_numbered_fields_from_text(text, session.missing_fields or [])
                or _extract_fields_from_text(text)
                or _normalize_text(text) in {"pular", "prosseguir", "continuar", "seguir"}
            )
        )
        is_confirmation_adjustment_reply = (
            session.status == "awaiting_confirmation"
            and bool(_extract_fields_from_text(text))
        )

        should_prompt_context_disambiguation = _should_prompt_context_disambiguation(
            session,
            text=text,
            lower=lower,
            explicit_code=explicit_code,
            is_item_selection_reply=is_item_selection_reply,
            is_company_selection_reply=is_company_selection_reply,
            is_summary_selection_reply=is_summary_selection_reply,
            is_missing_fields_reply=is_missing_fields_reply,
            is_confirmation_adjustment_reply=is_confirmation_adjustment_reply,
        )

        # Se o usuário acionar explicitamente o menu/código, reinicia o estado pendente.
        if session.status != "idle" and not should_prompt_context_disambiguation and not (
            is_item_selection_reply
            or is_company_selection_reply
            or is_summary_selection_reply
            or is_missing_fields_reply
            or is_confirmation_adjustment_reply
        ) and (_is_menu_request(lower) or explicit_code):
            _reset_session(session)

        selected_option = _safe_selected_option(session)

        if first_word in BACK_WORDS:
            return _attach_menu_intercept_metadata(
                _handle_back_navigation(session),
                session=session,
                option=selected_option,
                intercept_stage="back_navigation",
            )

        if session.status == CONTEXT_DISAMBIGUATION_STATUS:
            return _attach_menu_intercept_metadata(
                _handle_context_disambiguation_state(
                    session=session,
                    text=text,
                    lower=lower,
                    user_id=user_id,
                    company_id=company_id,
                    channel=channel,
                    thread_id=thread_id,
                ),
                session=session,
                option=selected_option,
                intercept_stage=CONTEXT_DISAMBIGUATION_STATUS,
            )

        if should_prompt_context_disambiguation:
            return _attach_menu_intercept_metadata(
                _prepare_context_disambiguation(session=session, pending_message=text),
                session=session,
                option=selected_option,
                intercept_stage=CONTEXT_DISAMBIGUATION_STATUS,
            )

        if (
            session.status == "idle"
            and not explicit_code
            and _is_greeting_only_message(lower)
        ):
            return _attach_menu_intercept_metadata(
                MenuInterceptResult(
                    handled=True,
                    response_text=_build_greeting_only_message(session.user_id),
                ),
                session=session,
                option=None,
                intercept_stage="greeting_only",
            )

        if session.status == "awaiting_confirmation":
            return _attach_menu_intercept_metadata(
                _handle_confirmation_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage="awaiting_confirmation",
            )

        if session.status == "awaiting_item_selection":
            return _attach_menu_intercept_metadata(
                _handle_item_selection_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage="awaiting_item_selection",
            )

        if session.status == "awaiting_fields":
            return _attach_menu_intercept_metadata(
                _handle_missing_fields_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage="awaiting_fields",
            )

        if session.status == ADDITIONAL_FIELDS_STATUS:
            return _attach_menu_intercept_metadata(
                _handle_additional_fields_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage=ADDITIONAL_FIELDS_STATUS,
            )

        if session.status == COMPANY_SELECTION_STATUS:
            return _attach_menu_intercept_metadata(
                _handle_operation_company_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage=COMPANY_SELECTION_STATUS,
            )

        if session.status == SUMMARY_EMAIL_CONFIRM_STATUS:
            return _attach_menu_intercept_metadata(
                _handle_summary_email_confirmation_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage=SUMMARY_EMAIL_CONFIRM_STATUS,
            )

        if session.status == SUMMARY_EMAIL_CUSTOM_STATUS:
            return _attach_menu_intercept_metadata(
                _handle_summary_email_custom_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage=SUMMARY_EMAIL_CUSTOM_STATUS,
            )

        if session.status in SUMMARY_WIZARD_STATUSES:
            return _attach_menu_intercept_metadata(
                _handle_summary_wizard_state(session, text, lower),
                session=session,
                option=selected_option,
                intercept_stage=session.status,
            )

        if explicit_code:
            option = _find_option_by_code(company_id, explicit_code)
            if not option:
                return _attach_menu_intercept_metadata(
                    MenuInterceptResult(
                        handled=True,
                        response_text=(
                            f"Nao encontrei o codigo de menu '{explicit_code}'.\n\n"
                            f"{_format_root_menu(company_id)}"
                        ),
                    ),
                    session=session,
                    option=None,
                    intercept_stage="explicit_code_not_found",
                    discovery_trace={
                        "strategy": "explicit_code",
                        "explicit_code": explicit_code,
                        "candidate_count": 0,
                    },
                )
            return _attach_menu_intercept_metadata(
                _prepare_option_flow(session, option, text, lower),
                session=session,
                option=option,
                intercept_stage="explicit_code",
                discovery_trace=build_explicit_workflow_trace(option, explicit_code=explicit_code),
            )

        if _is_menu_request(lower):
            return _attach_menu_intercept_metadata(
                MenuInterceptResult(
                    handled=True,
                    response_text=_format_root_menu(company_id),
                ),
                session=session,
                option=None,
                intercept_stage="root_menu",
            )

        # Fallback de ambiguidade em modo comando: somente quando parece ação operacional.
        if _looks_like_command(lower):
            candidates, discovery_trace = _discover_options_by_keywords(
                company_id,
                lower,
                channel=channel,
            )
            confidence_decision = _build_workflow_discovery_confidence_policy().decide(
                discovery_trace.get("top_matches") or []
            )
            discovery_trace = attach_confidence_decision_to_trace(
                discovery_trace,
                confidence_decision,
            )
            candidates_by_code = {
                str(candidate.code or "").strip(): candidate
                for candidate in candidates
            }
            if confidence_decision.route == DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS:
                ambiguous_candidates = [
                    candidates_by_code[code]
                    for code in confidence_decision.candidate_codes
                    if code in candidates_by_code
                ] or candidates
                logger.info(
                    "MENU DISCOVERY AMBIGUO: user=%s company=%s channel=%s thread=%s selected=%s",
                    user_id,
                    company_id,
                    channel,
                    thread_id,
                    json.dumps(discovery_trace, ensure_ascii=False),
                )
                return _attach_menu_intercept_metadata(
                    MenuInterceptResult(
                        handled=True,
                        response_text=_format_ambiguous_options(ambiguous_candidates),
                    ),
                    session=session,
                    option=None,
                    intercept_stage="implicit_discovery_ambiguous",
                    discovery_trace=discovery_trace,
                )
            if confidence_decision.route == DISCOVERY_CONFIDENCE_ROUTE_SELECT:
                selected_candidate = candidates_by_code.get(
                    confidence_decision.selected_code or ""
                ) or (candidates[0] if candidates else None)
                if selected_candidate is None:
                    return MenuInterceptResult()
                logger.info(
                    "MENU DISCOVERY SELECIONADO: user=%s company=%s channel=%s thread=%s selected=%s",
                    user_id,
                    company_id,
                    channel,
                    thread_id,
                    json.dumps(discovery_trace, ensure_ascii=False),
                )
                return _attach_menu_intercept_metadata(
                    _prepare_option_flow(session, selected_candidate, text, lower),
                    session=session,
                    option=selected_candidate,
                    intercept_stage="implicit_discovery_selected",
                    discovery_trace=discovery_trace,
                )

            if confidence_decision.route == DISCOVERY_CONFIDENCE_ROUTE_NO_MATCH or not candidates:
                logger.info(
                    "MENU DISCOVERY SEM MATCH: user=%s company=%s channel=%s thread=%s selected=%s",
                    user_id,
                    company_id,
                    channel,
                    thread_id,
                    json.dumps(discovery_trace, ensure_ascii=False),
                )
                return MenuInterceptResult(
                    handled=False,
                    metadata=_build_menu_intercept_metadata(
                        session=session,
                        option=None,
                        intercept_stage="implicit_discovery_no_match",
                        discovery_trace=discovery_trace,
                        handled=False,
                    ),
                )

    except Exception as exc:
        db.session.rollback()
        logger.exception("Falha no menu engine: %s", exc)
        return MenuInterceptResult()

    return MenuInterceptResult()


def _handle_back_navigation(session: AgentMenuSession) -> MenuInterceptResult:
    result = _build_session_navigation_runtime().handle_back_navigation(session)
    return MenuInterceptResult(
        handled=True,
        response_text=result.response_text,
    )


def start_channel_workflow(
    *,
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
    workflow_code: str,
    payload: Optional[Dict[str, Any]] = None,
    user_message: Optional[str] = None,
) -> MenuInterceptResult:
    try:
        _ensure_default_menu_seed()
        session = _get_or_create_session(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
        )
        option = _find_option_by_code(company_id, str(workflow_code or "").strip())
        if option is None:
            return MenuInterceptResult(
                handled=True,
                response_text=f"Fluxo {workflow_code} não encontrado na árvore oficial do Sapiens.",
            )

        session.selected_option_id = option.id
        session.last_user_message = str(user_message or "").strip() or f"workflow:{workflow_code}"
        session.status = "idle"
        session.collected_data = {}
        session.missing_fields = []
        db.session.commit()

        collected = dict(payload or {})
        company_selection_flow = _prepare_company_selection_flow_if_needed(
            session=session,
            option=option,
            collected=collected,
        )
        if company_selection_flow is not None:
            return _attach_menu_intercept_metadata(
                company_selection_flow,
                session=session,
                option=option,
                intercept_stage=COMPANY_SELECTION_STATUS,
            )

        return _attach_menu_intercept_metadata(
            _advance_option_after_payload_collection(
                session=session,
                option=option,
                payload=collected,
            ),
            session=session,
            option=option,
            intercept_stage="workflow_start",
        )
    except Exception:
        logger.exception("Erro ao iniciar fluxo de canal %s", workflow_code)
        return MenuInterceptResult(
            handled=True,
            response_text="Nao consegui iniciar o fluxo solicitado agora. Tente novamente em seguida.",
        )


def list_menu_options(
    company_id: Optional[int],
    parent_code: Optional[str] = None,
    include_inactive: bool = False,
    include_global: bool = True,
) -> List[AgentMenuOption]:
    query = AgentMenuOption.query
    if not include_inactive:
        query = query.filter(AgentMenuOption.is_active.is_(True))

    if include_global and company_id:
        query = query.filter(
            or_(
                AgentMenuOption.company_id == company_id,
                AgentMenuOption.company_id.is_(None),
            )
        )
    elif company_id:
        query = query.filter(AgentMenuOption.company_id == company_id)
    else:
        query = query.filter(AgentMenuOption.company_id.is_(None))

    if parent_code:
        parent = _find_option_by_code(company_id, parent_code, include_inactive=include_inactive)
        if not parent:
            return []
        query = query.filter(AgentMenuOption.parent_id == parent.id)
    else:
        query = query.filter(AgentMenuOption.parent_id.is_(None))

    options = query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all()
    return _dedupe_by_code(options, company_id)


def _prepare_option_flow(
    session: AgentMenuSession,
    option: AgentMenuOption,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    children = _list_children(session.company_id, option.id)
    if children and not _indicates_execute(lower):
        return MenuInterceptResult(
            handled=True,
            response_text=_format_submenu(option, children),
        )

    collected = _extract_fields_from_text(text)
    session.selected_option_id = option.id
    session.last_user_message = text
    payload = _inject_session_context_into_payload(
        session=session,
        option=option,
        payload=collected,
    )
    company_selection_flow = _prepare_company_selection_flow_if_needed(
        session=session,
        option=option,
        collected=payload,
    )
    if company_selection_flow is not None:
        return company_selection_flow
    _transition_session_state(
        session=session,
        status="awaiting_confirmation",
        payload=payload,
        missing_fields=[],
    )
    return MenuInterceptResult(
        handled=True,
        response_text=_format_workflow_selection_confirmation(option, session, payload, session.channel or "web"),
    )


def _handle_confirmation_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    payload = _inject_session_context_into_payload(
        session=session,
        option=option,
        payload=dict(session.collected_data or {}),
    )
    first_word = str(lower or "").split(" ")[0].strip(".,;:!?")

    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Acao cancelada. Digite 'menu' para retomar.",
        )

    if first_word in CONFIRM_WORDS:
        collected = dict(payload or {})

        company_selection_flow = _prepare_company_selection_flow_if_needed(
            session=session,
            option=option,
            collected=collected,
        )
        if company_selection_flow is not None:
            return company_selection_flow

        selection_flow = _prepare_selection_flow_if_applicable(
            session=session,
            option=option,
            collected=collected,
        )
        if selection_flow is not None:
            return selection_flow

        summary_flow = _prepare_summary_flow_if_applicable(
            session=session,
            option=option,
            collected=collected,
        )
        if summary_flow is not None:
            return summary_flow

        return _advance_option_after_payload_collection(
            session=session,
            option=option,
            payload=collected,
        )

    updated_payload = dict(payload)
    updated_payload.update(_extract_fields_from_text(text))
    _transition_session_state(
        session=session,
        status="awaiting_confirmation",
        payload=updated_payload,
        missing_fields=[],
    )
    return MenuInterceptResult(
        handled=True,
        response_text=_format_workflow_selection_confirmation(option, session, updated_payload, session.channel or "web"),
    )


def _handle_missing_fields_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    coordinator = _build_field_collection_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    merged = coordinator.merge_reply_payload(workflow_state, text=text)
    return _advance_option_after_payload_collection(
        session=session,
        option=option,
        payload=merged,
    )


def _handle_additional_fields_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    payload = dict(session.collected_data or {})
    normalized = _normalize_text(text)
    if normalized not in {"pular", "prosseguir", "continuar", "seguir"}:
        payload.update(_extract_numbered_fields_from_text(text, session.missing_fields or []))
        payload.update(_extract_fields_from_text(text))

    return _execute_option_with_payload(
        session=session,
        option=option,
        payload=payload,
    )


def _advance_option_after_payload_collection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    original_payload = dict(payload or {})
    preserved_hidden_payload = {
        key: value
        for key, value in original_payload.items()
        if str(key).startswith("_")
    }
    coordinator = _build_field_collection_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    decision = coordinator.evaluate_payload(
        workflow_state=workflow_state,
        raw_required_fields=option.required_fields,
        payload=payload,
    )
    payload = decision.payload
    if preserved_hidden_payload:
        payload = {**payload, **preserved_hidden_payload}
    missing = [field.model_dump() for field in decision.missing_fields]

    if decision.route == FIELD_COLLECTION_ROUTE_PROMPT_MISSING:
        assisted_selection = _prepare_missing_field_selection_flow_if_applicable(
            session=session,
            option=option,
            collected=payload,
            missing_fields=missing,
        )
        if assisted_selection is not None:
            return assisted_selection

        _transition_session_state(
            session=session,
            status="awaiting_fields",
            payload=payload,
            missing_fields=missing,
        )
        return MenuInterceptResult(
            handled=True,
            response_text=_format_missing_fields(option, missing, payload, session.channel or "web"),
        )

    additional_fields = _list_additional_fields(option, payload)
    if additional_fields:
        _transition_session_state(
            session=session,
            status=ADDITIONAL_FIELDS_STATUS,
            payload=payload,
            missing_fields=[field.model_dump() for field in additional_fields],
        )
        return MenuInterceptResult(
            handled=True,
            response_text=_format_additional_fields(option, additional_fields, payload, session, session.channel or "web"),
        )

    return _execute_option_with_payload(
        session=session,
        option=option,
        payload=payload,
    )


def _handle_item_selection_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    coordinator = _build_assisted_selection_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    decision = coordinator.handle_reply(workflow_state, text=text)
    if decision.route == SELECTION_ROUTE_ADVANCE:
        return _advance_option_after_payload_collection(
            session=session,
            option=option,
            payload=decision.payload,
        )
    if decision.route == SELECTION_ROUTE_CONFIRM:
        return _advance_option_after_payload_collection(
            session=session,
            option=option,
            payload=decision.payload,
        )
    return MenuInterceptResult(
        handled=True,
        response_text=decision.response_text or build_recovery_message("Selecao nao concluida", "Nao consegui processar a selecao agora.", channel=session.channel or "web", next_steps=["Tente informar novamente apenas o numero da opcao."]),
    )


def _is_menu_request(lower_text: str) -> bool:
    if lower_text in {"?", "ajuda", "help"}:
        return True
    return any(w in lower_text for w in MENU_WORDS)


def _looks_like_command(lower_text: str) -> bool:
    normalized = _normalize_text(lower_text)
    has_command = any(token in normalized for token in COMMAND_HINTS)
    has_query = any(token in normalized for token in COMMAND_QUERY_HINTS)
    has_scope = any(token in normalized for token in COMMAND_SCOPE_HINTS)
    has_status = any(token in normalized for token in COMMAND_STATUS_HINTS)
    is_hitl_operation = bool(
        re.search(r"\b(aprovar|aprovado|aprova|rejeitar|rejeitado|recusar|revalidar)\b", normalized)
    )
    is_pending_decision_query = bool(
        (
            "minha decisao" in normalized
            or "minha decisão" in lower_text
            or "aguardando minha decisao" in normalized
            or "aguardando minha decisão" in lower_text
        )
        and re.search(r"\b(acao|acoes|ação|ações|solicitacao|solicitação)\b", lower_text, flags=re.IGNORECASE)
    )
    is_deadline_rewrite = bool(
        re.search(
            r"\b(coloque|mudar|alterar)\b.*\b(para o dia|prazo|nova data|novo prazo)\b",
            normalized,
        )
    )
    is_task_completion_operation = bool(
        re.search(
            r"\b(dar como conclu(?:ida|ido|ir)|concluir|concluida|concluido|finalizar|encerrar)\b",
            normalized,
        )
        and re.search(r"\b(atividade|atividades|tarefa|tarefas)\b", normalized)
    )
    if is_hitl_operation or is_pending_decision_query or is_deadline_rewrite or is_task_completion_operation:
        return True
    return (has_command or has_query) and (has_scope or has_status)


def _is_context_disambiguation_reply(text: str, lower_text: str) -> bool:
    if _extract_selection_index(text) in {1, 2}:
        return True
    return lower_text in {"nova conversa", "continuar", "continuar a atual", "atual"}


def _is_greeting_only_message(lower_text: str) -> bool:
    normalized = _normalize_text(lower_text)
    if not normalized:
        return False
    compact = re.sub(r"[^\w\s]", " ", normalized)
    compact = " ".join(compact.split())
    if compact in GREETING_ONLY_PHRASES:
        return True

    tokens = compact.split()
    removable_suffixes = {"sapiens", "versus", "gestao", "gestão", "corp", "bot", "ai"}
    while tokens and tokens[-1] in removable_suffixes:
        tokens.pop()
    compact = " ".join(tokens)
    return compact in GREETING_ONLY_PHRASES


def _build_greeting_only_message(user_id: int) -> str:
    first_name = _resolve_user_first_name(user_id)
    greeting = (
        f"Olá {first_name}! Espero que esteja bem."
        if first_name
        else "Olá! Espero que esteja bem."
    )
    return (
        f"{greeting}\n\n"
        "Você pode:\n"
        "- digitar menu para navegar pelas opções\n"
        "- ou me fazer uma pergunta diretamente"
    )


def _should_prompt_context_disambiguation(
    session: AgentMenuSession,
    *,
    text: str,
    lower: str,
    explicit_code: Optional[str],
    is_item_selection_reply: bool,
    is_company_selection_reply: bool,
    is_summary_selection_reply: bool,
    is_missing_fields_reply: bool,
    is_confirmation_adjustment_reply: bool,
) -> bool:
    if session.status in {"idle", CONTEXT_DISAMBIGUATION_STATUS}:
        return False
    if explicit_code or _is_menu_request(lower):
        return False
    if (
        is_item_selection_reply
        or is_company_selection_reply
        or is_summary_selection_reply
        or is_missing_fields_reply
        or is_confirmation_adjustment_reply
    ):
        return False
    return _looks_like_command(lower)


def _extract_explicit_code(text: str, lower_text: str) -> Optional[str]:
    has_menu_signal = any(w in lower_text for w in MENU_WORDS) or any(h in lower_text for h in EXECUTE_HINTS)
    pure_code = bool(re.fullmatch(r"\s*\d+(?:\.\d+)*\s*", text))
    if not has_menu_signal and not pure_code:
        return None

    m = re.search(r"(?<!\d)(\d+(?:\.\d+){0,8})(?!\d)", text)
    if not m:
        return None
    return m.group(1)


def _extract_fields_from_text(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    stripped_text = str(text or "").strip()

    # Padrão "campo: valor" ou "campo=valor" por linha, evitando capturas internas
    # em valores de data/hora como "14:30".
    line_pattern = re.compile(r"^\s*([A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_ ]{1,59})\s*[:=]\s*(.+?)\s*$")
    for line in (text or "").splitlines():
        m = line_pattern.match(line)
        if not m:
            continue
        key_raw = (m.group(1) or "").strip()
        val_raw = (m.group(2) or "").strip()
        key = _slugify(key_raw)
        val = val_raw.strip(" ,.")
        if key and val and not key.isdigit():
            data[key] = val

    # Captura livre de "dados: ..."
    marker = re.search(r"(dados?|informacoes?|informações?)\s*[:=]\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if marker:
        free_text = marker.group(2).strip()
        if free_text:
            data.setdefault("dados", free_text)

    alias_match = COMPANY_ALIAS_PATTERN.match(stripped_text)
    if alias_match:
        alias_code = (alias_match.group(1) or "").strip()
        alias_name = (alias_match.group(2) or "").strip()
        if alias_code and len(alias_code) <= 5:
            data.setdefault("empresa", f"{alias_code} - {alias_name}".strip(" -") if alias_name else alias_code)

    company_match = re.search(
        r"(?:\bda?\s+empresa\b|\bempresa\b)\s+(.+?)(?=\s+(?:com\b|para\b|respons[aá]vel\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|tem\b|t[eê]m\b|ids?\b)|[?.!,;]|$)",
        text,
        flags=re.IGNORECASE,
    )
    if company_match:
        company_name = company_match.group(1).strip(" ,.-")
        normalized_company_name = _normalize_text(company_name)
        if company_name and not (
            normalized_company_name.startswith("sistema ")
            or normalized_company_name == "sistema"
            or "aguardando minha decisao" in normalized_company_name
        ):
            data.setdefault("empresa", company_name)

    if "empresa" not in data:
        implicit_company_match = re.search(
            r"\b(?:da|do|na|no)\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ0-9&'`.-]+(?:\s+(?!com\b|para\b|respons[aá]vel\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|tem\b|t[eê]m\b|ids?\b)[A-ZÀ-Ý][A-Za-zÀ-ÿ0-9&'`.-]+){0,5})(?=\s+(?:com\b|para\b|respons[aá]vel\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|tem\b|t[eê]m\b|ids?\b)|[?.!,;]|$)",
            text,
            flags=re.IGNORECASE,
        )
        if implicit_company_match:
            implicit_company = implicit_company_match.group(1).strip(" ,.-")
            normalized_implicit_company = _normalize_text(implicit_company)
            if implicit_company and normalized_implicit_company not in {"mim", "me", "ele", "ela"} and not (
                normalized_implicit_company.startswith("sistema ")
                or normalized_implicit_company == "sistema"
                or "aguardando minha decisao" in normalized_implicit_company
            ):
                data.setdefault("empresa", implicit_company)

    collaborator_patterns = (
        r"\b(?:usuario|usuário|colaborador)\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+){0,4})(?=\s+(?:da?\s+empresa\b|na?\s+empresa\b|empresa\b|com\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|tem\b|t[eê]m\b|vencid[oa]s?\b|atrasad[oa]s?\b|abert[oa]s?\b|concluid[oa]s?\b|ids?\b)|[?.!,;]|$)",
        r"\brespons[aá]vel(?:\s+por)?\s+(.+?)(?=\s+(?:da?\s+empresa\b|na?\s+empresa\b|empresa\b|com\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|ids?\b)|[?.!,;]|$)",
        r"\bque\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+){0,4})(?=\s+(?:da?\s+empresa\b|na?\s+empresa\b|empresa\b|com\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|tem\b|t[eê]m\b|ids?\b)|[?.!,;]|$)",
        r"\bpara\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+){0,4})(?=\s+(?:da?\s+empresa\b|na?\s+empresa\b|empresa\b|com\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b|ids?\b)|[?.!,;]|$)",
        r"\bde\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+){0,4})(?=\s+(?:da?\s+empresa\b|na?\s+empresa\b|empresa\b|com\b|status\b|hoje\b|esta\b|este\b|semana\b|mes\b|m[eê]s\b)|[?.!,;]|$)",
    )
    for pattern in collaborator_patterns:
        collaborator_match = re.search(pattern, text, flags=re.IGNORECASE)
        if not collaborator_match:
            continue
        collaborator_name = collaborator_match.group(1).strip(" ,.-")
        collaborator_name = re.sub(
            r"\s+\b(?:na|no|da|do)\s+empresa\b.*$",
            "",
            collaborator_name,
            flags=re.IGNORECASE,
        ).strip(" ,.-")
        collaborator_name = re.sub(r"\s+\b(?:na|no|da|do)\b$", "", collaborator_name, flags=re.IGNORECASE).strip(" ,.-")
        collaborator_name = re.sub(
            r"\s+\b(?:esta\s+semana|este\s+mes|este\s+m[eê]s|hoje)\b.*$",
            "",
            collaborator_name,
            flags=re.IGNORECASE,
        ).strip(" ,.-")
        collaborator_name = re.sub(
            r"\s+\b(?:tem|t[eê]m|est[aã]o|possui|tem\s+vencid[oa]s?|tem\s+atrasad[oa]s?)\b.*$",
            "",
            collaborator_name,
            flags=re.IGNORECASE,
        ).strip(" ,.-")
        normalized_collaborator = _normalize_text(collaborator_name)
        collaborator_tokens = [token for token in normalized_collaborator.split() if token]
        collaborator_leading_noise = {
            "tem",
            "temos",
            "tenho",
            "estao",
            "estão",
            "fazer",
            "este",
            "esta",
            "hoje",
            "semana",
            "mes",
            "atividade",
            "atividades",
            "tarefa",
            "tarefas",
            "instancia",
            "instancias",
            "processo",
            "processos",
            "projetos",
            "sistema",
            "todas",
        }
        if collaborator_name and normalized_collaborator not in {
            "ids",
            "id",
            "fazer",
            "fazer hoje",
            "tem",
            "temos",
            "tenho",
            "estao",
            "estão",
            "este",
            "esta",
            "este mes",
            "esta semana",
            "hoje",
            "semana",
            "mes",
        } and not (
            collaborator_tokens
            and collaborator_tokens[0] in collaborator_leading_noise
        ) and not (
            collaborator_tokens
            and all(token in collaborator_leading_noise for token in collaborator_tokens)
        ) and not (
            normalized_collaborator.startswith("quais ")
            or normalized_collaborator.startswith("qual ")
            or normalized_collaborator.startswith("me diga ")
            or normalized_collaborator.startswith("gostaria ")
            or normalized_collaborator.startswith("atividad")
            or normalized_collaborator.startswith("atividade")
            or normalized_collaborator.startswith("projet")
            or normalized_collaborator.startswith("sistema")
            or normalized_collaborator.startswith("todas")
        ):
            data.setdefault("colaborador", collaborator_name)
            break

    normalized_text = _normalize_text(text)
    mentions_processes = any(token in normalized_text for token in {"instancia", "instancias", "processo", "processos"})
    mentions_tasks = any(token in normalized_text for token in {"atividade", "atividades", "tarefa", "tarefas"})
    if mentions_processes and mentions_tasks:
        data["entidade"] = "mixed"
    elif mentions_processes:
        data.setdefault("entidade", "process_instance")
    elif mentions_tasks:
        data["entidade"] = "project_task"

    if re.search(r"\bsem\s+respons[aá]vel\b", text, flags=re.IGNORECASE):
        data.setdefault("tipo_auditoria", "missing_responsible")
    elif re.search(r"\bsem\s+data\b", text, flags=re.IGNORECASE):
        data.setdefault("tipo_auditoria", "missing_due_date")

    if any(token in normalized_text for token in {"vencido", "vencidos", "vencida", "vencidas", "atrasado", "atrasados", "atrasada", "atrasadas"}):
        data.setdefault("status_consulta", "overdue")
    elif any(token in normalized_text for token in {"aberto", "abertos", "aberta", "abertas", "pendente", "pendentes"}):
        data.setdefault("status_consulta", "open")
    elif any(token in normalized_text for token in {"concluido", "concluidos", "concluida", "concluidas", "finalizado", "finalizados", "finalizada", "finalizadas"}):
        data.setdefault("status_consulta", "completed")

    id_match = re.search(r"\bids?\s*[:=]?\s*([\d,\seE]+)", text, flags=re.IGNORECASE)
    if id_match:
        raw_ids = re.findall(r"\d+", id_match.group(1))
        if raw_ids:
            joined_ids = ",".join(raw_ids)
            data.setdefault("ids", joined_ids)
            data.setdefault("codigo_atividade", joined_ids)

    deadline_match = re.search(
        r"\b(?:para\s+o\s+dia|para\s+dia|pra\s+o\s+dia|pra\s+dia|novo\s+prazo|nova\s+data|prazo\s+para)\s+(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if deadline_match:
        due_date_value = deadline_match.group(1).strip()
        data.setdefault("due_date", due_date_value)
        data.setdefault("prazo", due_date_value)

    if re.search(r"\b(aprovar|aprovado|aprova)\b", normalized_text):
        data.setdefault("agent_action_operation", "approve")
    elif re.search(r"\b(rejeitar|rejeitado|recusar|recusado)\b", normalized_text):
        data.setdefault("agent_action_operation", "reject")
    elif re.search(r"\b(revalidar|renovar prazo|renove o prazo)\b", normalized_text):
        data.setdefault("agent_action_operation", "revalidate")

    if "agent_action_operation" in data:
        action_id_match = re.search(
            r"\b(?:ticket|solicitacao|solicitação|aprovacao|aprovação|acao|ação)?\s*#?\s*(\d{1,6})\b",
            text,
            flags=re.IGNORECASE,
        )
        if action_id_match:
            data.setdefault("agent_action_id", action_id_match.group(1))

    pending_action_limit_match = re.search(
        r"\b(?:liste|listar|lista)\s+(\d{1,2})\s+(?:acoes|ações|solicitacoes|solicitações)\b",
        text,
        flags=re.IGNORECASE,
    )
    if pending_action_limit_match:
        data.setdefault("limite", pending_action_limit_match.group(1))

    if "periodo" not in data:
        if "hoje" in normalized_text:
            data.setdefault("periodo", "hoje")
        elif "semana" in normalized_text:
            data.setdefault("periodo", "esta semana")
        elif "mes" in normalized_text:
            data.setdefault("periodo", "este mes")

    return data


def _public_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v for k, v in (payload or {}).items()
        if not str(k).startswith("_")
    }


def _resolve_user_first_name(user_id: int) -> Optional[str]:
    from models import User

    try:
        user = User.query.get(user_id)
    except RuntimeError:
        return None
    if not user or not str(getattr(user, "name", "") or "").strip():
        return None
    return str(user.name).strip().split(" ")[0]


def _resolve_company_session_label(company_id: Optional[int]) -> Optional[str]:
    if not company_id:
        return None
    from models.company import Company

    try:
        company = Company.query.get(company_id)
    except RuntimeError:
        return None
    if not company:
        return None
    code = str(getattr(company, "client_code", "") or "").strip()
    name = str(getattr(company, "name", "") or getattr(company, "legal_name", "") or "").strip()
    return " - ".join([part for part in (code, name) if part])


def _inject_session_context_into_payload(
    *,
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    updated = dict(payload or {})
    explicit_company_id = _resolve_explicit_company_id_from_payload(
        payload=updated,
        user_id=session.user_id,
    )
    if explicit_company_id:
        updated["_selected_company_id"] = int(explicit_company_id)
        explicit_label = _resolve_company_session_label(int(explicit_company_id))
        if explicit_label:
            updated["_resolved_company_label"] = explicit_label
    elif session.company_id and updated.get("_selected_company_id") is None and str(option.action_key or "").strip().lower() != "company.list_accessible":
        updated["_selected_company_id"] = int(session.company_id)
    updated.setdefault("_session_user_id", int(session.user_id))
    if session.company_id:
        updated.setdefault("_session_company_id", int(session.company_id))
    user_name = _resolve_user_first_name(session.user_id)
    if user_name:
        updated.setdefault("_session_user_name", user_name)
    company_label = _resolve_company_session_label(session.company_id)
    if company_label:
        updated.setdefault("_session_company_label", company_label)
    return updated


def _build_auto_filled_session_lines(payload: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    if payload.get("_session_user_name"):
        lines.append(f"Usuario: {payload['_session_user_name']}")
    if payload.get("_resolved_company_label"):
        lines.append(f"Empresa da consulta: {payload['_resolved_company_label']}")
    elif payload.get("_summary_company_label"):
        lines.append(f"Empresa da consulta: {payload['_summary_company_label']}")
    elif payload.get("_session_company_label"):
        lines.append(f"Empresa ativa: {payload['_session_company_label']}")
    return lines


def _payload_without_navigation(payload: Dict[str, Any]) -> Dict[str, Any]:
    return workflow_payload_without_navigation(payload)


def _extract_navigation_stack(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return extract_workflow_navigation_stack(payload)


def _build_session_snapshot(session: AgentMenuSession) -> Optional[Dict[str, Any]]:
    snapshot = build_workflow_session_snapshot(session)
    if snapshot is None:
        return None
    return snapshot.model_dump()


def _transition_session_state(
    session: AgentMenuSession,
    *,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[Dict[str, Any]]] = None,
    push_history: bool = True,
) -> None:
    _build_session_navigation_runtime().transition_state(
        session,
        status=status,
        payload=payload,
        missing_fields=missing_fields,
        push_history=push_history,
    )


def _prepare_context_disambiguation(
    session: AgentMenuSession,
    *,
    pending_message: str,
) -> MenuInterceptResult:
    payload = dict(session.collected_data or {})
    payload["_context_disambiguation_previous_status"] = str(session.status or "idle")
    payload["_context_disambiguation_pending_message"] = pending_message
    payload["_context_disambiguation_missing_fields"] = list(session.missing_fields or [])
    _transition_session_state(
        session=session,
        status=CONTEXT_DISAMBIGUATION_STATUS,
        payload=payload,
        missing_fields=[],
    )
    return MenuInterceptResult(
        handled=True,
        response_text=CONTEXT_DISAMBIGUATION_PROMPT,
    )


def _handle_context_disambiguation_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
    *,
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
) -> MenuInterceptResult:
    payload = dict(session.collected_data or {})
    pending_message = str(payload.get("_context_disambiguation_pending_message") or "").strip()
    previous_status = str(payload.get("_context_disambiguation_previous_status") or "").strip() or "idle"
    previous_missing_fields = list(payload.get("_context_disambiguation_missing_fields") or [])

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Perfeito. Fluxo anterior encerrado. Quando quiser, envie um novo pedido.",
        )

    selected_index = _extract_selection_index(text)
    normalized = _normalize_text(text)

    if selected_index == 1 or normalized == "nova conversa":
        if not pending_message:
            _reset_session(session)
            return MenuInterceptResult(
                handled=True,
                response_text="Nao consegui recuperar a ultima mensagem. Envie novamente o novo pedido.",
            )
        _reset_session(session)
        return handle_menu_message(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
            message=pending_message,
        )

    if selected_index == 2 or normalized in {"continuar", "continuar a atual", "atual"}:
        payload.pop("_context_disambiguation_pending_message", None)
        payload.pop("_context_disambiguation_previous_status", None)
        payload.pop("_context_disambiguation_missing_fields", None)
        _transition_session_state(
            session=session,
            status=previous_status,
            payload=payload,
            missing_fields=previous_missing_fields,
        )
        return MenuInterceptResult(
            handled=True,
            response_text="Certo. Entao continue a solicitacao atual com mais detalhes para eu concluir o fluxo.",
        )

    return MenuInterceptResult(
        handled=True,
        response_text="Responda com 1 para nova conversa ou 2 para continuar a atual.",
    )


def _render_current_session_prompt(session: AgentMenuSession) -> str:
    return _build_session_prompt_renderer().render(session)


def _parse_selection_number_date(text: str) -> Optional[Tuple[int, Optional[str]]]:
    """
    Interpreta:
    - 1: 27/02/2026
    - 1
    """
    m = re.match(r"^\s*(\d{1,3})(?:\s*[:=]\s*(.+))?\s*$", text or "")
    if not m:
        return None
    idx = int(m.group(1))
    right = (m.group(2) or "").strip()
    return idx, (right if right else None)


def _extract_choice_index_from_text(text: str, choices: List[Dict[str, Any]]) -> Optional[int]:
    normalized_text = _normalize_text(str(text or ""))
    if not normalized_text:
        return None

    for item in choices or []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue

        candidate_values = [
            item.get("label"),
            item.get("company_name"),
            item.get("company_code"),
            item.get("name"),
        ]
        normalized_candidates = {
            _normalize_text(str(value or ""))
            for value in candidate_values
            if str(value or "").strip()
        }
        if normalized_text in normalized_candidates:
            return index

        company_code = _normalize_text(str(item.get("company_code") or ""))
        company_name = _normalize_text(str(item.get("company_name") or ""))
        if company_code and company_name and normalized_text == f"{company_code} - {company_name}":
            return index
    return None


def _parse_completion_date(value: str):
    raw = (value or "").strip()
    if not raw:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _extract_numbered_fields_from_text(
    text: str,
    missing_fields: List[Dict[str, str]],
) -> Dict[str, str]:
    return extract_workflow_numbered_fields_from_text(text, missing_fields)


def _normalize_required_fields(raw_fields: Any) -> List[Dict[str, str]]:
    return [field.model_dump() for field in WorkflowRequiredField.normalize_many(raw_fields)]


def _missing_fields(required_fields: List[Dict[str, str]], collected_data: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        field.model_dump()
        for field in find_workflow_missing_required_fields(
            WorkflowRequiredField.normalize_many(required_fields),
            collected_data,
        )
    ]


def _adjust_required_fields_for_context(
    action_key: str,
    required_fields: List[Dict[str, str]],
    session: AgentMenuSession,
) -> List[Dict[str, str]]:
    del session
    return [
        field.model_dump()
        for field in adjust_workflow_required_fields_for_context(
            action_key,
            WorkflowRequiredField.normalize_many(required_fields),
        )
    ]


def _list_optional_fields(
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> List[WorkflowRequiredField]:
    normalized_payload = _public_payload(payload)
    fields = WorkflowRequiredField.normalize_many(option.required_fields or [])
    selected: List[WorkflowRequiredField] = []
    seen_keys: set[str] = set()
    for field in fields:
        if field.key in seen_keys:
            continue
        if field.category == "optional" and not str(normalized_payload.get(field.key) or "").strip():
            selected.append(field)
            seen_keys.add(field.key)
    return selected


def _list_complementary_fields(
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> List[WorkflowRequiredField]:
    normalized_payload = _public_payload(payload)
    fields = WorkflowRequiredField.normalize_many(option.required_fields or [])
    selected: List[WorkflowRequiredField] = []
    seen_keys: set[str] = set()
    for field in fields:
        if field.key in seen_keys:
            continue
        if field.category == "complementary" and not str(normalized_payload.get(field.key) or "").strip():
            selected.append(field)
            seen_keys.add(field.key)
    return selected


def _list_additional_fields(
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> List[WorkflowRequiredField]:
    return _list_optional_fields(option, payload) + _list_complementary_fields(option, payload)


def _is_read_only_action(action_key: Optional[str]) -> bool:
    action = (action_key or "").strip().lower()
    return action in {
        "routine.consult",
        "collaborator.occupancy",
        "company.list_accessible",
        "agent_action.list_pending",
        "project_task.audit",
        "my_work.open",
        "my_work.overdue",
        "my_work.due_range",
        "my_work.completed_range",
        "summary.today",
        "summary.week",
        "summary.month",
        "summary.custom",
        "onboarding.status",
        "onboarding.diagnose",
        "onboarding.go_live_check",
    }


def _prepare_selection_flow_if_applicable(
    session: AgentMenuSession,
    option: AgentMenuOption,
    collected: Dict[str, Any],
) -> Optional[MenuInterceptResult]:
    action = (option.action_key or "").strip().lower()
    if action not in {
        "project_task.complete",
        "process_instance.complete",
        "meeting.start",
        "meeting.summarize",
        "onboarding.diagnose",
    }:
        return None

    # Se já veio código explícito, segue fluxo padrão.
    if action == "project_task.complete" and any(k in collected for k in ("codigo_atividade", "activity_code", "task_code")):
        return None
    if action == "process_instance.complete" and any(k in collected for k in ("codigo_instancia", "instance_code", "codigo")):
        return None
    if action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"} and any(
        k in collected for k in ("id_reuniao", "meeting_id", "codigo_reuniao", "codigo")
    ):
        return None
    if action == "onboarding.diagnose" and any(
        k in collected for k in ("objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento")
    ):
        return None

    effective_company_id = _resolve_effective_company_id_for_payload(
        payload=collected,
        fallback_company_id=session.company_id,
        user_id=session.user_id,
    )
    selection = _load_open_choices(action=action, company_id=effective_company_id, user_id=session.user_id)
    if not selection.get("choices"):
        return None

    hidden_payload = build_assisted_selection_payload(
        dict(collected or {}),
        selection_action=action,
        selection=selection,
    )

    _transition_session_state(
        session=session,
        status="awaiting_item_selection",
        payload=hidden_payload,
        missing_fields=[],
    )

    return MenuInterceptResult(
        handled=True,
        response_text=_format_item_selection_prompt(option, selection, session.channel or "web"),
    )


def _prepare_missing_field_selection_flow_if_applicable(
    session: AgentMenuSession,
    option: AgentMenuOption,
    collected: Dict[str, Any],
    missing_fields: List[Dict[str, str]],
) -> Optional[MenuInterceptResult]:
    action = (option.action_key or "").strip().lower()
    if action not in {"project.update", "project.complete", "project_task.create"}:
        return None

    missing_keys = {_slugify(str(item.get("key") or "")) for item in (missing_fields or [])}
    if "codigo_projeto" not in missing_keys:
        return None

    effective_company_id = _resolve_effective_company_id_for_payload(
        payload=collected,
        fallback_company_id=session.company_id,
        user_id=session.user_id,
    )
    selection = _load_assisted_field_selection(
        action=action,
        field_key="codigo_projeto",
        company_id=effective_company_id,
        user_id=session.user_id,
    )
    if not selection.get("choices"):
        return None

    hidden_payload = build_assisted_selection_payload(
        _public_payload(collected),
        selection_action=action,
        selection=selection,
        selection_kind=selection.get("selection_kind") or "project_picker",
        selection_field_key=selection.get("field_key") or "codigo_projeto",
        selection_value_key=selection.get("value_key") or "code",
    )

    _transition_session_state(
        session=session,
        status="awaiting_item_selection",
        payload=hidden_payload,
        missing_fields=missing_fields,
    )

    return MenuInterceptResult(
        handled=True,
        response_text=_format_item_selection_prompt(option, selection, session.channel or "web"),
    )


def _prepare_summary_flow_if_applicable(
    session: AgentMenuSession,
    option: AgentMenuOption,
    collected: Dict[str, Any],
) -> Optional[MenuInterceptResult]:
    coordinator = _build_summary_workflow_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(_public_payload(collected))
    decision = coordinator.prepare_initial_step(workflow_state)
    if not decision.handled:
        return None

    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
    )


def _handle_summary_wizard_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    if session.status == "awaiting_summary_dates":
        return _handle_summary_dates_state(session, text, lower)
    if session.status == "awaiting_summary_company":
        return _handle_summary_company_state(session, text, lower)
    if session.status == "awaiting_summary_collaborator":
        return _handle_summary_collaborator_state(session, text, lower)
    if session.status == "awaiting_summary_status":
        return _handle_summary_status_state(session, text, lower)

    _reset_session(session)
    return MenuInterceptResult(
        handled=True,
        response_text="Sessao de resumo reiniciada. Digite 'menu' para continuar.",
    )


def _handle_summary_dates_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    payload = dict(session.collected_data or {})
    fields = _extract_fields_from_text(text)
    payload.update(fields)
    if "periodo" not in payload:
        payload["periodo"] = text.strip()

    coordinator = _build_summary_workflow_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(payload)
    decision = coordinator.advance_custom_period(
        workflow_state,
        payload=payload,
    )
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
        push_history=False,
    )


def _prepare_company_selection_flow_if_needed(
    session: AgentMenuSession,
    option: AgentMenuOption,
    collected: Dict[str, Any],
) -> Optional[MenuInterceptResult]:
    normalized_channel = str(session.channel or "").strip().lower()
    preserved_hidden_payload = {
        key: value
        for key, value in dict(collected or {}).items()
        if str(key).startswith("_")
    }
    coordinator = _build_operation_company_selection_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(_public_payload(collected))
    decision = coordinator.prepare_initial_selection(
        workflow_state,
        normalized_channel=normalized_channel,
        explicit_company_id=_resolve_explicit_company_id_from_payload(
            payload=workflow_state.payload,
            user_id=session.user_id,
        ),
        choices=_load_summary_company_choices(user_id=session.user_id),
    )
    if decision.route != COMPANY_SELECTION_ROUTE_PROMPT:
        return None

    next_payload = dict(decision.payload or {})
    if preserved_hidden_payload:
        next_payload.update(preserved_hidden_payload)
    _transition_session_state(
        session=session,
        status=COMPANY_SELECTION_STATUS,
        payload=next_payload,
        missing_fields=[],
    )
    return MenuInterceptResult(
        handled=True,
        response_text=_format_operation_company_prompt(
            option,
            [choice.model_dump() for choice in decision.choices],
            session.channel or "web",
        ),
    )


def _handle_operation_company_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    coordinator = _build_operation_company_selection_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    selected_index = _extract_selection_index(text)
    if selected_index is None:
        selected_index = _extract_choice_index_from_text(
            text,
            (workflow_state.payload or {}).get("_operation_company_choices") or [],
        )
    decision = coordinator.select_company(
        workflow_state,
        selected_index=selected_index,
        user_can_access_company=_user_can_access_company,
    )
    if decision.route != COMPANY_SELECTION_ROUTE_ADVANCE:
        if decision.should_reset_session:
            _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text=decision.response_text or build_recovery_message("Empresa nao identificada", "Nao consegui identificar a empresa selecionada.", channel=session.channel or "web", next_steps=["Responda apenas com o numero da empresa exibida."]),
        )

    payload = dict(decision.payload or {})
    selection_flow = _prepare_selection_flow_if_applicable(
        session=session,
        option=option,
        collected=payload,
    )
    if selection_flow is not None:
        return selection_flow

    summary_flow = _prepare_summary_flow_if_applicable(
        session=session,
        option=option,
        collected=payload,
    )
    if summary_flow is not None:
        return summary_flow

    return _advance_option_after_payload_collection(
        session=session,
        option=option,
        payload=payload,
    )


def _handle_summary_company_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    coordinator = _build_summary_workflow_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    selected_index = _extract_selection_index(text)
    if selected_index is None:
        selected_index = _extract_choice_index_from_text(
            text,
            (workflow_state.payload or {}).get("_summary_company_choices") or [],
        )
    decision = coordinator.select_company(
        workflow_state,
        selected_index=selected_index,
    )
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
        push_history=False,
    )


def _handle_summary_collaborator_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    if first_word in {"todos", "todas", "todo", "all"}:
        selected_indexes = [0]
    else:
        selected_indexes = _extract_selection_indexes(text, allow_zero=True)
        if not selected_indexes:
            matched_index = _extract_choice_index_from_text(
                text,
                (workflow_state.payload or {}).get("_summary_collaborator_choices") or [],
            )
            if matched_index is not None:
                selected_indexes = [matched_index]
    coordinator = _build_summary_workflow_coordinator()
    decision = coordinator.select_collaborators(
        workflow_state,
        selected_indexes=selected_indexes,
    )
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
        push_history=False,
    )


def _handle_summary_status_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    option = session.selected_option
    if not option:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Sessao de menu reiniciada. Digite 'menu' para continuar.")

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Digite 'menu' para retomar.")

    selected_index = _extract_selection_index(text)
    coordinator = _build_summary_workflow_coordinator()
    workflow_state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    )
    decision = coordinator.select_status(
        workflow_state,
        selected_index=selected_index,
    )
    if decision.route == SUMMARY_ROUTE_RESET and decision.response_text:
        logger.warning("Fluxo de resumo finalizado com reset apos erro: %s", decision.response_text)
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
        push_history=False,
    )


def _handle_summary_email_confirmation_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    payload = dict(session.collected_data or {})
    report_text = str(payload.get("_summary_report_text") or "").strip()
    if not report_text:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Nao consegui recuperar o relatorio para envio por e-mail. Gere um novo resumo em menu 3.5.",
        )

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Perfeito. Nao enviarei por e-mail. Se quiser outro resumo, digite menu 3.5.",
        )

    selected_index = _extract_selection_index(text)
    if selected_index == 1:
        target_email = _resolve_user_primary_email(session.user_id)
        if not target_email:
            return MenuInterceptResult(
                handled=True,
                response_text=(
                    "Nao encontrei um e-mail valido no seu cadastro.\n"
                    "Escolha 2 para informar outro e-mail."
                ),
            )
        return _send_summary_report_email(payload=payload, target_email=target_email, report_text=report_text, session=session)

    if selected_index == 2:
        _transition_session_state(
            session=session,
            status=SUMMARY_EMAIL_CUSTOM_STATUS,
            payload=payload,
            missing_fields=[],
        )
        return MenuInterceptResult(
            handled=True,
            response_text="Informe o e-mail de destino (ex: nome@empresa.com.br).",
        )

    if selected_index is not None:
        return MenuInterceptResult(
            handled=True,
            response_text="Opcao invalida. Responda com 1, 2 ou nao.",
        )

    direct_email = _extract_email_from_text(text)
    if direct_email:
        return _send_summary_report_email(payload=payload, target_email=direct_email, report_text=report_text, session=session)

    if _is_affirmative_confirmation_text(text):
        target_email = _resolve_user_primary_email(session.user_id)
        if not target_email:
            return MenuInterceptResult(
                handled=True,
                response_text=(
                    "Nao encontrei um e-mail valido no seu cadastro.\n"
                    "Escolha 2 para informar outro e-mail."
                ),
            )
        return _send_summary_report_email(payload=payload, target_email=target_email, report_text=report_text, session=session)

    return MenuInterceptResult(
        handled=True,
        response_text="Responda com 1 (meu e-mail), 2 (outro e-mail) ou nao.",
    )


def _handle_summary_email_custom_state(
    session: AgentMenuSession,
    text: str,
    lower: str,
) -> MenuInterceptResult:
    payload = dict(session.collected_data or {})
    report_text = str(payload.get("_summary_report_text") or "").strip()
    if not report_text:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Nao consegui recuperar o relatorio para envio por e-mail. Gere um novo resumo em menu 3.5.",
        )

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CANCEL_WORDS:
        return _handle_back_navigation(session)

    selected_index = _extract_selection_index(text)
    if selected_index == 1:
        target_email = _resolve_user_primary_email(session.user_id)
        if not target_email:
            return MenuInterceptResult(
                handled=True,
                response_text="Nao encontrei um e-mail valido no seu cadastro. Informe outro e-mail de destino.",
            )
        return _send_summary_report_email(payload=payload, target_email=target_email, report_text=report_text, session=session)

    if selected_index == 2:
        return MenuInterceptResult(
            handled=True,
            response_text="Informe o e-mail de destino (ex: nome@empresa.com.br).",
        )

    direct_email = _extract_email_from_text(text)
    if not direct_email:
        return MenuInterceptResult(
            handled=True,
            response_text="E-mail invalido. Informe um e-mail valido (ex: nome@empresa.com.br) ou responda nao para cancelar.",
        )

    return _send_summary_report_email(payload=payload, target_email=direct_email, report_text=report_text, session=session)


def _send_summary_report_email(
    payload: Dict[str, Any],
    target_email: str,
    report_text: str,
    session: AgentMenuSession,
) -> MenuInterceptResult:
    subject = _build_summary_email_subject_from_payload(payload)
    email_service = _build_summary_email_service()
    sent = email_service.send_email(
        to_emails=[target_email],
        subject=subject,
        body=report_text,
    )
    _reset_session(session)
    if sent:
        return MenuInterceptResult(
            handled=True,
            response_text=f"Perfeito! ✅ Enviei o relatorio para {target_email}.",
        )

    return MenuInterceptResult(
        handled=True,
        response_text="Tentei enviar o e-mail, mas houve uma falha no serviço agora. Posso tentar novamente.",
    )


def _build_summary_email_service():
    from services.email_service import EmailService

    service = EmailService()
    integration = _resolve_active_email_integration()
    if not integration:
        return service

    try:
        _apply_email_integration_to_service(service, integration)
    except Exception:
        logger.exception("Falha ao aplicar configuracao de e-mail da integracao no envio do resumo.")
    return service


def _resolve_active_email_integration() -> Optional[Dict[str, Any]]:
    try:
        from database.postgresql_db import get_integration, list_integrations
        from src.intelligence.tool_context import get_sapiens_context
    except Exception:
        return None

    company_id = None
    try:
        company_id = get_sapiens_context().company_id
    except Exception:
        company_id = None

    try:
        preferred = get_integration("email_integration", company_id=company_id)
        if preferred and _is_email_integration_record(preferred):
            return preferred
    except Exception:
        logger.exception("Falha ao buscar integracao 'email_integration'.")

    try:
        integrations = list_integrations(company_id=company_id) or []
    except Exception:
        logger.exception("Falha ao listar integracoes para envio de resumo por e-mail.")
        return None

    for record in integrations:
        if _is_email_integration_record(record):
            return record
    return None


def _is_email_integration_record(record: Dict[str, Any]) -> bool:
    if not isinstance(record, dict):
        return False

    record_type = _normalize_integration_service(record.get("type"))
    if record_type == "email":
        return True

    record_id = str(record.get("id") or "").strip().lower()
    if record_id == "email_integration":
        return True

    inferred = _normalize_integration_service(record_id)
    if inferred == "email":
        return True
    if record_id.endswith("_integration"):
        inferred = _normalize_integration_service(record_id[: -len("_integration")])
        if inferred == "email":
            return True
    return False


def _normalize_integration_service(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    aliases = {
        "mail": "email",
        "e-mail": "email",
    }
    return aliases.get(normalized, normalized)


def _apply_email_integration_to_service(service: Any, integration: Dict[str, Any]) -> None:
    config = integration.get("config") if isinstance(integration, dict) else {}
    config = config if isinstance(config, dict) else {}
    provider = str(
        config.get("provider")
        or integration.get("provider")
        or ""
    ).strip().lower()
    if provider in {"", "disabled", "none"}:
        return

    service.provider = provider
    service.smtp_server = config.get("server") or service.smtp_server
    service.smtp_port = _coerce_int(config.get("port"), default=service.smtp_port or 587)
    service.smtp_username = config.get("username") or service.smtp_username
    service.smtp_secret = config.get("password") or service.smtp_secret
    service.default_sender = config.get("default_sender") or config.get("from_email") or service.default_sender
    service.from_name = config.get("from_name") or service.from_name
    service.webhook_url = config.get("webhook_url") or service.webhook_url

    service.inbound_protocol = str(config.get("inbound_protocol") or service.inbound_protocol or "").strip().lower()
    service.inbound_host = config.get("inbound_host") or service.inbound_host
    service.inbound_port = _coerce_int(config.get("inbound_port"), default=service.inbound_port or 0)
    service.inbound_username = config.get("inbound_username") or service.inbound_username
    service.inbound_password = config.get("inbound_password") or service.inbound_password
    if "inbound_use_ssl" in config:
        service.inbound_use_ssl = bool(config.get("inbound_use_ssl"))


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _resolve_user_primary_email(user_id: int) -> Optional[str]:
    from models.user import User

    user = User.query.get(user_id)
    email = str(getattr(user, "email", "") or "").strip()
    if _is_valid_email_address(email):
        return email
    return None


def _extract_email_from_text(text: str) -> Optional[str]:
    match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", str(text or ""))
    if not match:
        return None
    candidate = str(match.group(1) or "").strip()
    if _is_valid_email_address(candidate):
        return candidate
    return None


def _is_valid_email_address(value: str) -> bool:
    email = str(value or "").strip()
    if not email:
        return False
    if len(email) > 254:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email))


def _is_affirmative_confirmation_text(value: str) -> bool:
    normalized = _normalize_text(value or "")
    if not normalized:
        return False

    direct_hits = {
        "sim",
        "s",
        "ok",
        "claro",
        "pode",
        "pode sim",
        "envia",
        "envie",
        "manda",
        "quero",
    }
    if normalized in direct_hits:
        return True

    keyword_hits = (
        "por email",
        "por e-mail",
        "pode enviar",
        "envie por",
        "manda por",
        "quero por",
    )
    return any(keyword in normalized for keyword in keyword_hits)


def _build_summary_email_subject_from_payload(payload: Dict[str, Any]) -> str:
    collaborator = str(
        payload.get("_summary_employee_name")
        or payload.get("colaborador")
        or "Colaborador"
    ).strip()
    company = str(
        payload.get("_summary_company_label")
        or payload.get("empresa")
        or "Empresa"
    ).strip()
    period = str(payload.get("periodo") or "").strip()
    status_label = str(payload.get("status") or "Todas").strip()

    subject = f"Relatorio de Resumo - {collaborator} - {status_label}"
    if period:
        subject += f" ({period})"
    if company:
        subject += f" - {company}"
    return subject


def _format_summary_period_prompt(option: AgentMenuOption, channel: str = "web") -> str:
    return build_summary_period_prompt(_build_workflow_display_option(option), channel=channel)


def _build_workflow_display_option(option: AgentMenuOption) -> WorkflowDisplayOption:
    action_key = str(option.action_key or "").strip()
    return WorkflowDisplayOption(
        code=str(option.code or "").strip(),
        title=str(option.title or "").strip(),
        action_key=(action_key or None),
        description=(str(option.description or "").strip() or _default_workflow_description(action_key, str(option.title or "").strip()) or None),
    )


def _build_assisted_selection_coordinator() -> AssistedSelectionCoordinator:
    return AssistedSelectionCoordinator(
        extract_fields_from_text=_extract_fields_from_text,
        parse_selection_number_date=_parse_selection_number_date,
        parse_completion_date=_parse_completion_date,
        public_payload=_public_payload,
    )


def _build_field_collection_coordinator() -> FieldCollectionCoordinator:
    return FieldCollectionCoordinator(
        extract_fields_from_text=_extract_fields_from_text,
        public_payload=_public_payload,
    )


def _build_operation_company_selection_coordinator() -> OperationCompanySelectionCoordinator:
    return OperationCompanySelectionCoordinator(
        public_payload=_public_payload,
        summary_action_keys=set(SUMMARY_ACTION_PERIOD.keys()),
    )


def _build_workflow_approval_policy_guard() -> WorkflowApprovalPolicyGuard:
    return WorkflowApprovalPolicyGuard()


def _build_direct_execution_dispatcher() -> DirectExecutionDispatcher:
    return DirectExecutionDispatcher(
        {
            "collaborator.occupancy": build_handler_executor(
                handler_factory=_build_collaborator_occupancy_execution_handler,
                request_model=CollaboratorOccupancyRequest,
            ),
            "company.list_accessible": build_handler_executor(
                handler_factory=_build_company_access_execution_handler,
                request_model=CompanyAccessExecutionRequest,
            ),
            "project_task.create": build_handler_executor(
                handler_factory=_build_project_task_create_execution_handler,
                request_model=ProjectTaskCreateRequest,
            ),
            "project_task.audit": build_handler_executor(
                handler_factory=_build_project_task_audit_execution_handler,
                request_model=ProjectTaskAuditRequest,
            ),
            "project_task.complete": build_handler_executor(
                handler_factory=_build_project_task_complete_execution_handler,
                request_model=ProjectTaskCompleteRequest,
            ),
            "project_task.update": build_handler_executor(
                handler_factory=_build_project_task_update_execution_handler,
                request_model=ProjectTaskUpdateRequest,
            ),
            "agent_action.approve": build_handler_executor(
                handler_factory=_build_agent_action_operation_execution_handler,
                request_model=AgentActionOperationRequest,
                extra_fields_builder=lambda request: {
                    "payload": {
                        **dict(request.payload or {}),
                        "agent_action_operation": "approve",
                        "actor_name": "Sapiens",
                    }
                },
            ),
            "agent_action.reject": build_handler_executor(
                handler_factory=_build_agent_action_operation_execution_handler,
                request_model=AgentActionOperationRequest,
                extra_fields_builder=lambda request: {
                    "payload": {
                        **dict(request.payload or {}),
                        "agent_action_operation": "reject",
                        "actor_name": "Sapiens",
                    }
                },
            ),
            "agent_action.revalidate": build_handler_executor(
                handler_factory=_build_agent_action_operation_execution_handler,
                request_model=AgentActionOperationRequest,
                extra_fields_builder=lambda request: {
                    "payload": {
                        **dict(request.payload or {}),
                        "agent_action_operation": "revalidate",
                        "actor_name": "Sapiens",
                    }
                },
            ),
            "agent_action.list_pending": build_handler_executor(
                handler_factory=_build_agent_action_list_pending_execution_handler,
                request_model=AgentActionListPendingRequest,
            ),
            "process_instance.complete": build_handler_executor(
                handler_factory=_build_process_instance_complete_execution_handler,
                request_model=ProcessInstanceCompleteRequest,
            ),
            "my_work.open": build_handler_executor(
                handler_factory=_build_my_work_execution_handler,
                request_model=MyWorkExecutionRequest,
                action_override="my_work.open",
            ),
            "my_work.overdue": build_handler_executor(
                handler_factory=_build_my_work_execution_handler,
                request_model=MyWorkExecutionRequest,
                action_override="my_work.overdue",
            ),
            "my_work.due_range": build_handler_executor(
                handler_factory=_build_my_work_execution_handler,
                request_model=MyWorkExecutionRequest,
                action_override="my_work.due_range",
            ),
            "my_work.completed_range": build_handler_executor(
                handler_factory=_build_my_work_execution_handler,
                request_model=MyWorkExecutionRequest,
                action_override="my_work.completed_range",
            ),
            "routine.consult": build_handler_executor(
                handler_factory=_build_routine_consult_execution_handler,
                request_model=RoutineConsultExecutionRequest,
                action_override="routine.consult",
            ),
            "meeting.schedule": build_handler_executor(
                handler_factory=_build_meeting_schedule_execution_handler,
                request_model=MeetingScheduleRequest,
            ),
            "meeting.start": build_handler_executor(
                handler_factory=_build_meeting_start_execution_handler,
                request_model=MeetingStartRequest,
            ),
            "meeting.summarize": build_handler_executor(
                handler_factory=_build_meeting_summarize_execution_handler,
                request_model=MeetingSummarizeRequest,
            ),
            "meeting.close": build_handler_executor(
                handler_factory=_build_meeting_close_execution_handler,
                request_model=MeetingCloseRequest,
            ),
            "meeting.send_summary_email": build_handler_executor(
                handler_factory=_build_meeting_send_summary_email_execution_handler,
                request_model=MeetingSendSummaryEmailRequest,
            ),
            "meeting.send_summary_whatsapp": build_handler_executor(
                handler_factory=_build_meeting_send_summary_whatsapp_execution_handler,
                request_model=MeetingSendSummaryWhatsAppRequest,
            ),
            "finance.receipt_ingest": build_handler_executor(
                handler_factory=_build_financial_receipt_ingest_execution_handler,
                request_model=FinancialReceiptIngestRequest,
            ),
            "onboarding.status": build_handler_executor(
                handler_factory=_build_onboarding_status_execution_handler,
                request_model=OnboardingStatusRequest,
            ),
            "onboarding.diagnose": build_handler_executor(
                handler_factory=_build_onboarding_diagnose_execution_handler,
                request_model=OnboardingDiagnoseRequest,
            ),
            "onboarding.start": build_handler_executor(
                handler_factory=_build_onboarding_start_execution_handler,
                request_model=OnboardingStartRequest,
            ),
            "onboarding.go_live_check": build_handler_executor(
                handler_factory=_build_onboarding_go_live_check_execution_handler,
                request_model=OnboardingGoLiveCheckRequest,
            ),
        },
        policy_guard=_build_workflow_approval_policy_guard().evaluate,
    )


def _build_confirmation_coordinator() -> ConfirmationCoordinator:
    return ConfirmationCoordinator(
        confirm_words=CONFIRM_WORDS,
        cancel_words=CANCEL_WORDS,
        extract_fields_from_text=_extract_fields_from_text,
        public_payload=_public_payload,
        try_execute_direct_option=_try_execute_direct_option,
        build_execution_prompt=_build_execution_prompt,
    )


def _build_summary_workflow_coordinator() -> SummaryWorkflowCoordinator:
    return SummaryWorkflowCoordinator(
        resolve_period_from_payload=_resolve_period_from_payload,
        apply_preselected_summary_company_selection=_apply_preselected_summary_company_selection,
        apply_single_summary_company_selection=_apply_single_summary_company_selection,
        load_summary_company_choices=_load_summary_company_choices,
        load_summary_collaborator_choices=_load_summary_collaborator_choices,
        summary_status_choices=_summary_status_choices,
        user_can_access_company=_user_can_access_company,
        execute_summary_menu_report=_execute_summary_menu_report,
        format_summary_collaborator_selection_label=_format_summary_collaborator_selection_label,
    )


def _build_summary_execution_handler() -> SummaryWorkflowExecutionHandler:
    from models.company import Company
    from models.employee import Employee

    return SummaryWorkflowExecutionHandler(
        user_can_access_company=_user_can_access_company,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        resolve_period_from_payload=_resolve_period_from_payload,
        load_employee_rows=lambda company_id, employee_ids: (
            Employee.query.filter(
                Employee.company_id == company_id,
                Employee.id.in_(employee_ids),
            ).all()
        ),
        format_summary_collaborator_selection_label=_format_summary_collaborator_selection_label,
        load_project_tasks_report=_load_project_tasks_report,
        load_process_instances_report=_load_process_instances_report,
        load_meetings_report=_load_meetings_report,
        merge_report_items=_merge_report_items,
        format_my_work_report=_format_my_work_report,
    )


def _build_project_task_create_execution_handler() -> ProjectTaskCreateExecutionHandler:
    from services.project_task_service import ProjectTaskService

    return ProjectTaskCreateExecutionHandler(
        resolve_company_ids_for_payload=_resolve_company_ids_for_payload,
        create_project_task=ProjectTaskService.create_project_task,
    )


def _build_project_task_audit_execution_handler() -> ProjectTaskAuditExecutionHandler:
    return ProjectTaskAuditExecutionHandler(
        resolve_company_ids_for_payload=_resolve_company_ids_for_payload,
        load_project_task_audit_rows=_load_project_task_audit_rows,
        format_report=_format_project_task_audit_report,
    )


def _build_project_task_complete_execution_handler() -> ProjectTaskCompleteExecutionHandler:
    from models.company import Company
    from models.project import ProjectTask

    return ProjectTaskCompleteExecutionHandler(
        extract_id_from_code=_extract_id_from_code,
        parse_completion_date=_parse_completion_date,
        today_provider=_local_today,
        load_task_by_id=lambda task_id: db.session.get(ProjectTask, task_id),
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        user_can_access_company=_user_can_access_company,
        commit_changes=lambda: db.session.commit(),
        rollback_changes=lambda: db.session.rollback(),
    )


def _build_project_task_update_execution_handler() -> ProjectTaskUpdateExecutionHandler:
    from models.company import Company
    from models.project import ProjectTask
    from services.project_task_service import ProjectTaskService

    return ProjectTaskUpdateExecutionHandler(
        extract_id_from_code=_extract_id_from_code,
        parse_due_date=ProjectTaskService.parse_due_date,
        load_task_by_id=lambda task_id: db.session.get(ProjectTask, task_id),
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        user_can_access_company=_user_can_access_company,
        commit_changes=lambda: db.session.commit(),
    )


def _build_agent_action_operation_execution_handler() -> AgentActionOperationExecutionHandler:
    from models.agent_action import AgentAction
    from models.project import ProjectTask
    from services.agent_action_backlog_service import find_backlog_link_by_action_id
    from services.backlog_human_gate_service import execute_backlog_human_gate_operation

    def _load_latest_pending_action(user_id: int, active_company_id: Optional[int]) -> Any:
        query = AgentAction.query.filter(
            AgentAction.status.in_(["pending", "awaiting_approval"]),
            AgentAction.user_id == user_id,
        )
        if active_company_id:
            query = query.filter(AgentAction.company_id == active_company_id)
        return query.order_by(AgentAction.created_at.desc()).first()

    return AgentActionOperationExecutionHandler(
        load_action_by_id=lambda action_id: db.session.get(AgentAction, action_id),
        load_latest_pending_action=_load_latest_pending_action,
        find_backlog_link_by_action_id=find_backlog_link_by_action_id,
        load_task_by_id=lambda task_id: db.session.get(ProjectTask, task_id) if task_id else None,
        execute_backlog_human_gate_operation=execute_backlog_human_gate_operation,
        user_can_access_company=_user_can_access_company,
    )


def _build_agent_action_list_pending_execution_handler() -> AgentActionListPendingExecutionHandler:
    from services.agent_action_service import list_pending_actions

    return AgentActionListPendingExecutionHandler(
        resolve_company_ids_for_payload=_resolve_company_ids_for_payload,
        list_pending_actions=list_pending_actions,
    )


def _build_process_instance_complete_execution_handler() -> ProcessInstanceCompleteExecutionHandler:
    from models.company import Company
    from models.process import ProcessInstance

    return ProcessInstanceCompleteExecutionHandler(
        extract_id_from_code=_extract_id_from_code,
        parse_completion_date=_parse_completion_date,
        today_provider=_local_today,
        load_instance_by_id=lambda instance_id: db.session.get(ProcessInstance, instance_id),
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        user_can_access_company=_user_can_access_company,
        commit_changes=lambda: db.session.commit(),
    )


def _build_my_work_execution_handler() -> MyWorkExecutionHandler:
    from src.intelligence.intents import MyWorkIntentFormBuilder

    intent_form_builder = MyWorkIntentFormBuilder()
    return MyWorkExecutionHandler(
        resolve_company_ids_for_payload=_resolve_company_ids_for_payload,
        resolve_employee_ids_for_report=_resolve_employee_ids_for_my_work_report,
        resolve_employee_scope_for_payload=_resolve_employee_scope_for_my_work_payload,
        resolve_period_from_payload=_resolve_period_from_payload,
        load_project_tasks_report=_load_project_tasks_report,
        load_process_instances_report=_load_process_instances_report,
        load_meetings_report=_load_meetings_report,
        format_my_work_report=_format_my_work_report,
        build_operational_form=lambda action, payload, active_company_id, channel: intent_form_builder.build(
            action=action,
            payload=payload,
            active_company_id=active_company_id,
            channel=channel,
        ),
    )


def _build_routine_consult_execution_handler() -> RoutineConsultExecutionHandler:
    from src.intelligence.intents import RoutineConsultIntentFormBuilder

    intent_form_builder = RoutineConsultIntentFormBuilder()
    my_work_handler = _build_my_work_execution_handler()
    return RoutineConsultExecutionHandler(
        build_operational_form=lambda action, payload, active_company_id, channel: intent_form_builder.build(
            action=action,
            payload=payload,
            active_company_id=active_company_id,
            channel=channel,
        ),
        execute_my_work=my_work_handler.execute,
    )


def _format_company_access_report(*, companies: List[Any], channel: str = "web") -> str:
    total = len(companies or [])
    if total <= 0:
        return "Nenhuma empresa vinculada ao seu usuário."

    lines = [
        f"Atualmente, voce possui acesso a {total} empresa(s) ativa(s).",
        "",
        "Empresas vinculadas:",
    ]
    for index, company in enumerate(companies, start=1):
        prefix = str(getattr(company, "client_code", "") or "").strip() or "SEM PREFIXO"
        name = str(getattr(company, "name", "") or f"Empresa {getattr(company, 'id', '-')}")
        company_id = getattr(company, "id", None)
        line = f"{index}. {prefix} - {name}"
        if company_id is not None:
            line = f"{line} (ID: {company_id})"
        lines.append(line)

    if str(channel or "web").strip().lower() == "whatsapp":
        lines.extend(
            [
                "",
                "Proximo passo:",
                "→ Se quiser, posso detalhar atividades, instancias ou pendencias de uma dessas empresas.",
            ]
        )
    return "\n".join(lines)


def _build_company_access_execution_handler() -> CompanyAccessExecutionHandler:
    return CompanyAccessExecutionHandler(
        load_accessible_companies_for_user=_load_accessible_companies_for_user,
        format_report=_format_company_access_report,
    )


def _build_collaborator_occupancy_execution_handler() -> CollaboratorOccupancyExecutionHandler:
    from decimal import Decimal

    from models.activity_work_log import ActivityWorkLog
    from models.employee import Employee
    from models.project import Project, ProjectTask

    def _resolve_employee_for_company(company_id: int, collaborator_term: str):
        normalized_term = _normalize_text(collaborator_term)
        employees = (
            Employee.query.filter(
                Employee.company_id == company_id,
                Employee.status == "active",
            )
            .order_by(Employee.name.asc())
            .all()
        )
        if not employees:
            return None, "Nenhum colaborador ativo encontrado para a empresa selecionada."

        matches = []
        for employee in employees:
            haystack = _normalize_text(
                f"{getattr(employee, 'name', '')} {getattr(employee, 'email', '')} {getattr(employee, 'department', '')}"
            )
            score = 0
            if normalized_term and normalized_term == _normalize_text(getattr(employee, "name", "")):
                score += 10
            if normalized_term and normalized_term in haystack:
                score += 4
            if normalized_term and all(token in haystack for token in normalized_term.split() if token):
                score += 2
            if score > 0:
                matches.append((score, employee))

        if not matches:
            names = ", ".join(emp.name for emp in employees[:8])
            return None, f"Nao encontrei colaborador para '{collaborator_term}'. Colaboradores ativos: {names}"

        matches.sort(key=lambda item: (-item[0], str(item[1].name or "").lower(), item[1].id))
        top_score = matches[0][0]
        top_matches = [employee for score, employee in matches if score == top_score]
        if len(top_matches) > 1:
            names = ", ".join(emp.name for emp in top_matches[:8])
            return None, f"Encontrei mais de um colaborador para '{collaborator_term}': {names}"
        return top_matches[0], None

    def _business_days_between(start_date: date, end_date: date) -> int:
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        total = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                total += 1
            current += timedelta(days=1)
        return total

    def _calculate_available_hours(employee: Any, start_date: date, end_date: date) -> float:
        weekly_hours = float(getattr(employee, "weekly_hours", 0) or 40.0)
        daily_capacity = weekly_hours / 5.0 if weekly_hours else 0.0
        return round(daily_capacity * _business_days_between(start_date, end_date), 2)

    def _sum_activity_hours(employee: Any, start_date: date, end_date: date, activity_types: List[str]) -> float:
        total = (
            db.session.query(func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0))
            .filter(
                ActivityWorkLog.employee_id == employee.id,
                ActivityWorkLog.activity_type.in_(activity_types),
                ActivityWorkLog.work_date >= start_date,
                ActivityWorkLog.work_date <= end_date,
            )
            .scalar()
        )
        return float(total or 0.0)

    def _load_project_hours_committed(employee: Any, start_date: date, end_date: date) -> float:
        tasks = (
            db.session.query(ProjectTask)
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(Project.company_id == employee.company_id)
            .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
            .filter(ProjectTask.stage != "completed")
            .all()
        )
        total = Decimal("0")
        for task in tasks:
            assigned = False
            if getattr(task, "employee_id", None) and int(task.employee_id) == int(employee.id):
                assigned = True
            if not assigned:
                for collaborator in getattr(task, "collaborators", []) or []:
                    if getattr(collaborator, "is_deleted", False):
                        continue
                    if int(getattr(collaborator, "employee_id", 0) or 0) == int(employee.id):
                        assigned = True
                        break
            if not assigned:
                continue
            due_date = getattr(task, "due_date", None)
            if due_date and (due_date < start_date or due_date > end_date):
                continue
            total += Decimal(str(getattr(task, "estimated_hours", 0) or 0))
        return float(total)

    def _format_report(**kwargs):
        return build_collaborator_occupancy_report(
            **kwargs,
            format_date_br=_format_date_br,
        )

    return CollaboratorOccupancyExecutionHandler(
        resolve_single_company_for_operation=_resolve_single_company_for_operation,
        resolve_period_from_payload=_resolve_period_from_payload,
        resolve_employee_for_company=_resolve_employee_for_company,
        calculate_available_hours=_calculate_available_hours,
        load_process_hours_taken=lambda employee, start_date, end_date: _sum_activity_hours(
            employee, start_date, end_date, ["process", "process_instance"]
        ),
        load_project_hours_taken=lambda employee, start_date, end_date: _sum_activity_hours(
            employee, start_date, end_date, ["project"]
        ),
        load_project_hours_committed=_load_project_hours_committed,
        format_report=_format_report,
    )


def _build_onboarding_status_execution_handler() -> OnboardingStatusExecutionHandler:
    from models.company import Company

    return OnboardingStatusExecutionHandler(
        resolve_single_company_for_operation=_resolve_single_company_for_operation,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
    )


def _build_onboarding_go_live_check_execution_handler() -> OnboardingGoLiveCheckExecutionHandler:
    from models.company import Company
    from models.employee import Employee
    from models.project import Project, ProjectTask
    from models.process import Process, ProcessInstance
    from models.meeting import Meeting

    def _load_operational_metrics(company_id: int) -> Dict[str, int]:
        active_employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
        ).count()
        employees_with_any_contact = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
            or_(
                _has_text_expr(Employee.telegram),
                _has_text_expr(Employee.whatsapp),
                _has_text_expr(Employee.email),
            ),
        ).count()
        projects_count = Project.query.filter(Project.company_id == company_id).count()
        open_tasks_count = (
            db.session.query(ProjectTask)
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(Project.company_id == company_id)
            .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
            .count()
        )
        processes_count = Process.query.filter(Process.company_id == company_id).count()
        open_instances_count = ProcessInstance.query.filter(
            ProcessInstance.company_id == company_id,
            ProcessInstance.status != "completed",
        ).count()
        meetings_count = Meeting.query.filter(Meeting.company_id == company_id).count()
        return {
            "active_employees": active_employees,
            "employees_with_any_contact": employees_with_any_contact,
            "projects_count": projects_count,
            "open_tasks_count": open_tasks_count,
            "processes_count": processes_count,
            "open_instances_count": open_instances_count,
            "meetings_count": meetings_count,
        }

    return OnboardingGoLiveCheckExecutionHandler(
        resolve_single_company_for_operation=_resolve_single_company_for_operation,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        load_operational_metrics=_load_operational_metrics,
    )


def _build_onboarding_start_execution_handler() -> OnboardingStartExecutionHandler:
    from models.cadastro_session import CadastroSession

    return OnboardingStartExecutionHandler(
        resolve_single_company_for_operation=_resolve_single_company_for_operation,
        create_session=lambda user_id, onboarding_type, company_id: CadastroSession.criar_sessao(
            user_id=user_id,
            tipo_cadastro=onboarding_type,
            empresa_id=company_id,
        ),
    )


def _build_onboarding_diagnose_execution_handler() -> OnboardingDiagnoseExecutionHandler:
    from models.company import Company
    from models.employee import Employee
    from models.role import Role
    from models.project import Project, ProjectTask
    from models.process import Process, ProcessInstance
    from models.meeting import Meeting

    def _load_diagnostic_metrics(company_id: int) -> Dict[str, int]:
        active_employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
        ).count()
        roles_count = Role.query.filter(Role.company_id == company_id).count()
        projects_count = Project.query.filter(Project.company_id == company_id).count()
        open_tasks_count = (
            db.session.query(ProjectTask)
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(Project.company_id == company_id)
            .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
            .count()
        )
        processes_count = Process.query.filter(Process.company_id == company_id).count()
        open_instances_count = ProcessInstance.query.filter(
            ProcessInstance.company_id == company_id,
            ProcessInstance.status != "completed",
        ).count()
        meetings_count = Meeting.query.filter(Meeting.company_id == company_id).count()
        employees_with_telegram = Employee.query.filter(
            Employee.company_id == company_id,
            _has_text_expr(Employee.telegram),
        ).count()
        employees_with_whatsapp = Employee.query.filter(
            Employee.company_id == company_id,
            _has_text_expr(Employee.whatsapp),
        ).count()
        employees_with_email = Employee.query.filter(
            Employee.company_id == company_id,
            _has_text_expr(Employee.email),
        ).count()
        employees_with_any_contact = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
            or_(
                _has_text_expr(Employee.telegram),
                _has_text_expr(Employee.whatsapp),
                _has_text_expr(Employee.email),
            ),
        ).count()
        return {
            "active_employees": active_employees,
            "roles_count": roles_count,
            "projects_count": projects_count,
            "open_tasks_count": open_tasks_count,
            "processes_count": processes_count,
            "open_instances_count": open_instances_count,
            "meetings_count": meetings_count,
            "employees_with_telegram": employees_with_telegram,
            "employees_with_whatsapp": employees_with_whatsapp,
            "employees_with_email": employees_with_email,
            "employees_with_any_contact": employees_with_any_contact,
        }

    return OnboardingDiagnoseExecutionHandler(
        resolve_single_company_for_operation=_resolve_single_company_for_operation,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
        normalize_objective=_normalize_objective,
        format_objective_label=_format_objective_label,
        load_diagnostic_metrics=_load_diagnostic_metrics,
    )


def _build_meeting_schedule_execution_handler() -> MeetingScheduleExecutionHandler:
    import json

    from models.company import Company
    from models.meeting import Meeting

    def _create_draft_meeting(
        *,
        company_id: int,
        title: str,
        scheduled_date: date,
        scheduled_time: str,
        notes: str,
        guest_dict: Dict[str, str],
        agenda: List[Dict[str, Any]],
    ):
        try:
            meeting = Meeting(
                company_id=company_id,
                title=title,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                invite_notes=notes,
                guests_json=json.dumps(guest_dict, ensure_ascii=False),
                agenda_json=json.dumps(agenda, ensure_ascii=False),
                status="draft",
            )
            db.session.add(meeting)
            db.session.commit()
            return meeting, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao agendar reuniao: {str(exc)}"

    return MeetingScheduleExecutionHandler(
        resolve_company_ids_for_payload=_resolve_company_ids_for_payload,
        parse_meeting_datetime_input=_parse_meeting_datetime_input,
        create_draft_meeting=_create_draft_meeting,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
    )


def _build_meeting_start_execution_handler() -> MeetingStartExecutionHandler:
    from models.company import Company
    from models.meeting import Meeting
    from models.project import Project

    def _ensure_linked_project(meeting: Any, started_at: datetime):
        if getattr(meeting, "project_id", None):
            return None, None
        try:
            project = Project(
                company_id=meeting.company_id,
                name=f"Reuniao - {meeting.title} ({started_at.strftime('%d/%m/%Y')})",
                status="in_progress",
                priority="medium",
                owner="Sapiens",
                deadline=started_at.date(),
                notes=f"Projeto gerado automaticamente para a reuniao ID {meeting.id}: {meeting.title}",
            )
            db.session.add(project)
            db.session.flush()
            meeting.project_id = project.id
            return project, None
        except Exception as exc:
            return None, f"Erro ao iniciar reuniao: {str(exc)}"

    return MeetingStartExecutionHandler(
        load_meeting_by_id=lambda meeting_id: db.session.get(Meeting, meeting_id),
        user_can_access_company=_user_can_access_company,
        now_provider=_local_now,
        ensure_linked_project=_ensure_linked_project,
        commit_changes=db.session.commit,
        rollback_changes=db.session.rollback,
        load_company_by_id=lambda company_id: db.session.get(Company, company_id),
    )


def _build_meeting_summarize_execution_handler() -> MeetingSummarizeExecutionHandler:
    from models.meeting import Meeting

    return MeetingSummarizeExecutionHandler(
        load_meeting_by_id=lambda meeting_id: db.session.get(Meeting, meeting_id),
        user_can_access_company=_user_can_access_company,
    )


def _build_meeting_close_execution_handler() -> MeetingCloseExecutionHandler:
    from models.meeting import Meeting

    return MeetingCloseExecutionHandler(
        load_meeting_by_id=lambda meeting_id: db.session.get(Meeting, meeting_id),
        user_can_access_company=_user_can_access_company,
        now_provider=_local_now,
        commit_changes=db.session.commit,
        rollback_changes=db.session.rollback,
    )


def _build_meeting_send_summary_email_execution_handler() -> MeetingSendSummaryEmailExecutionHandler:
    from models.meeting import Meeting
    from services.email_service import email_service

    def _build_summary_text(meeting_id: int, active_company_id: Optional[int], user_id: int) -> str:
        result = _build_meeting_summarize_execution_handler().execute(
            MeetingSummarizeRequest(
                payload={"id_reuniao": str(meeting_id)},
                active_company_id=active_company_id,
                user_id=user_id,
            )
        )
        return result.response_text

    return MeetingSendSummaryEmailExecutionHandler(
        load_meeting_by_id=lambda meeting_id: db.session.get(Meeting, meeting_id),
        user_can_access_company=_user_can_access_company,
        build_summary_text=_build_summary_text,
        send_email=lambda to_emails, subject, body: email_service.send_email(to_emails, subject, body),
    )


def _build_meeting_send_summary_whatsapp_execution_handler() -> MeetingSendSummaryWhatsAppExecutionHandler:
    from models.meeting import Meeting
    from services.whatsapp_service import whatsapp_service

    def _build_summary_text(meeting_id: int, active_company_id: Optional[int], user_id: int) -> str:
        result = _build_meeting_summarize_execution_handler().execute(
            MeetingSummarizeRequest(
                payload={"id_reuniao": str(meeting_id)},
                active_company_id=active_company_id,
                user_id=user_id,
            )
        )
        return result.response_text

    return MeetingSendSummaryWhatsAppExecutionHandler(
        load_meeting_by_id=lambda meeting_id: db.session.get(Meeting, meeting_id),
        user_can_access_company=_user_can_access_company,
        build_summary_text=_build_summary_text,
        send_whatsapp=whatsapp_service.send_message,
    )


def _build_financial_receipt_ingest_execution_handler() -> FinancialReceiptIngestExecutionHandler:
    from flask import current_app

    from services.financial_automation_channel_service import FinancialAutomationChannelService

    return FinancialReceiptIngestExecutionHandler(
        upload_root_provider=lambda: current_app.config.get("UPLOAD_FOLDER", "uploads"),
        stage_channel_document=FinancialAutomationChannelService.stage_channel_document,
    )


def _apply_summary_route_decision(
    session: AgentMenuSession,
    option: AgentMenuOption,
    decision,
    *,
    push_history: bool = True,
) -> MenuInterceptResult:
    if not decision or not getattr(decision, "handled", False):
        return MenuInterceptResult()

    route = str(getattr(decision, "route", "") or "")
    payload = dict(getattr(decision, "payload", {}) or {})
    status = getattr(decision, "status", None)
    response_text = getattr(decision, "response_text", None)
    report_text = getattr(decision, "report_text", None)

    if route == SUMMARY_ROUTE_RESET:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text=response_text or "Sessao de resumo reiniciada. Digite 'menu' para continuar.",
        )

    if route == SUMMARY_ROUTE_ERROR:
        if status:
            _transition_session_state(
                session=session,
                status=status,
                payload=payload,
                missing_fields=[],
                push_history=False,
            )
        return MenuInterceptResult(
            handled=True,
            response_text=response_text or "Nao consegui processar o resumo agora.",
        )

    if route == SUMMARY_ROUTE_PROMPT_DATES:
        _transition_session_state(
            session=session,
            status=status or SUMMARY_STATUS_AWAITING_DATES,
            payload=payload,
            missing_fields=[],
            push_history=push_history,
        )
        return MenuInterceptResult(
            handled=True,
            response_text=_format_summary_period_prompt(option, session.channel or "web"),
        )

    if route == SUMMARY_ROUTE_PROMPT_COMPANY:
        choices = payload.get("_summary_company_choices") or []
        _transition_session_state(
            session=session,
            status=status or "awaiting_summary_company",
            payload=payload,
            missing_fields=[],
            push_history=push_history,
        )
        prompt = _format_summary_company_prompt(option, choices, session.channel or "web")
        if response_text:
            prompt = f"{response_text}\n\n{prompt}"
        return MenuInterceptResult(handled=True, response_text=prompt)

    if route == SUMMARY_ROUTE_PROMPT_COLLABORATOR:
        choices = payload.get("_summary_collaborator_choices") or []
        _transition_session_state(
            session=session,
            status=status or "awaiting_summary_collaborator",
            payload=payload,
            missing_fields=[],
            push_history=push_history,
        )
        return MenuInterceptResult(
            handled=True,
            response_text=_format_summary_collaborator_prompt(option, choices, session.channel or "web"),
        )

    if route == SUMMARY_ROUTE_PROMPT_STATUS:
        choices = payload.get("_summary_status_choices") or _summary_status_choices()
        _transition_session_state(
            session=session,
            status=status or "awaiting_summary_status",
            payload=payload,
            missing_fields=[],
            push_history=push_history,
        )
        return MenuInterceptResult(
            handled=True,
            response_text=_format_summary_status_prompt(option, choices, session.channel or "web"),
        )

    if route == SUMMARY_ROUTE_EMAIL_CONFIRMATION:
        _transition_session_state(
            session=session,
            status=status or SUMMARY_EMAIL_CONFIRM_STATUS,
            payload=payload,
            missing_fields=[],
            push_history=push_history,
        )
        final_report = report_text or ""
        return MenuInterceptResult(
            handled=True,
            response_text=f"{final_report}\n\n{SUMMARY_EMAIL_OFFER_SUFFIX}",
        )

    if route == SUMMARY_ROUTE_COMPLETED:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text=report_text or response_text or "",
        )

    return MenuInterceptResult()


def _prompt_summary_company_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    coordinator = _build_summary_workflow_coordinator()
    state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(payload)
    decision = coordinator.prepare_company_prompt(state)
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
    )


def _apply_single_summary_company_selection(
    payload: Dict[str, Any],
    choices: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if len(choices or []) != 1:
        return None

    selected = choices[0] or {}
    company_id = selected.get("company_id")
    if not company_id:
        return None

    updated_payload = dict(payload or {})
    updated_payload["_summary_company_id"] = int(company_id)
    updated_payload["_summary_company_label"] = selected.get("label")
    updated_payload["empresa"] = selected.get("company_name")
    return updated_payload


def _apply_preselected_summary_company_selection(
    payload: Dict[str, Any],
    user_id: int,
    choices: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    explicit_company_id = _resolve_explicit_company_id_from_payload(
        payload=payload,
        user_id=user_id,
    )
    if not explicit_company_id:
        return None

    available_choices = list(choices or payload.get("_summary_company_choices") or _load_summary_company_choices(user_id=user_id))
    selected = next(
        (item for item in available_choices if int(item.get("company_id", -1)) == int(explicit_company_id)),
        None,
    )
    if not selected:
        return None

    updated_payload = dict(payload or {})
    updated_payload["_summary_company_choices"] = available_choices
    updated_payload["_summary_company_id"] = int(explicit_company_id)
    updated_payload["_summary_company_label"] = selected.get("label")
    updated_payload["empresa"] = selected.get("company_name")
    return updated_payload


def _prompt_summary_collaborator_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    coordinator = _build_summary_workflow_coordinator()
    state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(payload)
    decision = coordinator.prepare_collaborator_prompt(state)
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
    )


def _prompt_summary_status_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    coordinator = _build_summary_workflow_coordinator()
    state = WorkflowSessionState.from_agent_menu_session(
        session,
        workflow_code=option.code,
        workflow_action_key=option.action_key,
    ).with_payload(payload)
    decision = coordinator.prepare_status_prompt(state)
    return _apply_summary_route_decision(
        session=session,
        option=option,
        decision=decision,
    )


def _load_summary_company_choices(user_id: int) -> List[Dict[str, Any]]:
    from models.company import Company

    company_ids, _ = _resolve_company_ids_for_payload(
        payload={},
        active_company_id=None,
        user_id=user_id,
    )
    if not company_ids:
        return []

    companies = (
        Company.query.filter(
            Company.id.in_(company_ids),
            Company.is_active.is_(True),
        )
        .order_by(Company.name.asc())
        .all()
    )
    choices: List[Dict[str, Any]] = []
    for idx, company in enumerate(companies, start=1):
        label = (
            f"{company.client_code} - {company.name}"
            if company.client_code else
            company.name
        )
        choices.append(
            {
                "index": idx,
                "company_id": company.id,
                "company_name": company.name,
                "company_code": company.client_code or "",
                "label": label,
            }
        )
    return choices


def _load_summary_collaborator_choices(company_id: int) -> List[Dict[str, Any]]:
    from models.employee import Employee

    rows = (
        Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
        )
        .order_by(Employee.name.asc(), Employee.id.asc())
        .all()
    )
    choices: List[Dict[str, Any]] = []
    for idx, employee in enumerate(rows, start=1):
        name = str(employee.name or f"Colaborador {employee.id}").strip()
        email = str(employee.email or "").strip()
        label = f"{name} ({email})" if email else name
        choices.append(
            {
                "index": idx,
                "employee_id": employee.id,
                "name": name,
                "email": email,
                "label": label,
            }
        )
    return choices


def _summary_status_choices() -> List[Dict[str, Any]]:
    return [
        {"index": 1, "key": "open", "label": "Abertas"},
        {"index": 2, "key": "completed", "label": "Concluidas"},
        {"index": 3, "key": "all", "label": "Todas"},
    ]


def _format_summary_company_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
    channel: str = "web",
) -> str:
    return build_summary_company_prompt(
        _build_workflow_display_option(option),
        choices,
        channel=channel,
    )


def _format_operation_company_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
    channel: str = "web",
) -> str:
    return build_operation_company_prompt(
        _build_workflow_display_option(option),
        choices,
        channel=channel,
    )


def _format_summary_collaborator_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
    channel: str = "web",
) -> str:
    return build_summary_collaborator_prompt(
        _build_workflow_display_option(option),
        choices,
        channel=channel,
    )


def _format_summary_status_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
    channel: str = "web",
) -> str:
    return build_summary_status_prompt(
        _build_workflow_display_option(option),
        choices,
        channel=channel,
    )


def _extract_selection_index(text: str) -> Optional[int]:
    parsed = _parse_selection_number_date(text)
    if not parsed:
        return None
    idx, right = parsed
    if right:
        return None
    return idx


def _extract_selection_indexes(
    text: str,
    *,
    allow_zero: bool = False,
) -> Optional[List[int]]:
    raw = str(text or "").strip()
    if not raw:
        return None

    normalized = re.sub(r"\s+e\s+", ",", raw, flags=re.IGNORECASE)
    normalized = normalized.replace(";", ",")
    normalized = re.sub(r"\s+", ",", normalized)
    normalized = re.sub(r",+", ",", normalized).strip(",")
    if not normalized:
        return None
    if not re.fullmatch(r"\d{1,3}(?:,\d{1,3})*", normalized):
        return None

    parsed: List[int] = []
    seen = set()
    for token in normalized.split(","):
        idx = int(token)
        if idx < 0:
            return None
        if idx == 0 and not allow_zero:
            return None
        if idx in seen:
            continue
        seen.add(idx)
        parsed.append(idx)
    return parsed or None


def _format_summary_collaborator_selection_label(
    names: List[str],
    *,
    all_selected: bool = False,
) -> str:
    if all_selected:
        return "Todos os colaboradores"

    clean_names = [str(name or "").strip() for name in (names or []) if str(name or "").strip()]
    if not clean_names:
        return "Colaboradores selecionados"
    if len(clean_names) == 1:
        return clean_names[0]
    if len(clean_names) == 2:
        return f"{clean_names[0]} e {clean_names[1]}"
    if len(clean_names) == 3:
        return f"{clean_names[0]}, {clean_names[1]} e {clean_names[2]}"
    return f"{clean_names[0]}, {clean_names[1]}, {clean_names[2]} e mais {len(clean_names) - 3}"


def _load_open_choices(
    action: str,
    company_id: Optional[int],
    user_id: int,
) -> Dict[str, Any]:
    company_ids = _resolve_company_scope(company_id=company_id, user_id=user_id)
    if not company_ids:
        return {"choices": []}

    if action == "project_task.complete":
        return _load_open_project_task_choices(company_ids=company_ids)
    if action == "process_instance.complete":
        return _load_open_process_instance_choices(company_ids=company_ids)
    if action in {"meeting.start", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}:
        return _load_meeting_choices(company_ids=company_ids, mode="start")
    if action == "meeting.summarize":
        return _load_meeting_choices(company_ids=company_ids, mode="summarize")
    if action == "onboarding.diagnose":
        return _load_onboarding_diagnose_choices()
    return {"choices": []}


def _load_assisted_field_selection(
    action: str,
    field_key: str,
    company_id: Optional[int],
    user_id: int,
) -> Dict[str, Any]:
    company_ids = _resolve_company_scope(company_id=company_id, user_id=user_id)
    if not company_ids:
        return {"choices": []}

    normalized_field = _slugify(field_key)
    if normalized_field == "codigo_projeto" and action in {"project.update", "project.complete", "project_task.create"}:
        return _load_active_project_choices(company_ids=company_ids)

    return {"choices": []}


def _resolve_company_scope(company_id: Optional[int], user_id: int) -> List[int]:
    if company_id:
        return [company_id]

    from models.employee import Employee
    company_ids = [
        emp.company_id
        for emp in Employee.query.filter(Employee.user_id == user_id).all()
        if emp.company_id
    ]
    # Remove duplicatas preservando ordem
    seen = set()
    result: List[int] = []
    for cid in company_ids:
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def _load_active_project_choices(company_ids: List[int]) -> Dict[str, Any]:
    from models.project import Project
    from models.company import Company

    rows = (
        db.session.query(Project, Company)
        .join(Company, Company.id == Project.company_id)
        .filter(Project.company_id.in_(company_ids))
        .filter(or_(Project.status.is_(None), ~Project.status.in_(["completed", "cancelled"])))
        .order_by(Project.deadline.asc().nullslast(), Project.id.asc())
        .limit(30)
        .all()
    )

    choices = []
    company_names = []
    for idx, (project, company) in enumerate(rows, start=1):
        company_code = company.client_code or "CP"
        project_code = f"{company_code}.J.{project.id}"
        deadline_str = project.deadline.isoformat() if getattr(project, "deadline", None) else "-"
        choices.append({
            "index": idx,
            "id": project.id,
            "company_id": company.id,
            "company_name": company.name,
            "code": project_code,
            "title": project.name,
            "status": project.status or "planned",
            "progress": int(project.progress or 0),
            "due_date": deadline_str,
        })
        company_names.append(company.name)

    scope_label = _build_scope_label(company_names)
    return {
        "choices": choices,
        "scope_label": scope_label,
        "item_label_plural": "projetos",
        "selection_kind": "project_picker",
        "field_key": "codigo_projeto",
        "value_key": "code",
    }


def _load_open_project_task_choices(company_ids: List[int]) -> Dict[str, Any]:
    from models.project import ProjectTask, Project
    from models.company import Company

    rows = (
        db.session.query(ProjectTask, Project, Company)
        .join(Project, Project.id == ProjectTask.project_id)
        .join(Company, Company.id == Project.company_id)
        .filter(Project.company_id.in_(company_ids))
        .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
        .filter(ProjectTask.stage != "completed")
        .order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc())
        .limit(30)
        .all()
    )

    choices = []
    company_names = []
    for idx, (task, project, company) in enumerate(rows, start=1):
        company_code = company.client_code or "CP"
        project_code = f"{company_code}.J.{project.id}"
        activity_code = f"{project_code}.{task.id}"
        due_str = task.due_date.isoformat() if getattr(task, "due_date", None) else "-"
        choices.append({
            "index": idx,
            "id": task.id,
            "company_id": company.id,
            "company_name": company.name,
            "code": activity_code,
            "title": task.what,
            "project_code": project_code,
            "project_name": project.name,
            "due_date": due_str,
        })
        company_names.append(company.name)

    scope_label = _build_scope_label(company_names)
    return {
        "choices": choices,
        "scope_label": scope_label,
        "item_label_plural": "atividades",
    }


def _load_open_process_instance_choices(company_ids: List[int]) -> Dict[str, Any]:
    from models.process import ProcessInstance, Process
    from models.company import Company

    rows = (
        db.session.query(ProcessInstance, Process, Company)
        .join(Process, Process.id == ProcessInstance.process_id)
        .join(Company, Company.id == ProcessInstance.company_id)
        .filter(ProcessInstance.company_id.in_(company_ids))
        .filter(ProcessInstance.status != "completed")
        .order_by(ProcessInstance.due_date.asc().nullslast(), ProcessInstance.id.asc())
        .limit(30)
        .all()
    )

    choices = []
    company_names = []
    for idx, (inst, proc, company) in enumerate(rows, start=1):
        company_code = company.client_code or "CP"
        process_code = proc.code or f"{company_code}.C.{proc.id}"
        instance_code = inst.instance_code or f"{process_code}.{inst.id}"
        due_str = inst.due_date.isoformat() if getattr(inst, "due_date", None) else "-"
        choices.append({
            "index": idx,
            "id": inst.id,
            "company_id": company.id,
            "company_name": company.name,
            "code": instance_code,
            "title": inst.title or proc.name,
            "process_code": process_code,
            "due_date": due_str,
        })
        company_names.append(company.name)

    scope_label = _build_scope_label(company_names)
    return {
        "choices": choices,
        "scope_label": scope_label,
        "item_label_plural": "instancias de processo",
    }


def _load_meeting_choices(company_ids: List[int], mode: str) -> Dict[str, Any]:
    from models.meeting import Meeting
    from models.company import Company

    base_query = (
        db.session.query(Meeting, Company)
        .join(Company, Company.id == Meeting.company_id)
        .filter(Meeting.company_id.in_(company_ids))
    )

    rows = []
    if mode == "start":
        rows = (
            base_query
            .filter(Meeting.status != "completed")
            .filter(Meeting.scheduled_date.isnot(None))
            .order_by(
                Meeting.scheduled_date.asc(),
                Meeting.scheduled_time.asc().nullslast(),
                Meeting.id.asc(),
            )
            .limit(30)
            .all()
        )
        # Fallback: se não houver reuniões com data definida, mostra um conjunto reduzido.
        if not rows:
            rows = (
                base_query
                .filter(Meeting.status != "completed")
                .order_by(Meeting.updated_at.desc().nullslast(), Meeting.id.desc())
                .limit(12)
                .all()
            )
    else:
        content_filter = _build_meeting_content_filter(Meeting)
        rows = (
            base_query
            .filter(
                or_(
                    Meeting.status.in_(["in_progress", "completed"]),
                    Meeting.scheduled_date.isnot(None),
                    content_filter,
                )
            )
            .order_by(
                Meeting.scheduled_date.asc().nullslast(),
                Meeting.scheduled_time.asc().nullslast(),
                Meeting.updated_at.desc().nullslast(),
                Meeting.id.desc(),
            )
            .limit(30)
            .all()
        )
        if not rows:
            rows = (
                base_query
                .order_by(Meeting.updated_at.desc().nullslast(), Meeting.id.desc())
                .limit(12)
                .all()
            )

    choices: List[Dict[str, Any]] = []
    company_names: List[str] = []
    for idx, (meeting, company) in enumerate(rows, start=1):
        date_str = meeting.scheduled_date.isoformat() if meeting.scheduled_date else "-"
        time_str = meeting.scheduled_time or "-"
        choices.append({
            "index": idx,
            "id": meeting.id,
            "company_id": company.id,
            "company_name": company.name,
            "code": str(meeting.id),
            "title": meeting.title,
            "status": meeting.status or "draft",
            "scheduled_date": date_str,
            "scheduled_time": time_str,
        })
        company_names.append(company.name)

    scope_label = _build_scope_label(company_names)
    return {
        "choices": choices,
        "scope_label": scope_label,
        "item_label_plural": "reunioes",
    }


def _load_onboarding_diagnose_choices() -> Dict[str, Any]:
    raw_options = [
        ("reunioes", "Reunioes"),
        ("afazeres", "Afazeres e Projetos"),
        ("processos", "Processos"),
        ("telegram", "Canal Telegram"),
        ("whatsapp", "Canal WhatsApp"),
        ("onboarding", "Onboarding Geral"),
    ]
    choices: List[Dict[str, Any]] = []
    for idx, (code, label) in enumerate(raw_options, start=1):
        choices.append({
            "index": idx,
            "id": idx,
            "code": code,
            "title": label,
            "objective": code,
        })
    return {
        "choices": choices,
        "scope_label": "empresa ativa",
        "item_label_plural": "objetivos de diagnostico",
    }


def _build_meeting_content_filter(meeting_model: Any):
    return or_(
        and_(meeting_model.meeting_notes.isnot(None), meeting_model.meeting_notes != ""),
        and_(
            meeting_model.discussions_json.isnot(None),
            meeting_model.discussions_json.notin_(["", "[]", "{}"]),
        ),
        and_(
            meeting_model.activities_json.isnot(None),
            meeting_model.activities_json.notin_(["", "[]", "{}"]),
        ),
    )


def _has_text_expr(column: Any):
    return and_(column.isnot(None), func.length(func.trim(column)) > 0)


def _build_scope_label(company_names: List[str]) -> str:
    unique = []
    seen = set()
    for name in company_names:
        if name not in seen:
            seen.add(name)
            unique.append(name)

    if not unique:
        return "empresa ativa"
    if len(unique) == 1:
        return f"empresa {unique[0]}"
    return "empresas vinculadas"


def _user_can_access_company(user_id: int, company_id: Optional[int]) -> bool:
    if not company_id:
        return False
    try:
        from models.company import Company
        from models.user import User
        from models.employee import Employee
        company = Company.query.get(company_id)
        if not company or not bool(getattr(company, "is_active", True)):
            return False
        user = User.query.get(user_id)
        if not user:
            return False
        if str(getattr(user, "role", "")).lower() == "admin":
            return True
        return Employee.query.filter(
            Employee.user_id == user_id,
            Employee.company_id == company_id
        ).first() is not None
    except Exception:
        return False


def _build_execution_prompt(
    option: AgentMenuOption,
    payload: Dict[str, Any],
    original_user_text: str,
) -> str:
    payload_str = json.dumps(payload, ensure_ascii=False, indent=2)

    if option.execution_template:
        return option.execution_template.format(
            code=option.code,
            title=option.title,
            action_key=option.action_key or "",
            payload=payload_str,
            user_message=original_user_text,
        )

    return (
        f"[MENU_EXECUTION]\n"
        f"codigo_menu: {option.code}\n"
        f"acao: {option.action_key or option.code}\n"
        f"titulo: {option.title}\n"
        f"dados: {payload_str}\n"
        f"pedido_original: {original_user_text}\n"
        "Execute a acao com as ferramentas MCP disponiveis e confirme o resultado."
    )


def _try_execute_direct_option_result(
    option: AgentMenuOption,
    payload: Dict[str, Any],
    company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> DirectExecutionResult:
    """Executa ação determinística e devolve resultado estruturado com metadata."""
    dispatcher = _build_direct_execution_dispatcher()
    return dispatcher.execute(
        DirectExecutionRequest(
            action_key=option.action_key,
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
            channel=channel,
        )
    )


def _execute_option_with_payload(
    *,
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    effective_company_id = _resolve_effective_company_id_for_payload(
        payload=payload,
        fallback_company_id=session.company_id,
        user_id=session.user_id,
    )
    direct_execution = _try_execute_direct_option_result(
        option=option,
        payload=payload,
        company_id=effective_company_id,
        user_id=session.user_id,
        channel=session.channel or "web",
    )
    _reset_session(session)
    if direct_execution.executed:
        return MenuInterceptResult(
            handled=True,
            response_text=direct_execution.response_text,
            metadata=dict(direct_execution.metadata or {}),
        )
    return MenuInterceptResult(
        handled=False,
        override_message=_build_execution_prompt(option, payload, str(session.last_user_message or "")),
    )


def _try_execute_direct_option(
    option: AgentMenuOption,
    payload: Dict[str, Any],
    company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> Optional[str]:
    """
    Execução direta para ações críticas/repetitivas, reduzindo variação do LLM.
    Retorna texto de resposta quando executado; None para seguir fluxo via LLM.
    """
    result = _try_execute_direct_option_result(
        option=option,
        payload=payload,
        company_id=company_id,
        user_id=user_id,
        channel=channel,
    )
    if not result.executed:
        return None
    return result.response_text


def execute_approved_resume_payload(resume_payload: Dict[str, Any]) -> DirectExecutionResult:
    """Executa payload previamente aprovado, contornando nova exigência de aprovação por canal."""
    action_key = str((resume_payload or {}).get("action_key") or "").strip().lower()
    user_id = (resume_payload or {}).get("user_id")
    active_company_id = (resume_payload or {}).get("active_company_id")
    payload = dict((resume_payload or {}).get("payload") or {})
    requested_channel = str((resume_payload or {}).get("channel") or "web").strip().lower()

    if not action_key or user_id is None:
        return DirectExecutionResult(
            executed=False,
            response_text="Resume payload inválido para retomada aprovada.",
        )

    payload.setdefault("_approval_granted_action_id", (resume_payload or {}).get("approved_action_id"))
    payload.setdefault("_approval_requested_channel", requested_channel)

    dispatcher = _build_direct_execution_dispatcher()
    result = dispatcher.execute(
        DirectExecutionRequest(
            action_key=action_key,
            payload=payload,
            active_company_id=active_company_id,
            user_id=int(user_id),
            channel="approval",
        )
    )
    approval_metadata = {
        "workflow_approval": {
            "status": "resumed_execution",
            "source_action_id": (resume_payload or {}).get("approved_action_id"),
            "requested_channel": requested_channel,
            "action_key": action_key,
        }
    }
    merged_metadata = _merge_menu_metadata(result.metadata, approval_metadata) or approval_metadata
    return DirectExecutionResult(
        executed=result.executed,
        response_text=result.response_text,
        metadata=merged_metadata,
    )


def _execute_create_project_task(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_project_task_create_execution_handler()
    result = handler.execute(
        ProjectTaskCreateRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_schedule_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_meeting_schedule_execution_handler()
    result = handler.execute(
        MeetingScheduleRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_start_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_meeting_start_execution_handler()
    result = handler.execute(
        MeetingStartRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_summarize_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_meeting_summarize_execution_handler()
    result = handler.execute(
        MeetingSummarizeRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_onboarding_status(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_onboarding_status_execution_handler()
    result = handler.execute(
        OnboardingStatusRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_onboarding_diagnose(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_onboarding_diagnose_execution_handler()
    result = handler.execute(
        OnboardingDiagnoseRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_onboarding_start(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_onboarding_start_execution_handler()
    result = handler.execute(
        OnboardingStartRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_onboarding_go_live_check(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_onboarding_go_live_check_execution_handler()
    result = handler.execute(
        OnboardingGoLiveCheckRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _resolve_single_company_for_operation(
    payload: Dict[str, Any],
    active_company_id: Optional[int],
    user_id: int,
    allow_none_company: bool = False,
) -> Tuple[Optional[int], Optional[str]]:
    company_ids, label_or_error = _resolve_company_ids_for_payload(
        payload=payload,
        active_company_id=active_company_id,
        user_id=user_id,
    )
    if not company_ids:
        if allow_none_company:
            return None, None
        return None, label_or_error or "Nenhuma empresa encontrada."
    if len(company_ids) > 1:
        return None, (
            "Encontrei mais de uma empresa no seu contexto. "
            "Informe no formato: empresa: NOME_DA_EMPRESA"
        )
    return int(company_ids[0]), None


def _resolve_explicit_company_id_from_payload(
    payload: Dict[str, Any],
    user_id: int,
) -> Optional[int]:
    selected_id = payload.get("_selected_company_id") or payload.get("_summary_company_id")
    if selected_id is not None:
        try:
            selected_company_id = int(selected_id)
        except (TypeError, ValueError):
            selected_company_id = None
        if selected_company_id and _user_can_access_company(user_id, selected_company_id):
            return selected_company_id

    company_ids, _ = _resolve_company_ids_for_payload(
        payload=payload,
        active_company_id=None,
        user_id=user_id,
    )
    if len(company_ids) == 1:
        return int(company_ids[0])
    return None


def _resolve_effective_company_id_for_payload(
    payload: Dict[str, Any],
    fallback_company_id: Optional[int],
    user_id: int,
) -> Optional[int]:
    explicit_company_id = _resolve_explicit_company_id_from_payload(
        payload=payload,
        user_id=user_id,
    )
    if explicit_company_id:
        return explicit_company_id
    return fallback_company_id


def _normalize_objective(value: str) -> str:
    normalized = _normalize_text(value or "")
    if any(tok in normalized for tok in ("reuniao", "reunioes")):
        return "reunioes"
    if any(tok in normalized for tok in ("processo", "instancia")):
        return "processos"
    if any(tok in normalized for tok in ("afazer", "tarefa", "atividade", "projeto", "trabalho")):
        return "afazeres"
    if "telegram" in normalized:
        return "telegram"
    if "whatsapp" in normalized:
        return "whatsapp"
    if any(tok in normalized for tok in ("onboarding", "cadastro", "empresa")):
        return "onboarding"
    return "geral"


def _format_objective_label(value: str) -> str:
    objective = _normalize_objective(value)
    mapping = {
        "reunioes": "Reunioes",
        "afazeres": "Afazeres e Projetos",
        "processos": "Processos",
        "telegram": "Canal Telegram",
        "whatsapp": "Canal WhatsApp",
        "onboarding": "Onboarding Geral",
        "geral": "Geral",
    }
    return mapping.get(objective, value)


def _default_workflow_description(action_key: str, title: str) -> str:
    mapping = {
        "project.create": "Cria um novo projeto no sistema com escopo inicial controlado.",
        "project.update": "Atualiza dados estruturados de um projeto existente com rastreabilidade.",
        "project.complete": "Finaliza um projeto e registra o encerramento operacional.",
        "project_task.create": "Cadastra uma nova atividade vinculada a um projeto existente.",
        "project_task.complete": "Conclui uma atividade de projeto e registra a finalizacao.",
        "project_task.update": "Atualiza dados de uma atividade, como prazo ou informacoes operacionais.",
        "project_task.audit": "Audita atividades para localizar lacunas de responsavel, prazo ou cadastro.",
        "process_instance.start": "Inicia uma instancia operacional de processo para execucao controlada.",
        "process_instance.complete": "Conclui uma instancia de processo e registra a finalizacao.",
        "routine.consult": "Consulta operacional de rotina para atividades, processos e reunioes usando contexto da sessao.",
        "my_work.open": "Consulta atividades, processos e reunioes em aberto no contexto operacional.",
        "my_work.overdue": "Consulta itens vencidos para priorizacao imediata.",
        "my_work.due_range": "Consulta itens a vencer em um periodo informado.",
        "my_work.completed_range": "Consulta itens concluidos dentro de um periodo.",
        "summary.today": "Gera um resumo executivo das atividades do dia.",
        "summary.week": "Gera um resumo executivo consolidado da semana.",
        "summary.month": "Gera um resumo executivo consolidado do mes.",
        "summary.custom": "Gera um resumo executivo para um periodo personalizado.",
        "collaborator.occupancy": "Analisa ocupacao, capacidade e carga de um colaborador no periodo informado.",
        "company.list_accessible": "Lista as empresas vinculadas e acessiveis ao usuario atual.",
        "meeting.schedule": "Agenda uma reuniao e registra os dados essenciais do compromisso.",
        "meeting.start": "Inicia uma reuniao registrada para acompanhamento operacional.",
        "meeting.summarize": "Consolida e resume uma reuniao registrada.",
        "meeting.close": "Encerra uma reuniao registrada com trilha operacional.",
        "meeting.send_summary_email": "Envia o resumo de uma reuniao por e-mail.",
        "meeting.send_summary_whatsapp": "Envia o resumo de uma reuniao por WhatsApp.",
        "finance.receipt_ingest": "Recebe um recibo/documento por canal e envia para a Central de Automacao Financeira com selecao segura de empresa.",
        "onboarding.diagnose": "Diagnostica o que falta para fazer um fluxo funcionar no ambiente atual.",
        "onboarding.status": "Consulta o status do onboarding e os pontos pendentes.",
        "onboarding.start": "Inicia um onboarding assistido de forma estruturada.",
        "onboarding.go_live_check": "Executa um checklist de prontidao antes de entrada em producao.",
        "agent_action.approve": "Aprova uma solicitacao pendente com trilha de auditoria.",
        "agent_action.reject": "Rejeita uma solicitacao pendente com trilha de auditoria.",
        "agent_action.revalidate": "Revalida uma solicitacao pendente para nova analise.",
        "agent_action.list_pending": "Lista solicitacoes pendentes aguardando decisao humana.",
    }
    return mapping.get(str(action_key or "").strip().lower(), f"Executa o fluxo {title} de forma controlada no APP32.")


def _execute_complete_project_task(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_project_task_complete_execution_handler()
    result = handler.execute(
        ProjectTaskCompleteRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_complete_process_instance(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    handler = _build_process_instance_complete_execution_handler()
    result = handler.execute(
        ProcessInstanceCompleteRequest(
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
        )
    )
    return result.response_text


def _execute_my_work_report(
    action: str,
    payload: Dict[str, Any],
    company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> str:
    handler = _build_my_work_execution_handler()
    result = handler.execute(
        MyWorkExecutionRequest(
            action=action,
            payload=dict(payload or {}),
            active_company_id=company_id,
            user_id=user_id,
            channel=channel or "web",
        )
    )
    return result.response_text


def _execute_summary_menu_report(
    payload: Dict[str, Any],
    active_company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> str:
    handler = _build_summary_execution_handler()
    result = handler.execute(
        SummaryExecutionRequest(
            payload=dict(payload or {}),
            active_company_id=active_company_id,
            user_id=user_id,
            channel=channel or "web",
        )
    )
    return result.report_text


def _merge_report_items(items: List[Dict[str, Any]], unique_key: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in items or []:
        code = str(item.get(unique_key) or "").strip()
        if not code:
            code = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if code not in merged:
            merged[code] = item
    return list(merged.values())


def _resolve_user_role_for_company_resolution(user_id: int) -> str:
    from models.user import User

    user = User.query.get(user_id)
    role = str(getattr(user, "role", "") or "collaborator").strip().lower()
    if role == "consultant":
        role = "collaborator"
    return role or "collaborator"


def _resolve_company_ids_for_payload(
    payload: Dict[str, Any],
    active_company_id: Optional[int],
    user_id: int,
) -> Tuple[List[int], str]:
    user_role = _resolve_user_role_for_company_resolution(user_id)
    accessible = [
        company
        for company in _load_accessible_companies_for_user(user_id=user_id)
        if bool(getattr(company, "is_active", True))
    ]

    if not accessible:
        return [], "Nenhuma empresa vinculada ao seu usuário."

    selected_company_id = payload.get("_selected_company_id") or payload.get("_summary_company_id")
    if selected_company_id is not None:
        try:
            selected_company_id = int(selected_company_id)
        except (TypeError, ValueError):
            selected_company_id = None

    if selected_company_id:
        chosen = next((company for company in accessible if int(getattr(company, "id", 0) or 0) == selected_company_id), None)
        if chosen:
            label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
            return [chosen.id], f"empresa {label}"
        return [], "Voce nao possui acesso a empresa selecionada."

    empresa_term = str(payload.get("empresa") or payload.get("company") or "").strip()
    if empresa_term:
        matches = _match_companies_by_term(accessible, empresa_term)
        if not matches:
            return [], f"Nao encontrei empresa para '{empresa_term}'."
        if len(matches) > 1:
            lines = ["Encontrei mais de uma empresa para esse termo. Escolha uma empresa e tente novamente:"]
            for comp in matches[:10]:
                prefix = comp.client_code or "SEM PREFIXO"
                lines.append(f"- {prefix} - {comp.name}")
            return [], "\n".join(lines)
        chosen = matches[0]
        label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
        return [chosen.id], f"empresa {label}"

    if active_company_id:
        chosen = next((c for c in accessible if c.id == active_company_id), None)
        if chosen:
            label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
            return [chosen.id], f"empresa {label}"

    if len(accessible) == 1:
        chosen = accessible[0]
        label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
        return [chosen.id], f"empresa {label}"

    if user_role == "collaborator":
        return [], "Seu usuário está vinculado a mais de uma empresa. Informe a empresa desejada para continuar."

    return [c.id for c in accessible], "empresas vinculadas"


def _resolve_employee_ids_for_my_work_report(user_id: int, company_ids: List[int]) -> Optional[List[int]]:
    from models.employee import Employee
    from models.user import User

    user = User.query.get(user_id)
    if not user:
        return []

    user_role = str(getattr(user, "role", "") or "").strip().lower()
    if user_role == "consultant":
        user_role = "collaborator"

    if user_role != "collaborator":
        return None

    query = Employee.query.filter(
        Employee.user_id == user_id,
        Employee.company_id.in_(company_ids),
    )
    employee_ids = [employee.id for employee in query.all() if getattr(employee, "id", None)]
    return employee_ids


def _match_employees_by_term_for_companies(
    company_ids: List[int],
    collaborator_term: str,
) -> Tuple[List[Any], Optional[str]]:
    from models.employee import Employee

    normalized_term = _normalize_text(collaborator_term)
    if not normalized_term:
        return [], "Informe o colaborador para continuar."

    employees = (
        Employee.query.filter(
            Employee.company_id.in_(company_ids),
            Employee.status == "active",
        )
        .order_by(Employee.company_id.asc(), Employee.name.asc(), Employee.id.asc())
        .all()
    )
    if not employees:
        return [], "Nenhum colaborador ativo encontrado no recorte solicitado."

    matches: List[Tuple[int, Any]] = []
    for employee in employees:
        haystack = _normalize_text(
            f"{getattr(employee, 'name', '')} {getattr(employee, 'email', '')} {getattr(employee, 'department', '')}"
        )
        employee_name = _normalize_text(getattr(employee, "name", "") or "")
        score = 0
        if normalized_term == employee_name:
            score += 10
        if normalized_term in haystack:
            score += 4
        if all(token in haystack for token in normalized_term.split() if token):
            score += 2
        if score > 0:
            matches.append((score, employee))

    if not matches:
        visible_names = ", ".join(
            str(getattr(employee, "name", "") or "").strip()
            for employee in employees[:8]
            if str(getattr(employee, "name", "") or "").strip()
        )
        return [], (
            f"Nao encontrei colaborador para '{collaborator_term}'."
            + (f" Colaboradores ativos: {visible_names}" if visible_names else "")
        )

    matches.sort(
        key=lambda item: (
            -item[0],
            str(getattr(item[1], "name", "") or "").lower(),
            int(getattr(item[1], "id", 0) or 0),
        )
    )
    top_score = matches[0][0]
    top_matches = [employee for score, employee in matches if score == top_score]
    unique_ids = {
        getattr(employee, "id", None)
        for employee in top_matches
        if getattr(employee, "id", None) is not None
    }
    if len(unique_ids) > 1:
        names = ", ".join(str(getattr(employee, "name", "") or "").strip() for employee in top_matches[:8])
        return [], f"Encontrei mais de um colaborador para '{collaborator_term}': {names}"
    return top_matches[:1], None


def _resolve_employee_scope_for_my_work_payload(
    payload: Dict[str, Any],
    user_id: int,
    company_ids: List[int],
    default_employee_ids: Optional[List[int]],
) -> Tuple[Optional[List[int]], Optional[str], Optional[str]]:
    del user_id

    collaborator_term = str(
        payload.get("colaborador")
        or payload.get("colaborador_nome")
        or payload.get("responsavel")
        or payload.get("responsável")
        or ""
    ).strip()
    if not collaborator_term:
        return default_employee_ids, None, None

    matches, error_message = _match_employees_by_term_for_companies(company_ids, collaborator_term)
    if error_message:
        return None, None, error_message

    matched_ids = [int(employee.id) for employee in matches if getattr(employee, "id", None) is not None]
    matched_label = str(getattr(matches[0], "name", "") or collaborator_term).strip() if matches else collaborator_term

    if default_employee_ids is not None:
        has_explicit_company_scope = bool(
            payload.get("_selected_company_id")
            or payload.get("_summary_company_id")
            or str(payload.get("empresa") or payload.get("company") or "").strip()
        )
        if not (collaborator_term and has_explicit_company_scope):
            allowed_ids = set(default_employee_ids)
            matched_ids = [employee_id for employee_id in matched_ids if employee_id in allowed_ids]
            if not matched_ids:
                return None, None, f"Voce nao possui acesso ao colaborador '{matched_label}' neste recorte."

    return matched_ids, matched_label, None


def _load_accessible_companies_for_user(user_id: int) -> List[Any]:
    from models.company import Company
    from models.employee import Employee
    from models.user import User

    user = User.query.get(user_id)
    is_admin = bool(user and str(getattr(user, "role", "")).lower() == "admin")

    if is_admin:
        return (
            Company.query.filter(Company.is_active.is_(True))
            .order_by(Company.name.asc())
            .all()
        )

    return (
        db.session.query(Company)
        .join(Employee, Employee.company_id == Company.id)
        .filter(
            Employee.user_id == user_id,
            Company.is_active.is_(True),
        )
        .distinct()
        .order_by(Company.name.asc())
        .all()
    )


def _match_companies_by_term(companies: List[Any], term: str) -> List[Any]:
    normalized_term = _normalize_text(term)
    if not normalized_term:
        return companies

    term_tokens = [tok for tok in normalized_term.split() if tok]
    ranked = []
    for comp in companies:
        code = _normalize_text(getattr(comp, "client_code", "") or "")
        name = _normalize_text(getattr(comp, "name", "") or "")
        legal = _normalize_text(getattr(comp, "legal_name", "") or "")
        hay = f"{code} {name} {legal}".strip()

        score = 0
        if normalized_term == code:
            score += 10
        if normalized_term in hay:
            score += 6
        if term_tokens:
            hits = sum(1 for tok in term_tokens if tok in hay)
            score += hits
        if score > 0:
            ranked.append((score, comp))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return [comp for _, comp in ranked]


def _resolve_period_from_payload(payload: Dict[str, Any]) -> Tuple[Optional[date], Optional[date]]:
    period_value = str(payload.get("periodo") or payload.get("period") or "").strip()
    if period_value:
        parsed = _parse_date_range(period_value)
        if parsed:
            return parsed

        relative = _resolve_relative_period_text(period_value)
        if relative:
            return relative

    d1 = _parse_completion_date(str(payload.get("data_inicial") or payload.get("start_date") or "").strip())
    d2 = _parse_completion_date(str(payload.get("data_final") or payload.get("end_date") or "").strip())
    if d1 and d2:
        if d1 <= d2:
            return d1, d2
        return d2, d1

    return None, None


def _resolve_relative_period_text(raw_value: str) -> Optional[Tuple[date, date]]:
    text = _normalize_text(raw_value or "")
    if not text:
        return None

    today = _local_today()

    if text in {"hoje", "dia de hoje"}:
        return today, today

    if text in {"amanha", "amanhã"}:
        target = today + timedelta(days=1)
        return target, target

    if "semana" in text:
        # Semana corrente: de hoje ate domingo.
        days_until_sunday = 6 - today.weekday()
        if days_until_sunday < 0:
            days_until_sunday = 0
        return today, today + timedelta(days=days_until_sunday)

    if any(token in text for token in {"este mes", "neste mes", "mes atual", "mês atual", "este mês", "neste mês"}):
        first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_day_next_month - timedelta(days=1)
        return today, end_of_month

    m_days = re.search(r"proxim(?:o|os|a|as)\s+(\d{1,3})\s+dias?", text)
    if m_days:
        days = int(m_days.group(1))
        if days <= 0:
            return None
        return today, today + timedelta(days=days - 1)

    m_weeks = re.search(r"proxim(?:a|as|o|os)\s+(\d{1,2})\s+semanas?", text)
    if m_weeks:
        weeks = int(m_weeks.group(1))
        if weeks <= 0:
            return None
        total_days = (weeks * 7) - 1
        return today, today + timedelta(days=total_days)

    return None


def _parse_date_range(raw_value: str) -> Optional[Tuple[date, date]]:
    if not raw_value:
        return None

    # Captura DD/MM/AAAA ou AAAA-MM-DD
    date_tokens = re.findall(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", raw_value)
    if not date_tokens:
        return None

    if len(date_tokens) == 1:
        d = _parse_completion_date(date_tokens[0])
        if not d:
            return None
        return d, d

    d1 = _parse_completion_date(date_tokens[0])
    d2 = _parse_completion_date(date_tokens[1])
    if not d1 or not d2:
        return None
    if d1 <= d2:
        return d1, d2
    return d2, d1


def _parse_meeting_datetime_input(
    datetime_raw: str,
    date_raw: str,
    time_raw: str,
) -> Tuple[Optional[date], Optional[str], Optional[str]]:
    """
    Converte entrada textual para data/hora de reunião.
    Aceita:
    - data_hora: DD/MM/AAAA HH:MM
    - data_hora: AAAA-MM-DD HH:MM
    - data_hora: DD/MM/AAAA (hora padrão 09:00)
    - data_hora: AAAA-MM-DD (hora padrão 09:00)
    - data + hora em campos separados
    """
    date_part = None
    time_part = None

    raw = (datetime_raw or "").strip()
    if raw:
        tokens = raw.replace("T", " ").split()
        if tokens:
            date_part = _parse_completion_date(tokens[0])
        if len(tokens) >= 2:
            time_part = _parse_time_value(tokens[1])
        if not date_part:
            m_date = re.search(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", raw)
            m_time = re.search(r"\d{1,2}[:hH]\d{2}|\d{1,2}h", raw)
            if m_date:
                date_part = _parse_completion_date(m_date.group(0))
            if m_time:
                time_part = _parse_time_value(m_time.group(0))

    if not date_part and date_raw:
        date_part = _parse_completion_date(date_raw.strip())
    if not time_part and time_raw:
        time_part = _parse_time_value(time_raw.strip())

    if not date_part:
        return None, None, (
            "Data/Hora invalida. Use um destes formatos:\n"
            "- data_hora: 10/03/2026 14:30\n"
            "- data_hora: 2026-03-10 14:30"
        )
    if not time_part:
        time_part = "09:00"

    return date_part, time_part, None


def _parse_time_value(raw_value: str) -> Optional[str]:
    raw = (raw_value or "").strip().lower()
    if not raw:
        return None

    raw = raw.replace(" ", "")
    raw = raw.replace("h", ":")
    if re.fullmatch(r"\d{1,2}", raw):
        raw = f"{raw}:00"
    if re.fullmatch(r"\d{1,2}:", raw):
        raw = f"{raw}00"

    try:
        parsed = datetime.strptime(raw, "%H:%M")
    except ValueError:
        return None
    return parsed.strftime("%H:%M")


def _load_project_tasks_report(
    company_ids: List[int],
    mode: str,
    start_date: Optional[date],
    end_date: Optional[date],
    employee_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    from models.project import ProjectTask, Project
    from models.company import Company

    today = _local_today()
    query = (
        db.session.query(ProjectTask, Project, Company)
        .join(Project, Project.id == ProjectTask.project_id)
        .join(Company, Company.id == Project.company_id)
        .filter(Project.company_id.in_(company_ids))
    )

    if employee_ids is not None:
        if not employee_ids:
            return []
        query = query.filter(ProjectTask.employee_id.in_(employee_ids))

    if mode == "my_work.completed_range":
        query = query.filter(or_(ProjectTask.status == "completed", ProjectTask.stage == "completed"))
        if start_date and end_date:
            query = query.filter(ProjectTask.completion_date >= start_date, ProjectTask.completion_date <= end_date)
        query = query.order_by(ProjectTask.completion_date.asc().nullslast(), ProjectTask.id.asc())
    else:
        query = query.filter(~ProjectTask.status.in_(["completed", "cancelled"]))
        query = query.filter(ProjectTask.stage != "completed")
        if mode == "my_work.overdue":
            query = query.filter(ProjectTask.due_date.isnot(None), ProjectTask.due_date < today)
        elif mode == "my_work.due_range" and start_date and end_date:
            query = query.filter(ProjectTask.due_date.isnot(None), ProjectTask.due_date >= start_date, ProjectTask.due_date <= end_date)
        query = query.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc())

    rows = query.limit(120).all()
    items: List[Dict[str, Any]] = []
    for task, project, company in rows:
        company_code = company.client_code or "CP"
        project_code = f"{company_code}.J.{project.id}"
        activity_code = f"{project_code}.{task.id}"
        due = task.due_date.isoformat() if getattr(task, "due_date", None) else "-"
        completed = task.completion_date.isoformat() if getattr(task, "completion_date", None) else "-"
        responsible = task.employee.name if getattr(task, "employee", None) else (task.who or "Sem responsavel")
        items.append({
            "company_id": company.id,
            "company_code": company_code,
            "company_name": company.name,
            "project_code": project_code,
            "project_name": project.name,
            "activity_code": activity_code,
            "title": task.what,
            "responsible": responsible,
            "due_date": due,
            "completion_date": completed,
            "status": task.status,
        })
    return items


def _load_project_task_audit_rows(
    company_ids: List[int],
    audit_type: str,
) -> List[Dict[str, Any]]:
    from models.company import Company
    from models.project import Project, ProjectTask

    query = (
        db.session.query(ProjectTask, Project, Company)
        .join(Project, Project.id == ProjectTask.project_id)
        .join(Company, Company.id == Project.company_id)
        .filter(Project.company_id.in_(company_ids))
        .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
        .filter(ProjectTask.stage != "completed")
    )

    if audit_type == "missing_responsible":
        query = query.filter(
            ProjectTask.employee_id.is_(None),
            or_(ProjectTask.who.is_(None), func.length(func.trim(ProjectTask.who)) == 0),
        )
    else:
        query = query.filter(ProjectTask.due_date.is_(None))

    rows = query.order_by(Company.name.asc(), Project.name.asc(), ProjectTask.id.asc()).limit(150).all()
    items: List[Dict[str, Any]] = []
    for task, project, company in rows:
        company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
        project_code = str(getattr(project, "code", "") or "").strip() or f"{company_code}.J.{getattr(project, 'id', '-')}"
        activity_code = str(getattr(task, "code", "") or "").strip() or f"{project_code}.{getattr(task, 'id', '-')}"
        responsible = task.employee.name if getattr(task, "employee", None) else (task.who or "Sem responsavel")
        items.append(
            {
                "company_name": str(getattr(company, "name", "") or "").strip() or f"Empresa {getattr(company, 'id', '-')}",
                "project_name": str(getattr(project, "name", "") or "").strip() or f"Projeto {getattr(project, 'id', '-')}",
                "project_code": project_code,
                "activity_code": activity_code,
                "title": str(getattr(task, "what", "") or "").strip() or "Atividade sem titulo",
                "responsible": responsible,
                "due_date": getattr(task, "due_date", None).isoformat() if getattr(task, "due_date", None) else "-",
            }
        )
    return items


def _format_project_task_audit_report(
    items: List[Dict[str, Any]],
    audit_type: str,
    scope_label: str,
) -> str:
    issue_label = "sem responsável" if audit_type == "missing_responsible" else "sem data"
    if not items:
        return f"Nao encontrei atividades {issue_label} no recorte {scope_label}."

    lines = [
        f"Encontrei {len(items)} atividade(s) {issue_label} no recorte {scope_label}.",
        "",
        "Principais itens:",
    ]
    for index, item in enumerate(items[:30], start=1):
        lines.append(
            f"{index}. [{item['company_name']}] {item['project_code']} - {item['project_name']} | "
            f"{item['activity_code']} | {item['title']} | responsavel={item['responsible']} | prazo={item['due_date']}"
        )
    if len(items) > 30:
        lines.append("")
        lines.append(f"...e mais {len(items) - 30} atividade(s).")
    return "\n".join(lines)


def _load_process_instances_report(
    company_ids: List[int],
    mode: str,
    start_date: Optional[date],
    end_date: Optional[date],
    employee_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    from models.process import ProcessInstance, Process
    from models.company import Company

    today = _local_today()
    query = (
        db.session.query(ProcessInstance, Process, Company)
        .join(Process, Process.id == ProcessInstance.process_id)
        .join(Company, Company.id == ProcessInstance.company_id)
        .filter(ProcessInstance.company_id.in_(company_ids))
    )

    if employee_ids is not None:
        if not employee_ids:
            return []
        query = query.filter(
            or_(
                ProcessInstance.owner_employee_id.in_(employee_ids),
                ProcessInstance.responsible_id.in_(employee_ids),
                ProcessInstance.executor_id.in_(employee_ids),
            )
        )

    if mode == "my_work.completed_range":
        query = query.filter(ProcessInstance.status == "completed")
        if start_date and end_date:
            query = query.filter(
                or_(
                    and_(ProcessInstance.actual_end_date.isnot(None), ProcessInstance.actual_end_date >= start_date, ProcessInstance.actual_end_date <= end_date),
                    and_(ProcessInstance.completed_at.isnot(None), ProcessInstance.completed_at >= datetime.combine(start_date, datetime.min.time()), ProcessInstance.completed_at <= datetime.combine(end_date, datetime.max.time())),
                )
            )
        query = query.order_by(ProcessInstance.actual_end_date.asc().nullslast(), ProcessInstance.id.asc())
    else:
        query = query.filter(ProcessInstance.status != "completed")
        if mode == "my_work.overdue":
            query = query.filter(ProcessInstance.due_date.isnot(None), ProcessInstance.due_date < today)
        elif mode == "my_work.due_range" and start_date and end_date:
            query = query.filter(ProcessInstance.due_date.isnot(None), ProcessInstance.due_date >= start_date, ProcessInstance.due_date <= end_date)
        query = query.order_by(ProcessInstance.due_date.asc().nullslast(), ProcessInstance.id.asc())

    rows = query.limit(120).all()
    items: List[Dict[str, Any]] = []
    for instance, process, company in rows:
        company_code = company.client_code or "CP"
        process_code = process.code or f"{company_code}.C.{process.id}"
        instance_code = instance.instance_code or f"{process_code}.{instance.id}"
        due = instance.due_date.isoformat() if getattr(instance, "due_date", None) else "-"
        done = instance.actual_end_date.isoformat() if getattr(instance, "actual_end_date", None) else "-"
        owner_name = _resolve_process_owner_name(instance)
        items.append({
            "company_id": company.id,
            "company_code": company_code,
            "company_name": company.name,
            "process_code": process_code,
            "process_name": process.name,
            "instance_code": instance_code,
            "title": instance.title or process.name,
            "owner": owner_name,
            "due_date": due,
            "completion_date": done,
            "status": instance.status,
        })
    return items


def _load_meetings_report(
    company_ids: List[int],
    mode: str,
    start_date: Optional[date],
    end_date: Optional[date],
    collaborator_terms: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    from models.meeting import Meeting
    from models.company import Company
    from models.project import Project

    today = _local_today()
    query = (
        db.session.query(Meeting, Company, Project)
        .join(Company, Company.id == Meeting.company_id)
        .outerjoin(Project, Project.id == Meeting.project_id)
        .filter(Meeting.company_id.in_(company_ids))
    )

    status_expr = func.lower(func.coalesce(Meeting.status, ""))
    if mode == "my_work.completed_range":
        query = query.filter(status_expr == "completed")
        if start_date and end_date:
            query = query.filter(
                or_(
                    and_(Meeting.actual_date.isnot(None), Meeting.actual_date >= start_date, Meeting.actual_date <= end_date),
                    and_(
                        Meeting.actual_date.is_(None),
                        Meeting.scheduled_date.isnot(None),
                        Meeting.scheduled_date >= start_date,
                        Meeting.scheduled_date <= end_date,
                    ),
                )
            )
        query = query.order_by(
            Meeting.actual_date.asc().nullslast(),
            Meeting.scheduled_date.asc().nullslast(),
            Meeting.scheduled_time.asc().nullslast(),
            Meeting.id.asc(),
        )
    else:
        query = query.filter(status_expr != "completed")
        if mode == "my_work.overdue":
            query = query.filter(Meeting.scheduled_date.isnot(None), Meeting.scheduled_date < today)
        elif mode == "my_work.due_range" and start_date and end_date:
            query = query.filter(
                Meeting.scheduled_date.isnot(None),
                Meeting.scheduled_date >= start_date,
                Meeting.scheduled_date <= end_date,
            )
        query = query.order_by(
            Meeting.scheduled_date.asc().nullslast(),
            Meeting.scheduled_time.asc().nullslast(),
            Meeting.id.asc(),
        )

    rows = query.limit(120).all()
    items: List[Dict[str, Any]] = []
    normalized_terms = [
        str(term or "").strip().lower()
        for term in (collaborator_terms or [])
        if str(term or "").strip()
    ]
    for meeting, company, project in rows:
        if normalized_terms:
            guests_raw = str(meeting.guests_json or "").lower()
            if not guests_raw:
                continue
            if not any(term in guests_raw for term in normalized_terms):
                continue

        company_code = company.client_code or "CP"
        meeting_code = f"{company_code}.R.{meeting.id}"
        scheduled = meeting.scheduled_date.isoformat() if getattr(meeting, "scheduled_date", None) else "-"
        completed = meeting.actual_date.isoformat() if getattr(meeting, "actual_date", None) else "-"
        project_code = f"{company_code}.J.{project.id}" if project else "-"
        project_name = project.name if project else "Sem projeto vinculado"

        items.append({
            "company_id": company.id,
            "company_code": company_code,
            "company_name": company.name,
            "meeting_code": meeting_code,
            "meeting_name": meeting.title or f"Reuniao {meeting.id}",
            "project_code": project_code,
            "project_name": project_name,
            "scheduled_time": meeting.scheduled_time or "-",
            "due_date": scheduled,
            "completion_date": completed,
            "status": meeting.status or "draft",
        })
    return items


def _resolve_process_owner_name(instance: Any) -> str:
    from models.employee import Employee

    for field in ("owner_employee_id", "responsible_id", "executor_id"):
        emp_id = getattr(instance, field, None)
        if emp_id:
            emp = Employee.query.get(emp_id)
            if emp and emp.name:
                return emp.name
    return "Sem dono definido"


def _format_my_work_report(
    action: str,
    company_label: str,
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
    start_date: Optional[date],
    end_date: Optional[date],
    channel: str,
    payload: Dict[str, Any],
    user_id: int,
) -> str:
    manager_name = _resolve_report_user_name(user_id=user_id)
    return build_my_work_report(
        action=action,
        company_label=company_label,
        tasks=tasks,
        processes=processes,
        meetings=meetings,
        start_date=start_date,
        end_date=end_date,
        channel=channel,
        payload=payload,
        manager_name=manager_name,
        reference_date=_local_today(),
        format_date_br=_format_date_br,
    )


def _group_my_work_by_company(
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return group_my_work_by_company(tasks=tasks, processes=processes, meetings=meetings)


def _get_my_work_channel_style(channel: str) -> Dict[str, Any]:
    return get_bullet_style(channel)


def _resolve_report_user_name(user_id: int) -> str:
    from models.user import User

    user = User.query.get(user_id)
    if user and user.name:
        return str(user.name).strip()
    return "Gestor"


def _resolve_my_work_collaborator_label(
    payload: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    fallback_name: str,
) -> str:
    return resolve_my_work_collaborator_label(
        payload=payload,
        tasks=tasks,
        processes=processes,
        fallback_name=fallback_name,
    )


def _describe_my_work_period(
    action: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    return describe_my_work_period(
        action=action,
        start_date=start_date,
        end_date=end_date,
        today=_local_today(),
        format_date_br=_format_date_br,
    )


def _format_date_br(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    raw = str(value).strip()
    if not raw or raw == "-":
        return "-"

    token = raw.split("T")[0]
    parsed = _parse_completion_date(token)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return raw


def _sanitize_for_channel(value: Any, channel: str) -> str:
    return sanitize_for_channel(value, channel)


def _extract_id_from_code(code_value: str) -> Optional[int]:
    # Prioriza o último bloco numérico do código hierárquico.
    tokens = re.findall(r"\d+", code_value or "")
    if not tokens:
        return None
    try:
        return int(tokens[-1])
    except ValueError:
        return None


def _local_today():
    # Fallback para America/Bahia por padrão do ambiente.
    return _local_now().date()


def _local_now() -> datetime:
    # Fallback para America/Bahia por padrão do ambiente.
    try:
        from zoneinfo import ZoneInfo
        import os
        tz_name = os.environ.get("APP_TIMEZONE") or "America/Bahia"
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()


def _format_root_menu(company_id: Optional[int]) -> str:
    roots = list_menu_options(company_id=company_id, parent_code=None, include_inactive=False, include_global=True)
    return build_root_menu_message([f"{opt.code} - {opt.title}" for opt in roots], channel="web")


def _format_submenu(parent: AgentMenuOption, children: List[AgentMenuOption]) -> str:
    return build_submenu_message(
        f"Submenu {parent.code} - {parent.title}",
        [f"{child.code} - {child.title}" for child in children],
        channel="web",
    )


def _format_ambiguous_options(candidates: List[AgentMenuOption]) -> str:
    return build_ambiguous_options_message(
        [f"{opt.code} - {opt.title}" for opt in candidates[:8]],
        channel="web",
    )


def _format_item_selection_prompt(
    option: AgentMenuOption,
    selection: Dict[str, Any],
    channel: str = "web",
) -> str:
    return build_item_selection_prompt(
        _build_workflow_display_option(option),
        selection,
        format_project_status_label=_format_project_status_label,
        format_date_br=_format_date_br,
        channel=channel,
    )


def _format_confirmation(option: AgentMenuOption, payload: Dict[str, Any], channel: str = "web") -> str:
    return build_confirmation_text(
        _build_workflow_display_option(option),
        _public_payload(payload),
        format_project_choice_line=_format_project_choice_line,
        format_project_task_choice_line=_format_project_task_choice_line,
        format_process_instance_choice_line=_format_process_instance_choice_line,
        format_meeting_choice_line=_format_meeting_choice_line,
        format_objective_label=_format_objective_label,
        channel=channel,
    )


def _format_workflow_selection_confirmation(
    option: AgentMenuOption,
    session: AgentMenuSession,
    payload: Dict[str, Any],
    channel: str = "web",
) -> str:
    return build_workflow_selection_confirmation(
        _build_workflow_display_option(option),
        user_name=str(payload.get("_session_user_name") or _resolve_user_first_name(session.user_id) or "").strip() or None,
        channel=channel,
    )


def _build_confirmation_display_items(option: AgentMenuOption, payload: Dict[str, Any]) -> List[str]:
    return build_confirmation_display_items(
        _build_workflow_display_option(option),
        dict(payload or {}),
        format_project_choice_line=_format_project_choice_line,
        format_project_task_choice_line=_format_project_task_choice_line,
        format_process_instance_choice_line=_format_process_instance_choice_line,
        format_meeting_choice_line=_format_meeting_choice_line,
        format_objective_label=_format_objective_label,
    )


def _format_project_task_choice_line(activity_code: str) -> Optional[str]:
    from models.project import ProjectTask

    task_id = _extract_id_from_code(activity_code)
    if not task_id:
        return None

    task = ProjectTask.query.get(task_id)
    if not task:
        return None

    project_name = task.project.name if task.project else "-"
    due_str = task.due_date.isoformat() if getattr(task, "due_date", None) else "-"
    canonical_code = task.code if hasattr(task, "code") and task.code else activity_code
    return f"{canonical_code} - {task.what} | {project_name} | Prazo: {due_str}"


def _format_project_status_label(status: Any) -> str:
    normalized = _slugify(str(status or ""))
    labels = {
        "planned": "Planejado",
        "in_progress": "Em andamento",
        "completed": "Concluido",
        "cancelled": "Cancelado",
    }
    return labels.get(normalized, str(status or "Sem status"))


def _format_project_choice_line(project_code: str) -> Optional[str]:
    from models.project import Project
    from models.company import Company

    project_id = _extract_id_from_code(project_code)
    if not project_id:
        return None

    project = Project.query.get(project_id)
    if not project:
        return None

    company = Company.query.get(project.company_id)
    company_code = company.client_code if company and company.client_code else "CP"
    canonical_code = f"{company_code}.J.{project.id}"
    deadline_str = _format_date_br(getattr(project, "deadline", None))
    status_label = _format_project_status_label(getattr(project, "status", None))
    progress = int(getattr(project, "progress", 0) or 0)
    return (
        f"{canonical_code} - {project.name} | Status: {status_label} | "
        f"Progresso: {progress}% | Prazo: {deadline_str}"
    )


def _format_process_instance_choice_line(instance_code: str) -> Optional[str]:
    from models.process import ProcessInstance

    instance_id = _extract_id_from_code(instance_code)
    if not instance_id:
        return None

    instance = ProcessInstance.query.get(instance_id)
    if not instance:
        return None

    due_str = instance.due_date.isoformat() if getattr(instance, "due_date", None) else "-"
    title = instance.title or f"Instancia {instance.id}"
    code = instance.instance_code or instance_code
    return f"{code} - {title} | Prazo: {due_str}"


def _format_meeting_choice_line(meeting_value: str) -> Optional[str]:
    from models.meeting import Meeting

    meeting_id = _extract_id_from_code(meeting_value)
    if not meeting_id:
        return None

    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return None

    date_part = meeting.scheduled_date.isoformat() if meeting.scheduled_date else "-"
    time_part = meeting.scheduled_time or "-"
    status = meeting.status or "draft"
    return f"ID {meeting.id} - {meeting.title} | Status: {status} | Data: {date_part} {time_part}"


def _format_missing_fields(
    option: AgentMenuOption,
    missing_fields: List[Dict[str, str]],
    payload: Dict[str, Any],
    channel: str = "web",
) -> str:
    optional_fields = [
        field.model_dump()
        for field in _list_optional_fields(option, payload)
    ]
    complementary_fields = [
        field.model_dump()
        for field in _list_complementary_fields(option, payload)
    ]
    return build_missing_fields_prompt(
        _build_workflow_display_option(option),
        missing_fields,
        payload,
        optional_fields=optional_fields,
        complementary_fields=complementary_fields,
        auto_filled_fields=_build_auto_filled_session_lines(payload),
        channel=channel,
    )


def _format_additional_fields(
    option: AgentMenuOption,
    additional_fields: List[WorkflowRequiredField],
    payload: Dict[str, Any],
    session: AgentMenuSession,
    channel: str = "web",
) -> str:
    optional_fields = [field.model_dump() for field in additional_fields if field.category == "optional"]
    complementary_fields = [field.model_dump() for field in additional_fields if field.category == "complementary"]
    return build_missing_fields_prompt(
        _build_workflow_display_option(option),
        [],
        payload,
        optional_fields=optional_fields,
        complementary_fields=complementary_fields,
        auto_filled_fields=_build_auto_filled_session_lines(_inject_session_context_into_payload(session=session, option=option, payload=payload)),
        channel=channel,
    )


def _get_or_create_session(
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
) -> AgentMenuSession:
    normalized_channel = str(channel or "web").strip().lower() or "web"
    session = AgentMenuSession.query.filter(
        AgentMenuSession.user_id == user_id,
        AgentMenuSession.company_id == company_id,
        AgentMenuSession.channel == normalized_channel,
        AgentMenuSession.thread_id == thread_id,
    ).first()
    if session:
        return session

    if normalized_channel != "web":
        fallback_session = AgentMenuSession.query.filter(
            AgentMenuSession.user_id == user_id,
            AgentMenuSession.channel == normalized_channel,
            AgentMenuSession.thread_id == thread_id,
        ).order_by(AgentMenuSession.updated_at.desc(), AgentMenuSession.id.desc()).first()
        if fallback_session:
            return fallback_session

    session = AgentMenuSession(
        user_id=user_id,
        company_id=company_id,
        channel=normalized_channel,
        thread_id=thread_id,
        status="idle",
        collected_data={},
        missing_fields=[],
    )
    db.session.add(session)
    db.session.commit()
    return session


def _reset_session(session: AgentMenuSession) -> None:
    session.status = "idle"
    session.selected_option_id = None
    session.collected_data = {}
    session.missing_fields = []
    session.last_user_message = None
    db.session.commit()


def _find_option_by_code(
    company_id: Optional[int],
    code: str,
    include_inactive: bool = False,
) -> Optional[AgentMenuOption]:
    query = AgentMenuOption.query.filter(AgentMenuOption.code == code)
    if not include_inactive:
        query = query.filter(AgentMenuOption.is_active.is_(True))

    if company_id:
        options = query.filter(
            or_(
                AgentMenuOption.company_id == company_id,
                AgentMenuOption.company_id.is_(None),
            )
        ).all()
        if not options:
            return None
        options.sort(key=lambda o: (0 if o.company_id == company_id else 1, o.sort_order, o.id))
        return options[0]

    return query.filter(AgentMenuOption.company_id.is_(None)).order_by(AgentMenuOption.sort_order.asc()).first()


def _list_children(company_id: Optional[int], parent_id: int) -> List[AgentMenuOption]:
    query = AgentMenuOption.query.filter(
        AgentMenuOption.parent_id == parent_id,
        AgentMenuOption.is_active.is_(True),
    )
    if company_id:
        query = query.filter(
            or_(
                AgentMenuOption.company_id == company_id,
                AgentMenuOption.company_id.is_(None),
            )
        )
    else:
        query = query.filter(AgentMenuOption.company_id.is_(None))

    options = query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all()
    return _dedupe_by_code(options, company_id)


def _dedupe_by_code(options: List[AgentMenuOption], company_id: Optional[int]) -> List[AgentMenuOption]:
    if not options:
        return []
    sorted_options = sorted(
        options,
        key=lambda o: (
            0 if (company_id is not None and o.company_id == company_id) else 1,
            o.sort_order,
            o.code,
            o.id,
        ),
    )
    dedupe: Dict[str, AgentMenuOption] = {}
    for option in sorted_options:
        if option.code not in dedupe:
            dedupe[option.code] = option
    return list(dedupe.values())


def _discover_options_by_keywords(
    company_id: Optional[int],
    lower_text: str,
    *,
    channel: str = "web",
) -> Tuple[List[AgentMenuOption], Dict[str, Any]]:
    query = AgentMenuOption.query.filter(AgentMenuOption.is_active.is_(True))
    if company_id:
        query = query.filter(
            or_(
                AgentMenuOption.company_id == company_id,
                AgentMenuOption.company_id.is_(None),
            )
        )
    else:
        query = query.filter(AgentMenuOption.company_id.is_(None))

    options = query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all()
    runtime = WorkflowRuntime()
    discovery = runtime.discover_from_menu_options(
        text=lower_text,
        options=options,
        preferred_company_id=company_id,
        top_k=10,
        channel=channel,
    )
    options_by_id = {option.id: option for option in options}
    matched_options: List[AgentMenuOption] = []
    for match in discovery.matches:
        option_id = match.workflow.source_option_id
        option = options_by_id.get(option_id)
        if option is not None:
            matched_options.append(option)
    return matched_options, build_workflow_discovery_trace(discovery)


def _indicates_execute(lower_text: str) -> bool:
    return any(token in lower_text for token in EXECUTE_HINTS)


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def _slugify(value: str) -> str:
    normalized = _normalize_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _default_menu_seed_items() -> List[Dict[str, Any]]:
    return [
        {"code": "1", "title": "Gestao da Rotina", "parent_code": None, "sort_order": 10},
        {"code": "11", "title": "Minhas Tarefas", "parent_code": "1", "sort_order": 11},
        {"code": "111", "title": "O que tenho para hoje", "parent_code": "11", "action_key": "summary.today", "keywords": ["o que tenho para hoje", "minhas tarefas hoje"], "sort_order": 111},
        {"code": "112", "title": "O que tenho para esta semana", "parent_code": "11", "action_key": "summary.week", "keywords": ["o que tenho para esta semana", "minhas tarefas da semana"], "sort_order": 112},
        {"code": "113", "title": "O que esta vencido", "parent_code": "11", "action_key": "my_work.overdue", "keywords": ["o que esta vencido", "tarefas vencidas"], "sort_order": 113},
        {"code": "114", "title": "O que vence no periodo", "parent_code": "11", "action_key": "my_work.due_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que vence no periodo"], "sort_order": 114},
        {"code": "115", "title": "O que foi concluido no periodo", "parent_code": "11", "action_key": "my_work.completed_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que foi concluido no periodo"], "sort_order": 115},
        {"code": "12", "title": "Atividades de Projetos", "parent_code": "1", "sort_order": 12},
        {"code": "121", "title": "Consultar atividades", "parent_code": "12", "action_key": "my_work.open", "description": "Consulta atividades em aberto no contexto operacional.", "required_fields": [{"key": "empresa", "label": "Empresa", "required": True, "category": "required"}, {"key": "colaborador", "label": "Colaborador", "required": False, "category": "optional"}], "keywords": ["consultar atividades", "listar atividades", "atividades em aberto"], "sort_order": 121},
        {"code": "122", "title": "Criar atividade", "parent_code": "12", "action_key": "project_task.create", "description": "Cadastra uma nova atividade vinculada a um projeto existente.", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto", "required": True, "category": "required"}, {"key": "nome_atividade", "label": "Nome da Atividade", "required": True, "category": "required"}, {"key": "due_date", "label": "Prazo", "required": False, "category": "optional"}, {"key": "notes", "label": "Observacoes", "required": False, "category": "complementary"}], "keywords": ["criar atividade", "nova atividade"], "sort_order": 122},
        {"code": "123", "title": "Editar atividade", "parent_code": "12", "action_key": "project_task.update", "required_fields": [{"key": "codigo_atividade", "label": "Codigo da Atividade", "required": True, "category": "required"}, {"key": "due_date", "label": "Novo Prazo", "required": False, "category": "optional"}], "keywords": ["editar atividade", "alterar atividade"], "sort_order": 123},
        {"code": "124", "title": "Concluir atividade", "parent_code": "12", "action_key": "project_task.complete", "required_fields": [{"key": "codigo_atividade", "label": "Codigo da Atividade", "required": True, "category": "required"}], "keywords": ["concluir atividade", "finalizar atividade"], "sort_order": 124},
        {"code": "13", "title": "Instancias de Processos", "parent_code": "1", "sort_order": 13},
        {"code": "131", "title": "Consultar instancias", "parent_code": "13", "action_key": "routine.consult", "description": "Consulta instancias de processo usando o contexto operacional da sessao.", "required_fields": [{"key": "empresa", "label": "Empresa", "required": True, "category": "required"}, {"key": "periodo", "label": "Periodo", "required": False, "category": "optional"}], "keywords": ["consultar instancias", "meus processos", "instancias de processos"], "sort_order": 131},
        {"code": "132", "title": "Iniciar instancia", "parent_code": "13", "action_key": "process_instance.start", "required_fields": [{"key": "codigo_processo", "label": "Codigo do Processo", "required": True, "category": "required"}], "keywords": ["iniciar instancia", "abrir processo"], "sort_order": 132},
        {"code": "133", "title": "Atualizar instancia", "parent_code": "13", "sort_order": 133},
        {"code": "134", "title": "Concluir instancia", "parent_code": "13", "action_key": "process_instance.complete", "required_fields": [{"key": "codigo_instancia", "label": "Codigo da Instancia", "required": True, "category": "required"}], "keywords": ["concluir instancia", "encerrar processo"], "sort_order": 134},
        {"code": "14", "title": "Reunioes", "parent_code": "1", "sort_order": 14},
        {"code": "141", "title": "Consultar reunioes", "parent_code": "14", "action_key": "routine.consult", "description": "Consulta reunioes usando o contexto operacional da sessao.", "required_fields": [{"key": "empresa", "label": "Empresa", "required": True, "category": "required"}, {"key": "periodo", "label": "Periodo", "required": False, "category": "optional"}], "keywords": ["consultar reunioes", "minhas reunioes"], "sort_order": 141},
        {"code": "142", "title": "Agendar reuniao", "parent_code": "14", "action_key": "meeting.schedule", "description": "Agenda uma reuniao e registra os dados essenciais do compromisso.", "required_fields": [{"key": "titulo", "label": "Titulo da Reuniao", "required": True, "category": "required"}, {"key": "data_hora", "label": "Data/Hora", "required": True, "category": "required"}, {"key": "participantes", "label": "Participantes", "required": False, "category": "optional"}, {"key": "pauta", "label": "Pauta", "required": False, "category": "complementary"}], "keywords": ["agendar reuniao", "marcar reuniao"], "sort_order": 142},
        {"code": "143", "title": "Iniciar reuniao", "parent_code": "14", "action_key": "meeting.start", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao", "required": True, "category": "required"}], "keywords": ["iniciar reuniao", "comecar reuniao"], "sort_order": 143},
        {"code": "144", "title": "Resumir reuniao", "parent_code": "14", "action_key": "meeting.summarize", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao", "required": True, "category": "required"}], "keywords": ["resumir reuniao", "resumo da reuniao"], "sort_order": 144},
        {"code": "145", "title": "Encerrar reuniao", "parent_code": "14", "action_key": "meeting.close", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao", "required": True, "category": "required"}], "keywords": ["encerrar reuniao", "finalizar reuniao"], "sort_order": 145},
        {"code": "146", "title": "Enviar resumo de reuniao por e-mail", "parent_code": "14", "action_key": "meeting.send_summary_email", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao", "required": True, "category": "required"}, {"key": "email", "label": "E-mail", "required": True, "category": "required"}], "keywords": ["enviar resumo de reuniao por email", "enviar ata por email"], "sort_order": 146},
        {"code": "147", "title": "Enviar resumo de reuniao por WhatsApp", "parent_code": "14", "action_key": "meeting.send_summary_whatsapp", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao", "required": True, "category": "required"}, {"key": "telefone", "label": "Telefone", "required": True, "category": "required"}], "keywords": ["enviar resumo de reuniao por whatsapp", "enviar ata por whatsapp"], "sort_order": 147},
        {"code": "15", "title": "Tarefas da Equipe", "parent_code": "1", "sort_order": 15},
        {"code": "151", "title": "O que tem para hoje", "parent_code": "15", "action_key": "summary.today", "keywords": ["tarefas da equipe hoje", "o que a equipe tem para hoje"], "sort_order": 151},
        {"code": "152", "title": "O que tem para esta semana", "parent_code": "15", "action_key": "summary.week", "keywords": ["tarefas da equipe esta semana"], "sort_order": 152},
        {"code": "153", "title": "O que esta vencido", "parent_code": "15", "action_key": "my_work.overdue", "keywords": ["tarefas vencidas da equipe"], "sort_order": 153},
        {"code": "154", "title": "O que vence no periodo", "parent_code": "15", "action_key": "my_work.due_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que vence no periodo da equipe"], "sort_order": 154},
        {"code": "155", "title": "O que foi concluido no periodo", "parent_code": "15", "action_key": "my_work.completed_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que foi concluido no periodo da equipe"], "sort_order": 155},
        {"code": "16", "title": "Tarefas da Empresa", "parent_code": "1", "sort_order": 16},
        {"code": "161", "title": "O que tem para hoje", "parent_code": "16", "action_key": "summary.today", "keywords": ["tarefas da empresa hoje"], "sort_order": 161},
        {"code": "162", "title": "O que tem para esta semana", "parent_code": "16", "action_key": "summary.week", "keywords": ["tarefas da empresa esta semana"], "sort_order": 162},
        {"code": "163", "title": "O que esta vencido", "parent_code": "16", "action_key": "my_work.overdue", "keywords": ["tarefas vencidas da empresa"], "sort_order": 163},
        {"code": "164", "title": "O que vence no periodo", "parent_code": "16", "action_key": "my_work.due_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que vence no periodo da empresa"], "sort_order": 164},
        {"code": "165", "title": "O que foi concluido no periodo", "parent_code": "16", "action_key": "my_work.completed_range", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["o que foi concluido no periodo da empresa"], "sort_order": 165},
        {"code": "17", "title": "Resumos Operacionais", "parent_code": "1", "sort_order": 17},
        {"code": "171", "title": "Resumo de hoje", "parent_code": "17", "action_key": "summary.today", "keywords": ["resumo de hoje"], "sort_order": 171},
        {"code": "172", "title": "Resumo da semana", "parent_code": "17", "action_key": "summary.week", "keywords": ["resumo da semana"], "sort_order": 172},
        {"code": "173", "title": "Resumo do mes", "parent_code": "17", "action_key": "summary.month", "keywords": ["resumo do mes"], "sort_order": 173},
        {"code": "174", "title": "Resumo personalizado", "parent_code": "17", "action_key": "summary.custom", "required_fields": [{"key": "periodo", "label": "Periodo", "required": True, "category": "required"}], "keywords": ["resumo personalizado"], "sort_order": 174},
        {"code": "18", "title": "Capacidade Operacional", "parent_code": "1", "sort_order": 18},
        {"code": "181", "title": "Ocupacao do colaborador", "parent_code": "18", "action_key": "collaborator.occupancy", "required_fields": [{"key": "colaborador", "label": "Colaborador"}, {"key": "periodo", "label": "Periodo"}], "keywords": ["ocupacao do colaborador", "capacidade do colaborador"], "sort_order": 181},
        {"code": "182", "title": "Capacidade da equipe", "parent_code": "18", "sort_order": 182},
        {"code": "183", "title": "Capacidade da empresa", "parent_code": "18", "sort_order": 183},
        {"code": "2", "title": "Gestao Estrategica", "parent_code": None, "sort_order": 20},
        {"code": "21", "title": "Planejamento Estrategico", "parent_code": "2", "sort_order": 21},
        {"code": "22", "title": "Metas e Objetivos", "parent_code": "2", "sort_order": 22},
        {"code": "23", "title": "Indicadores", "parent_code": "2", "sort_order": 23},
        {"code": "24", "title": "Projetos Estrategicos", "parent_code": "2", "sort_order": 24},
        {"code": "241", "title": "Criar projeto", "parent_code": "24", "action_key": "project.create", "required_fields": [{"key": "nome_projeto", "label": "Nome do Projeto", "required": True, "category": "required"}], "keywords": ["criar projeto", "novo projeto"], "sort_order": 241},
        {"code": "242", "title": "Editar projeto", "parent_code": "24", "action_key": "project.update", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto", "required": True, "category": "required"}], "keywords": ["editar projeto"], "sort_order": 242},
        {"code": "243", "title": "Concluir projeto", "parent_code": "24", "action_key": "project.complete", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto", "required": True, "category": "required"}], "keywords": ["concluir projeto", "finalizar projeto"], "sort_order": 243},
        {"code": "25", "title": "Riscos e Prioridades", "parent_code": "2", "sort_order": 25},
        {"code": "26", "title": "Resumos Executivos", "parent_code": "2", "sort_order": 26},
        {"code": "3", "title": "Gestao Financeira", "parent_code": None, "sort_order": 30},
        {"code": "31", "title": "Resultado Financeiro", "parent_code": "3", "sort_order": 31},
        {"code": "32", "title": "Receitas", "parent_code": "3", "sort_order": 32},
        {"code": "33", "title": "Despesas", "parent_code": "3", "sort_order": 33},
        {"code": "34", "title": "Fluxo de Caixa", "parent_code": "3", "sort_order": 34},
        {"code": "35", "title": "Orcamento", "parent_code": "3", "sort_order": 35},
        {"code": "36", "title": "Prestacao de Contas", "parent_code": "3", "sort_order": 36},
        {"code": "361", "title": "Enviar recibo para automacao", "parent_code": "36", "action_key": "finance.receipt_ingest", "keywords": ["enviar recibo", "mandar recibo", "enviar nota para automacao", "prestacao via whatsapp"], "sort_order": 361},
        {"code": "37", "title": "Consultas Financeiras", "parent_code": "3", "sort_order": 37},
        {"code": "4", "title": "Sapiens", "parent_code": None, "sort_order": 40},
        {"code": "41", "title": "Pergunta Livre", "parent_code": "4", "sort_order": 41},
        {"code": "42", "title": "Descobrir Capacidades", "parent_code": "4", "sort_order": 42},
        {"code": "43", "title": "Consultar por Linguagem Natural", "parent_code": "4", "sort_order": 43},
        {"code": "44", "title": "Executar por Linguagem Natural", "parent_code": "4", "sort_order": 44},
        {"code": "45", "title": "Ajuda e Exemplos", "parent_code": "4", "sort_order": 45},
        {"code": "46", "title": "Minhas Conversas", "parent_code": "4", "sort_order": 46},
        {"code": "5", "title": "Governanca e Aprovacoes", "parent_code": None, "sort_order": 50},
        {"code": "51", "title": "Aprovar solicitacao", "parent_code": "5", "action_key": "agent_action.approve", "required_fields": [{"key": "agent_action_id", "label": "ID da Solicitacao", "required": True, "category": "required"}], "keywords": ["aprovar solicitacao"], "sort_order": 51},
        {"code": "52", "title": "Rejeitar solicitacao", "parent_code": "5", "action_key": "agent_action.reject", "required_fields": [{"key": "agent_action_id", "label": "ID da Solicitacao", "required": True, "category": "required"}], "keywords": ["rejeitar solicitacao"], "sort_order": 52},
        {"code": "53", "title": "Revalidar solicitacao", "parent_code": "5", "action_key": "agent_action.revalidate", "required_fields": [{"key": "agent_action_id", "label": "ID da Solicitacao", "required": True, "category": "required"}], "keywords": ["revalidar solicitacao"], "sort_order": 53},
        {"code": "54", "title": "Pendencias de aprovacao", "parent_code": "5", "action_key": "agent_action.list_pending", "keywords": ["pendencias de aprovacao", "aprovacoes pendentes"], "sort_order": 54},
        {"code": "55", "title": "Auditoria operacional", "parent_code": "5", "sort_order": 55},
        {"code": "56", "title": "Human gate", "parent_code": "5", "sort_order": 56},
        {"code": "6", "title": "Implantacao e Funcionamento", "parent_code": None, "sort_order": 60},
        {"code": "61", "title": "Diagnosticar funcionamento", "parent_code": "6", "action_key": "onboarding.diagnose", "description": "Diagnostica o que falta para fazer um fluxo funcionar no ambiente atual.", "required_fields": [{"key": "objetivo", "label": "O que voce quer fazer funcionar", "required": True, "category": "required"}, {"key": "area", "label": "Area/Modulo", "required": False, "category": "optional"}, {"key": "evidencias", "label": "Evidencias do Problema", "required": False, "category": "complementary"}], "keywords": ["diagnosticar funcionamento", "fazer funcionar"], "sort_order": 61},
        {"code": "62", "title": "Status do onboarding", "parent_code": "6", "action_key": "onboarding.status", "keywords": ["status do onboarding"], "sort_order": 62},
        {"code": "63", "title": "Iniciar onboarding assistido", "parent_code": "6", "action_key": "onboarding.start", "required_fields": [{"key": "tipo_cadastro", "label": "Tipo de Cadastro (real ou modelo)", "required": True, "category": "required"}], "keywords": ["iniciar onboarding"], "sort_order": 63},
        {"code": "64", "title": "Checklist de producao", "parent_code": "6", "action_key": "onboarding.go_live_check", "keywords": ["checklist de producao", "go live"], "sort_order": 64},
        {"code": "65", "title": "Prontidao operacional", "parent_code": "6", "sort_order": 65},
        {"code": "7", "title": "Sapiens Factory", "parent_code": None, "sort_order": 70},
        {"code": "71", "title": "Diagnosticar workflow", "parent_code": "7", "sort_order": 71},
        {"code": "72", "title": "Criar capability", "parent_code": "7", "sort_order": 72},
        {"code": "73", "title": "Evoluir capability", "parent_code": "7", "sort_order": 73},
        {"code": "74", "title": "Corrigir tool/contrato", "parent_code": "7", "sort_order": 74},
        {"code": "75", "title": "Planejar rollout", "parent_code": "7", "sort_order": 75},
        {"code": "76", "title": "Governanca tecnica", "parent_code": "7", "sort_order": 76},
    ]


def _ensure_default_menu_seed() -> None:
    has_global = AgentMenuOption.query.filter(AgentMenuOption.company_id.is_(None)).first()
    if has_global:
        _ensure_default_menu_upgrades()
        return

    code_to_id: Dict[str, int] = {}
    for item in _default_menu_seed_items():
        parent_id = code_to_id.get(item.get("parent_code")) if item.get("parent_code") else None
        option = AgentMenuOption(
            company_id=None,
            parent_id=parent_id,
            code=item["code"],
            title=item["title"],
            action_key=item.get("action_key"),
            description=item.get("description"),
            required_fields=item.get("required_fields") or [],
            keywords=item.get("keywords") or [],
            sort_order=item.get("sort_order", 0),
            is_active=True,
        )
        db.session.add(option)
        db.session.flush()
        code_to_id[item["code"]] = option.id
    db.session.commit()


def _ensure_default_menu_upgrades() -> None:
    """
    Garante que novas opcoes padrao sejam adicionadas em bases ja inicializadas.
    """
    valid_codes = {item["code"] for item in _default_menu_seed_items()}
    legacy_options = AgentMenuOption.query.filter(
        AgentMenuOption.company_id.is_(None),
        ~AgentMenuOption.code.in_(valid_codes),
        AgentMenuOption.is_active.is_(True),
    ).all()
    for legacy in legacy_options:
        legacy.is_active = False

    for item in _default_menu_seed_items():
        _ensure_menu_option_exists(
            code=item["code"],
            title=item["title"],
            parent_code=item.get("parent_code"),
            sort_order=int(item.get("sort_order", 0) or 0),
            action_key=item.get("action_key"),
            description=item.get("description"),
            required_fields=item.get("required_fields") or [],
            keywords=item.get("keywords") or [],
        )
    db.session.commit()


def _ensure_menu_option_exists(
    code: str,
    title: str,
    parent_code: Optional[str],
    sort_order: int,
    action_key: Optional[str] = None,
    description: Optional[str] = None,
    required_fields: Optional[List[Dict[str, Any]]] = None,
    keywords: Optional[List[str]] = None,
) -> Optional[AgentMenuOption]:
    parent_id = None
    if parent_code:
        parent = AgentMenuOption.query.filter(
            AgentMenuOption.company_id.is_(None),
            AgentMenuOption.code == parent_code,
        ).first()
        if parent is None:
            return None
        parent_id = parent.id

    existing = AgentMenuOption.query.filter(
        AgentMenuOption.company_id.is_(None),
        AgentMenuOption.code == code,
    ).first()
    if existing:
        updated = False
        if str(existing.title or "").strip() != title:
            existing.title = title
            updated = True
        if existing.parent_id != parent_id:
            existing.parent_id = parent_id
            updated = True
        normalized_action = str(action_key or "").strip() or None
        if (str(existing.action_key or "").strip() or None) != normalized_action:
            existing.action_key = normalized_action
            updated = True
        if existing.sort_order != sort_order:
            existing.sort_order = sort_order
            updated = True
        if not bool(existing.is_active):
            existing.is_active = True
            updated = True
        if description and str(existing.description or "").strip() != description:
            existing.description = description
            updated = True
        existing_fields = list(existing.required_fields or [])
        if required_fields and existing_fields != required_fields:
            existing.required_fields = required_fields
            updated = True
        if keywords and list(existing.keywords or []) != keywords:
            existing.keywords = keywords
            updated = True
        if updated:
            db.session.flush()
        return existing

    option = AgentMenuOption(
        company_id=None,
        parent_id=parent_id,
        code=code,
        title=title,
        action_key=action_key,
        description=description,
        required_fields=required_fields or [],
        keywords=keywords or [],
        sort_order=sort_order,
        is_active=True,
    )
    db.session.add(option)
    db.session.flush()
    return option
