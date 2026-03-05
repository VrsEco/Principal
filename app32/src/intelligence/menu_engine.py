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

logger = logging.getLogger(__name__)


@dataclass
class MenuInterceptResult:
    handled: bool = False
    response_text: Optional[str] = None
    override_message: Optional[str] = None


MENU_WORDS = ("menu", "opcao", "opção", "opcoes", "opções", "fluxo")
CONFIRM_WORDS = {"sim", "confirmo", "ok", "pode", "confirmar"}
CANCEL_WORDS = {"nao", "não", "cancelar", "cancela", "voltar", "parar"}
EXECUTE_HINTS = ("executar", "fazer", "iniciar", "finalizar", "cadastrar", "editar")
COMMAND_HINTS = ("cadastrar", "criar", "iniciar", "finalizar", "editar", "executar", "resumo")
SUMMARY_ACTION_PERIOD = {
    "summary.today": "today",
    "summary.week": "week",
    "summary.month": "month",
    "summary.custom": "custom",
}
SUMMARY_WIZARD_STATUSES = {
    "awaiting_summary_dates",
    "awaiting_summary_company",
    "awaiting_summary_collaborator",
    "awaiting_summary_status",
}


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

    try:
        _ensure_default_menu_seed()
        session = _get_or_create_session(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
        )

        explicit_code = _extract_explicit_code(text, lower)
        is_item_selection_reply = (
            session.status == "awaiting_item_selection"
            and _parse_selection_number_date(text) is not None
        )
        is_summary_selection_reply = (
            session.status in SUMMARY_WIZARD_STATUSES
            and _parse_selection_number_date(text) is not None
        )

        # Se o usuário iniciar um novo comando de menu enquanto há sessão pendente,
        # reinicia o estado para evitar "prisão" em fluxo anterior.
        if session.status != "idle" and (
            _is_menu_request(lower)
            or (explicit_code and not is_item_selection_reply and not is_summary_selection_reply)
        ):
            _reset_session(session)

        if session.status == "awaiting_confirmation":
            return _handle_confirmation_state(session, text, lower)

        if session.status == "awaiting_item_selection":
            return _handle_item_selection_state(session, text, lower)

        if session.status == "awaiting_fields":
            return _handle_missing_fields_state(session, text, lower)

        if session.status in SUMMARY_WIZARD_STATUSES:
            return _handle_summary_wizard_state(session, text, lower)

        if explicit_code:
            option = _find_option_by_code(company_id, explicit_code)
            if not option:
                return MenuInterceptResult(
                    handled=True,
                    response_text=(
                        f"Nao encontrei o codigo de menu '{explicit_code}'.\n\n"
                        f"{_format_root_menu(company_id)}"
                    ),
                )
            return _prepare_option_flow(session, option, text, lower)

        if _is_menu_request(lower):
            return MenuInterceptResult(
                handled=True,
                response_text=_format_root_menu(company_id),
            )

        # Fallback de ambiguidade em modo comando: somente quando parece ação operacional.
        if _looks_like_command(lower):
            candidates = _match_options_by_keywords(company_id, lower)
            if len(candidates) >= 2:
                return MenuInterceptResult(
                    handled=True,
                    response_text=_format_ambiguous_options(candidates),
                )
            if len(candidates) == 1:
                return _prepare_option_flow(session, candidates[0], text, lower)

    except Exception as exc:
        db.session.rollback()
        logger.exception("Falha no menu engine: %s", exc)
        return MenuInterceptResult()

    return MenuInterceptResult()


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

    required_fields = _normalize_required_fields(option.required_fields)
    required_fields = _adjust_required_fields_for_context(
        action_key=(option.action_key or ""),
        required_fields=required_fields,
        session=session,
    )
    missing = _missing_fields(required_fields, collected)

    if missing:
        session.status = "awaiting_fields"
        session.collected_data = collected
        session.missing_fields = missing
        db.session.commit()
        return MenuInterceptResult(
            handled=True,
            response_text=_format_missing_fields(option, missing, collected),
        )

    if _is_read_only_action(option.action_key):
        direct_execution = _try_execute_direct_option(
            option=option,
            payload=collected,
            company_id=session.company_id,
            user_id=session.user_id,
            channel=session.channel or "web",
        )
        if direct_execution is not None:
            _reset_session(session)
            return MenuInterceptResult(
                handled=True,
                response_text=direct_execution,
            )

    session.status = "awaiting_confirmation"
    session.collected_data = collected
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_confirmation(option, collected),
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

    first_word = lower.split(" ")[0] if lower else ""
    if first_word in CONFIRM_WORDS:
        payload = session.collected_data or {}
        direct_execution = _try_execute_direct_option(
            option=option,
            payload=payload,
            company_id=session.company_id,
            user_id=session.user_id,
            channel=session.channel or "web",
        )
        if direct_execution is not None:
            _reset_session(session)
            return MenuInterceptResult(handled=True, response_text=direct_execution)

        prompt = _build_execution_prompt(
            option,
            _public_payload(payload),
            original_user_text=session.last_user_message or text
        )
        _reset_session(session)
        return MenuInterceptResult(handled=False, override_message=prompt)

    if first_word in CANCEL_WORDS:
        _reset_session(session)
        return MenuInterceptResult(handled=True, response_text="Acao cancelada. Se quiser, digite 'menu' para escolher outra opcao.")

    # Se o usuário mandar ajuste de dados em vez de "sim", atualiza e reconfirma.
    updated = dict(session.collected_data or {})
    updated.update(_extract_fields_from_text(text))
    session.collected_data = updated
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_confirmation(option, updated),
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

    merged = dict(session.collected_data or {})
    merged.update(_extract_numbered_fields_from_text(text, session.missing_fields or []))
    merged.update(_extract_fields_from_text(text))

    required_fields = _normalize_required_fields(option.required_fields)
    required_fields = _adjust_required_fields_for_context(
        action_key=(option.action_key or ""),
        required_fields=required_fields,
        session=session,
    )
    missing = _missing_fields(required_fields, merged)

    if missing:
        session.collected_data = merged
        session.missing_fields = missing
        db.session.commit()
        return MenuInterceptResult(
            handled=True,
            response_text=_format_missing_fields(option, missing, merged),
        )

    if _is_read_only_action(option.action_key):
        direct_execution = _try_execute_direct_option(
            option=option,
            payload=merged,
            company_id=session.company_id,
            user_id=session.user_id,
            channel=session.channel or "web",
        )
        if direct_execution is not None:
            _reset_session(session)
            return MenuInterceptResult(
                handled=True,
                response_text=direct_execution,
            )

    session.status = "awaiting_confirmation"
    session.collected_data = merged
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_confirmation(option, merged),
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

    hidden = dict(session.collected_data or {})
    choices = hidden.get("_choices") or []
    selection_action = str(hidden.get("_selection_action") or "").lower()

    # Fallback: usuário pode informar o código diretamente.
    direct_fields = _extract_fields_from_text(text)
    if selection_action == "project_task.complete" and "codigo_atividade" in direct_fields:
        merged = _public_payload(hidden)
        merged.update(direct_fields)
        session.status = "awaiting_confirmation"
        session.collected_data = merged
        session.missing_fields = []
        db.session.commit()
        return MenuInterceptResult(handled=True, response_text=_format_confirmation(option, merged))
    if selection_action == "process_instance.complete" and "codigo_instancia" in direct_fields:
        merged = _public_payload(hidden)
        merged.update(direct_fields)
        session.status = "awaiting_confirmation"
        session.collected_data = merged
        session.missing_fields = []
        db.session.commit()
        return MenuInterceptResult(handled=True, response_text=_format_confirmation(option, merged))
    if selection_action in {"meeting.start", "meeting.summarize"} and any(
        k in direct_fields for k in ("id_reuniao", "meeting_id", "codigo_reuniao", "codigo")
    ):
        merged = _public_payload(hidden)
        meeting_value = (
            direct_fields.get("id_reuniao")
            or direct_fields.get("meeting_id")
            or direct_fields.get("codigo_reuniao")
            or direct_fields.get("codigo")
        )
        merged["id_reuniao"] = str(meeting_value).strip()
        for key, value in direct_fields.items():
            if key in {"id_reuniao", "meeting_id", "codigo_reuniao", "codigo"}:
                continue
            merged[key] = value
        session.status = "awaiting_confirmation"
        session.collected_data = merged
        session.missing_fields = []
        db.session.commit()
        return MenuInterceptResult(handled=True, response_text=_format_confirmation(option, merged))
    if selection_action == "onboarding.diagnose" and any(
        k in direct_fields for k in ("objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento")
    ):
        merged = _public_payload(hidden)
        objective_value = (
            direct_fields.get("objetivo")
            or direct_fields.get("o_que_quer_funcionar")
            or direct_fields.get("objetivo_de_funcionamento")
        )
        merged["objetivo"] = str(objective_value).strip()
        for key, value in direct_fields.items():
            if key in {"objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento"}:
                continue
            merged[key] = value
        session.status = "awaiting_confirmation"
        session.collected_data = merged
        session.missing_fields = []
        db.session.commit()
        return MenuInterceptResult(handled=True, response_text=_format_confirmation(option, merged))

    parsed = _parse_selection_number_date(text)
    if not parsed:
        if selection_action in {"meeting.start", "meeting.summarize", "onboarding.diagnose"}:
            return MenuInterceptResult(
                handled=True,
                response_text=(
                    "Formato invalido. Informe apenas o numero da opcao (ex: 1).\n"
                    "Se quiser, voce tambem pode enviar o ID diretamente no formato campo: valor."
                ),
            )
        return MenuInterceptResult(
            handled=True,
            response_text=(
                "Formato invalido. Informe no formato numero: data (ex: 1: 27/02/2026).\n"
                "Se quiser, voce tambem pode enviar o codigo diretamente no formato campo: valor."
            ),
        )

    choice_index, date_raw = parsed
    selected = None
    for item in choices:
        if int(item.get("index", -1)) == int(choice_index):
            selected = item
            break

    if not selected:
        return MenuInterceptResult(
            handled=True,
            response_text="Indice nao encontrado na lista. Informe um numero valido conforme as opcoes exibidas.",
        )

    date_iso = None
    if date_raw:
        parsed_date = _parse_completion_date(date_raw)
        if not parsed_date:
            return MenuInterceptResult(
                handled=True,
                response_text="Data invalida. Use DD/MM/AAAA ou AAAA-MM-DD.",
            )
        date_iso = parsed_date.isoformat()

    merged = _public_payload(hidden)
    if selection_action == "project_task.complete":
        merged["codigo_atividade"] = selected.get("code")
    elif selection_action == "process_instance.complete":
        merged["codigo_instancia"] = selected.get("code")
    elif selection_action in {"meeting.start", "meeting.summarize"}:
        merged["id_reuniao"] = str(selected.get("id") or selected.get("code") or "")
    elif selection_action == "onboarding.diagnose":
        merged["objetivo"] = str(selected.get("objective") or selected.get("code") or "")
    else:
        merged["codigo"] = selected.get("code")

    if date_iso:
        merged["data_finalizacao"] = date_iso

    session.status = "awaiting_confirmation"
    session.collected_data = merged
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_confirmation(option, merged),
    )


def _is_menu_request(lower_text: str) -> bool:
    if lower_text in {"?", "ajuda", "help"}:
        return True
    return any(w in lower_text for w in MENU_WORDS)


def _looks_like_command(lower_text: str) -> bool:
    has_command = any(token in lower_text for token in COMMAND_HINTS)
    has_scope = any(
        token in lower_text
        for token in (
            "projeto",
            "atividade",
            "processo",
            "instancia",
            "instância",
            "resumo",
            "relatorio",
            "relatório",
        )
    )
    return has_command and has_scope


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

    return data


def _public_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v for k, v in (payload or {}).items()
        if not str(k).startswith("_")
    }


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
    """
    Interpreta respostas no formato:
    1: valor
    2: valor
    usando a ordem dos campos faltantes apresentados ao usuário.
    """
    data: Dict[str, str] = {}
    if not text or not missing_fields:
        return data

    pattern = re.compile(r"(?:^|[\n;])\s*(\d{1,2})\s*[:=]\s*([^\n;]+)")
    for idx_raw, value_raw in pattern.findall(text):
        try:
            pos = int(idx_raw) - 1
        except ValueError:
            continue
        if pos < 0 or pos >= len(missing_fields):
            continue

        field = missing_fields[pos] or {}
        key = _slugify(str(field.get("key") or ""))
        value = value_raw.strip(" ,.")
        if key and value:
            data[key] = value

    return data


def _normalize_required_fields(raw_fields: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in raw_fields or []:
        if isinstance(item, dict):
            key = _slugify(str(item.get("key") or item.get("label") or ""))
            label = str(item.get("label") or item.get("key") or key or "Campo")
            if key:
                normalized.append({"key": key, "label": label})
        else:
            value = str(item).strip()
            key = _slugify(value)
            if key:
                normalized.append({"key": key, "label": value})
    return normalized


def _missing_fields(required_fields: List[Dict[str, str]], collected_data: Dict[str, Any]) -> List[Dict[str, str]]:
    missing: List[Dict[str, str]] = []
    normalized_data = {_slugify(k): str(v).strip() for k, v in (collected_data or {}).items() if str(v).strip()}
    for field in required_fields:
        key = field["key"]
        if key not in normalized_data:
            missing.append(field)
    return missing


def _adjust_required_fields_for_context(
    action_key: str,
    required_fields: List[Dict[str, str]],
    session: AgentMenuSession,
) -> List[Dict[str, str]]:
    action = (action_key or "").strip().lower()
    if not action.startswith("my_work."):
        return required_fields

    # Para consultas de trabalho, empresa é inferida por contexto/scope acessível.
    return [f for f in required_fields if str(f.get("key")) != "empresa"]


def _is_read_only_action(action_key: Optional[str]) -> bool:
    action = (action_key or "").strip().lower()
    return action in {
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
    if action in {"meeting.start", "meeting.summarize"} and any(
        k in collected for k in ("id_reuniao", "meeting_id", "codigo_reuniao", "codigo")
    ):
        return None
    if action == "onboarding.diagnose" and any(
        k in collected for k in ("objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento")
    ):
        return None

    selection = _load_open_choices(action=action, company_id=session.company_id, user_id=session.user_id)
    if not selection.get("choices"):
        return None

    hidden_payload = dict(collected or {})
    hidden_payload["_selection_action"] = action
    hidden_payload["_choices"] = selection["choices"]
    hidden_payload["_scope_label"] = selection.get("scope_label")
    hidden_payload["_item_label_plural"] = selection.get("item_label_plural")

    session.status = "awaiting_item_selection"
    session.collected_data = hidden_payload
    session.missing_fields = []
    db.session.commit()

    return MenuInterceptResult(
        handled=True,
        response_text=_format_item_selection_prompt(option, selection),
    )


def _prepare_summary_flow_if_applicable(
    session: AgentMenuSession,
    option: AgentMenuOption,
    collected: Dict[str, Any],
) -> Optional[MenuInterceptResult]:
    action = (option.action_key or "").strip().lower()
    period_kind = SUMMARY_ACTION_PERIOD.get(action)
    if not period_kind:
        return None

    payload = _public_payload(collected)
    payload["_summary_action"] = action

    if period_kind == "today":
        payload["periodo"] = "hoje"
    elif period_kind == "week":
        payload["periodo"] = "esta semana"
    elif period_kind == "month":
        payload["periodo"] = "este mes"
    else:
        start_date, end_date = _resolve_period_from_payload(payload)
        if not start_date or not end_date:
            session.status = "awaiting_summary_dates"
            session.collected_data = payload
            session.missing_fields = []
            db.session.commit()
            return MenuInterceptResult(
                handled=True,
                response_text=_format_summary_period_prompt(option),
            )
        payload["periodo"] = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"

    return _prompt_summary_company_selection(session=session, option=option, payload=payload)


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

    start_date, end_date = _resolve_period_from_payload(payload)
    if not start_date or not end_date:
        return MenuInterceptResult(
            handled=True,
            response_text=(
                "Periodo invalido. Informe no formato:\n"
                "DD/MM/AAAA a DD/MM/AAAA\n"
                "Exemplo: 01/03/2026 a 31/03/2026"
            ),
        )

    payload["data_inicial"] = start_date.isoformat()
    payload["data_final"] = end_date.isoformat()
    payload["periodo"] = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"

    return _prompt_summary_company_selection(session=session, option=option, payload=payload)


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

    selected_index = _extract_selection_index(text)
    if selected_index is None:
        return MenuInterceptResult(
            handled=True,
            response_text="Formato invalido. Responda apenas com o numero da empresa. Exemplo: 1",
        )

    payload = dict(session.collected_data or {})
    choices = payload.get("_summary_company_choices") or []
    selected = next(
        (item for item in choices if int(item.get("index", -1)) == int(selected_index)),
        None,
    )
    if not selected:
        return MenuInterceptResult(
            handled=True,
            response_text="Indice de empresa invalido. Escolha uma opcao da lista.",
        )

    company_id = int(selected.get("company_id"))
    if not _user_can_access_company(session.user_id, company_id):
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Voce nao possui acesso a empresa selecionada.",
        )

    payload["_summary_company_id"] = company_id
    payload["_summary_company_label"] = selected.get("label")
    payload["empresa"] = selected.get("company_name")

    return _prompt_summary_collaborator_selection(session=session, option=option, payload=payload)


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

    selected_index = _extract_selection_index(text)
    if selected_index is None:
        return MenuInterceptResult(
            handled=True,
            response_text="Formato invalido. Responda apenas com o numero do colaborador. Exemplo: 1",
        )

    payload = dict(session.collected_data or {})
    choices = payload.get("_summary_collaborator_choices") or []
    selected = next(
        (item for item in choices if int(item.get("index", -1)) == int(selected_index)),
        None,
    )
    if not selected:
        return MenuInterceptResult(
            handled=True,
            response_text="Indice de colaborador invalido. Escolha uma opcao da lista.",
        )

    payload["_summary_employee_id"] = int(selected.get("employee_id"))
    payload["_summary_employee_name"] = selected.get("name")
    payload["colaborador"] = selected.get("name")

    return _prompt_summary_status_selection(session=session, option=option, payload=payload)


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
    if selected_index is None:
        return MenuInterceptResult(
            handled=True,
            response_text="Formato invalido. Responda apenas com o numero do status. Exemplo: 1",
        )

    payload = dict(session.collected_data or {})
    choices = payload.get("_summary_status_choices") or _summary_status_choices()
    selected = next(
        (item for item in choices if int(item.get("index", -1)) == int(selected_index)),
        None,
    )
    if not selected:
        return MenuInterceptResult(
            handled=True,
            response_text="Indice de status invalido. Escolha uma opcao da lista.",
        )

    payload["_summary_status"] = selected.get("key")
    payload["status"] = selected.get("label")

    try:
        report = _execute_summary_menu_report(
            payload=payload,
            active_company_id=session.company_id,
            user_id=session.user_id,
            channel=session.channel or "web",
        )
    except Exception as exc:
        db.session.rollback()
        _reset_session(session)
        logger.exception("Falha ao executar fluxo de resumo: %s", exc)
        return MenuInterceptResult(
            handled=True,
            response_text=f"Nao consegui gerar o resumo agora: {str(exc)}",
        )

    _reset_session(session)
    return MenuInterceptResult(handled=True, response_text=report)


def _format_summary_period_prompt(option: AgentMenuOption) -> str:
    return "\n".join(
        [
            f"{option.code} - {option.title}",
            "",
            "Informe a data inicial e final do período personalizado.",
            "Formato: DD/MM/AAAA a DD/MM/AAAA",
            "Exemplo: 01/03/2026 a 31/03/2026",
        ]
    )


def _prompt_summary_company_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    choices = _load_summary_company_choices(user_id=session.user_id)
    if not choices:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Nenhuma empresa vinculada foi encontrada para gerar o resumo.",
        )

    payload = dict(payload or {})
    payload["_summary_company_choices"] = choices
    session.status = "awaiting_summary_company"
    session.collected_data = payload
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_summary_company_prompt(option, choices),
    )


def _prompt_summary_collaborator_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    company_id = payload.get("_summary_company_id")
    if not company_id:
        _reset_session(session)
        return MenuInterceptResult(
            handled=True,
            response_text="Nao consegui identificar a empresa selecionada. Digite 'menu' e tente novamente.",
        )

    choices = _load_summary_collaborator_choices(company_id=int(company_id))
    if not choices:
        company_choices = payload.get("_summary_company_choices") or _load_summary_company_choices(user_id=session.user_id)
        payload["_summary_company_choices"] = company_choices
        session.status = "awaiting_summary_company"
        session.collected_data = payload
        session.missing_fields = []
        db.session.commit()
        return MenuInterceptResult(
            handled=True,
            response_text=(
                "Nao encontrei colaboradores ativos na empresa selecionada. "
                "Escolha outra empresa:\n\n"
                f"{_format_summary_company_prompt(option, company_choices)}"
            ),
        )

    payload = dict(payload or {})
    payload["_summary_collaborator_choices"] = choices
    session.status = "awaiting_summary_collaborator"
    session.collected_data = payload
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_summary_collaborator_prompt(option, choices),
    )


def _prompt_summary_status_selection(
    session: AgentMenuSession,
    option: AgentMenuOption,
    payload: Dict[str, Any],
) -> MenuInterceptResult:
    choices = _summary_status_choices()
    payload = dict(payload or {})
    payload["_summary_status_choices"] = choices

    session.status = "awaiting_summary_status"
    session.collected_data = payload
    session.missing_fields = []
    db.session.commit()
    return MenuInterceptResult(
        handled=True,
        response_text=_format_summary_status_prompt(option, choices),
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
        Company.query.filter(Company.id.in_(company_ids))
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
) -> str:
    lines = [f"{option.code} - {option.title}", "", "Escolha a empresa:"]
    for item in choices:
        lines.append(f"{item['index']} - {item['label']}")
    lines.append("")
    lines.append("Responda apenas com o numero da empresa. Exemplo: 1")
    return "\n".join(lines)


def _format_summary_collaborator_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
) -> str:
    lines = [f"{option.code} - {option.title}", "", "Escolha o colaborador:"]
    for item in choices:
        lines.append(f"{item['index']} - {item['label']}")
    lines.append("")
    lines.append("Responda apenas com o numero do colaborador. Exemplo: 1")
    return "\n".join(lines)


def _format_summary_status_prompt(
    option: AgentMenuOption,
    choices: List[Dict[str, Any]],
) -> str:
    lines = [f"{option.code} - {option.title}", "", "Escolha o status:"]
    for item in choices:
        lines.append(f"{item['index']} - {item['label']}")
    lines.append("")
    lines.append("Responda apenas com o numero do status. Exemplo: 1")
    return "\n".join(lines)


def _extract_selection_index(text: str) -> Optional[int]:
    parsed = _parse_selection_number_date(text)
    if not parsed:
        return None
    idx, right = parsed
    if right:
        return None
    return idx


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
    if action == "meeting.start":
        return _load_meeting_choices(company_ids=company_ids, mode="start")
    if action == "meeting.summarize":
        return _load_meeting_choices(company_ids=company_ids, mode="summarize")
    if action == "onboarding.diagnose":
        return _load_onboarding_diagnose_choices()
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
        from models.user import User
        from models.employee import Employee
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
    action = (option.action_key or "").strip().lower()
    if action == "project_task.complete":
        return _execute_complete_project_task(payload=payload, company_id=company_id, user_id=user_id)
    if action == "process_instance.complete":
        return _execute_complete_process_instance(payload=payload, company_id=company_id, user_id=user_id)
    if action == "my_work.open":
        return _execute_my_work_report(
            action=action,
            payload=payload,
            company_id=company_id,
            user_id=user_id,
            channel=channel,
        )
    if action == "my_work.overdue":
        return _execute_my_work_report(
            action=action,
            payload=payload,
            company_id=company_id,
            user_id=user_id,
            channel=channel,
        )
    if action == "my_work.due_range":
        return _execute_my_work_report(
            action=action,
            payload=payload,
            company_id=company_id,
            user_id=user_id,
            channel=channel,
        )
    if action == "my_work.completed_range":
        return _execute_my_work_report(
            action=action,
            payload=payload,
            company_id=company_id,
            user_id=user_id,
            channel=channel,
        )
    if action == "meeting.schedule":
        return _execute_schedule_meeting(payload=payload, company_id=company_id, user_id=user_id)
    if action == "meeting.start":
        return _execute_start_meeting(payload=payload, company_id=company_id, user_id=user_id)
    if action == "meeting.summarize":
        return _execute_summarize_meeting(payload=payload, company_id=company_id, user_id=user_id)
    if action == "onboarding.status":
        return _execute_onboarding_status(payload=payload, company_id=company_id, user_id=user_id)
    if action == "onboarding.diagnose":
        return _execute_onboarding_diagnose(payload=payload, company_id=company_id, user_id=user_id)
    if action == "onboarding.start":
        return _execute_onboarding_start(payload=payload, company_id=company_id, user_id=user_id)
    if action == "onboarding.go_live_check":
        return _execute_onboarding_go_live_check(payload=payload, company_id=company_id, user_id=user_id)
    return None


def _execute_schedule_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.meeting import Meeting
    from models.company import Company
    import json

    title = str(payload.get("titulo") or payload.get("title") or "").strip()
    if not title:
        return "Nao encontrei o titulo da reuniao. Informe no formato: titulo: Nome da Reuniao"

    company_ids, company_label_or_error = _resolve_company_ids_for_payload(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
    )
    if not company_ids:
        return company_label_or_error or "Nao foi possivel identificar a empresa da reuniao."
    if len(company_ids) > 1:
        return (
            "Encontrei mais de uma empresa no seu contexto. "
            "Informe no formato: empresa: NOME_DA_EMPRESA"
        )
    target_company_id = int(company_ids[0])

    datetime_raw = str(payload.get("data_hora") or payload.get("datahora") or "").strip()
    date_raw = str(payload.get("data") or payload.get("date") or "").strip()
    time_raw = str(payload.get("hora") or payload.get("time") or "").strip()
    scheduled_date, scheduled_time, parse_error = _parse_meeting_datetime_input(
        datetime_raw=datetime_raw,
        date_raw=date_raw,
        time_raw=time_raw,
    )
    if parse_error:
        return parse_error

    guests_raw = str(
        payload.get("convidados")
        or payload.get("guests")
        or payload.get("participantes")
        or ""
    ).strip()
    agenda_raw = str(
        payload.get("pauta")
        or payload.get("agenda")
        or payload.get("agenda_itens")
        or payload.get("itens_agenda")
        or ""
    ).strip()
    notes = str(
        payload.get("observacoes")
        or payload.get("notas")
        or payload.get("notes")
        or payload.get("dados")
        or ""
    ).strip()

    guest_values = [item.strip() for item in re.split(r"[,\n;]+", guests_raw) if item and item.strip()]
    guest_dict = {value: value for value in guest_values}

    agenda_values = [item.strip() for item in re.split(r"[;\n]+", agenda_raw) if item and item.strip()]
    agenda = [{"title": value} for value in agenda_values]

    try:
        meeting = Meeting(
            company_id=target_company_id,
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
    except Exception as exc:
        db.session.rollback()
        return f"Erro ao agendar reuniao: {str(exc)}"

    company = Company.query.get(target_company_id)
    company_label = (
        f"{company.client_code} - {company.name}"
        if company and company.client_code
        else (company.name if company else "empresa")
    )
    guests_label = ", ".join(guest_values) if guest_values else "Nenhum informado"
    agenda_label = "; ".join(agenda_values) if agenda_values else "Sem pauta definida"
    return (
        f"Reuniao '{title}' agendada com sucesso!\n\n"
        f"- ID: {meeting.id}\n"
        f"- Empresa: {company_label}\n"
        f"- Data/Hora: {scheduled_date.isoformat()} {scheduled_time}\n"
        f"- Convidados: {guests_label}\n"
        f"- Pauta: {agenda_label}"
    )


def _execute_start_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.meeting import Meeting
    from models.project import Project
    from models.company import Company

    meeting_value = str(
        payload.get("id_reuniao")
        or payload.get("meeting_id")
        or payload.get("codigo_reuniao")
        or payload.get("codigo")
        or ""
    ).strip()
    if not meeting_value:
        return "Nao encontrei o ID da reuniao. Informe no formato: id_reuniao: 123"

    meeting_id = _extract_id_from_code(meeting_value)
    if not meeting_id:
        return f"Nao consegui identificar o ID da reuniao em '{meeting_value}'."

    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return f"Reuniao ID {meeting_id} nao encontrada."

    if company_id and meeting.company_id != company_id and not _user_can_access_company(user_id, meeting.company_id):
        return "A reuniao informada nao pertence ao contexto da empresa ativa."
    if not _user_can_access_company(user_id, meeting.company_id):
        return "Voce nao possui acesso a esta reuniao."

    if str(meeting.status or "").lower() == "completed":
        return f"A reuniao '{meeting.title}' ja esta concluida."

    now = _local_now()
    meeting.actual_date = now.date()
    meeting.actual_time = now.strftime("%H:%M")
    meeting.status = "in_progress"

    if not meeting.project_id:
        proj = Project(
            company_id=meeting.company_id,
            name=f"Reuniao - {meeting.title} ({now.strftime('%d/%m/%Y')})",
            status="in_progress",
            priority="medium",
            owner="Sapiens",
            deadline=now.date(),
            notes=f"Projeto gerado automaticamente para a reuniao ID {meeting.id}: {meeting.title}",
        )
        db.session.add(proj)
        db.session.flush()
        meeting.project_id = proj.id

    db.session.commit()

    company = Company.query.get(meeting.company_id)
    company_code = company.client_code if company and company.client_code else "CP"
    project_code = f"{company_code}.J.{meeting.project_id}" if meeting.project_id else "-"
    return (
        f"Reuniao '{meeting.title}' iniciada com sucesso!\n\n"
        f"- ID Reuniao: {meeting.id}\n"
        f"- Inicio: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"- Projeto vinculado: {project_code}"
    )


def _execute_summarize_meeting(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.meeting import Meeting
    import json

    meeting_value = str(
        payload.get("id_reuniao")
        or payload.get("meeting_id")
        or payload.get("codigo_reuniao")
        or payload.get("codigo")
        or ""
    ).strip()
    if not meeting_value:
        return "Nao encontrei o ID da reuniao. Informe no formato: id_reuniao: 123"

    meeting_id = _extract_id_from_code(meeting_value)
    if not meeting_id:
        return f"Nao consegui identificar o ID da reuniao em '{meeting_value}'."

    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return f"Reuniao ID {meeting_id} nao encontrada."

    if company_id and meeting.company_id != company_id and not _user_can_access_company(user_id, meeting.company_id):
        return "A reuniao informada nao pertence ao contexto da empresa ativa."
    if not _user_can_access_company(user_id, meeting.company_id):
        return "Voce nao possui acesso a esta reuniao."

    try:
        guests = json.loads(meeting.guests_json or "{}")
        if not isinstance(guests, dict):
            guests = {}
    except Exception:
        guests = {}

    try:
        discussions = json.loads(meeting.discussions_json or "[]")
        if not isinstance(discussions, list):
            discussions = []
    except Exception:
        discussions = []

    try:
        activities = json.loads(meeting.activities_json or "[]")
        if not isinstance(activities, list):
            activities = []
    except Exception:
        activities = []

    scheduled_when = f"{meeting.scheduled_date.isoformat() if meeting.scheduled_date else '-'} {meeting.scheduled_time or '-'}"
    actual_when = f"{meeting.actual_date.isoformat() if meeting.actual_date else '-'} {meeting.actual_time or '-'}"
    status = meeting.status or "draft"

    lines = [
        f"Resumo da reuniao ID {meeting.id} - {meeting.title}",
        f"- Status: {status}",
        f"- Data prevista: {scheduled_when}",
        f"- Data real: {actual_when}",
    ]

    if guests:
        guest_names = list(guests.keys())
        preview = ", ".join(guest_names[:10])
        extra = "" if len(guest_names) <= 10 else f" (+{len(guest_names) - 10})"
        lines.append(f"- Participantes: {preview}{extra}")
    else:
        lines.append("- Participantes: Nao registrados")

    if meeting.project_id:
        lines.append(f"- Projeto vinculado: {meeting.project_id}")

    if discussions:
        lines.append("")
        lines.append("Principais pontos:")
        for idx, item in enumerate(discussions[:10], start=1):
            topic = str(item.get("title") or "Topico nao informado").strip()
            decision = str(item.get("decision") or "").strip()
            responsible = str(item.get("responsible") or "").strip()
            deadline = str(item.get("deadline") or "").strip()
            line = f"{idx}. {topic}"
            details = []
            if decision:
                details.append(f"Decisao: {decision}")
            if responsible:
                details.append(f"Responsavel: {responsible}")
            if deadline:
                details.append(f"Prazo: {deadline}")
            if details:
                line += " | " + " | ".join(details)
            lines.append(line)

    if activities:
        lines.append("")
        lines.append("Atividades registradas:")
        for idx, item in enumerate(activities[:10], start=1):
            title = str(item.get("title") or "Atividade").strip()
            responsible = str(item.get("responsible") or "Sem responsavel").strip()
            deadline = str(item.get("deadline") or "-").strip()
            lines.append(f"{idx}. {title} | Responsavel: {responsible} | Prazo: {deadline}")

    if not discussions and not activities:
        notes = str(meeting.meeting_notes or "").strip()
        lines.append("")
        if notes:
            compact = " ".join(notes.split())
            preview = compact[:900] + ("..." if len(compact) > 900 else "")
            lines.append("Resumo registrado:")
            lines.append(preview)
        else:
            lines.append("Nao ha discussoes, atividades ou ata registrada para esta reuniao.")

    return "\n".join(lines)


def _execute_onboarding_status(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.company import Company

    selected_company_id, err = _resolve_single_company_for_operation(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
    )
    if not selected_company_id:
        return err or "Nao foi possivel identificar a empresa para o onboarding."

    company = Company.query.get(selected_company_id)
    if not company:
        return "Empresa nao encontrada."

    field_map = [
        ("client_code", "Codigo da Empresa"),
        ("name", "Nome da Empresa"),
        ("segment", "Segmento"),
        ("city", "Cidade"),
        ("state", "Estado (UF)"),
        ("mission", "Missao"),
        ("vision", "Visao"),
        ("values", "Valores"),
    ]
    missing_labels = [label for field, label in field_map if not getattr(company, field, None)]
    total_fields = len(field_map)
    completed_fields = total_fields - len(missing_labels)
    progress_pct = int(round((completed_fields / total_fields) * 100)) if total_fields else 0

    label = f"{company.client_code} - {company.name}" if company.client_code else company.name
    if missing_labels:
        lines = [
            f"Status de onboarding da empresa {label}: INCOMPLETO",
            f"Progresso: {completed_fields}/{total_fields} campos ({progress_pct}%).",
            "",
            "Campos pendentes:",
        ]
        for idx, item in enumerate(missing_labels, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")
        lines.append("Sugestoes:")
        lines.append("1. Use menu 5.1 para diagnostico completo por objetivo.")
        lines.append("2. Use menu 5.3 para iniciar onboarding assistido (cadastro guiado).")
        return "\n".join(lines)

    return (
        f"Status de onboarding da empresa {label}: COMPLETO.\n"
        f"Progresso: {completed_fields}/{total_fields} campos ({progress_pct}%).\n"
        "Os principais campos cadastrais estao preenchidos."
    )


def _execute_onboarding_diagnose(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.company import Company
    from models.employee import Employee
    from models.role import Role
    from models.project import Project, ProjectTask
    from models.process import Process, ProcessInstance
    from models.meeting import Meeting

    selected_company_id, err = _resolve_single_company_for_operation(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
    )
    if not selected_company_id:
        return err or "Nao foi possivel identificar a empresa para diagnostico."

    company = Company.query.get(selected_company_id)
    if not company:
        return "Empresa nao encontrada."

    objective_raw = str(
        payload.get("objetivo")
        or payload.get("o_que_quer_funcionar")
        or payload.get("objetivo_de_funcionamento")
        or "geral"
    ).strip()
    objective = _normalize_objective(objective_raw)

    active_employees = Employee.query.filter(
        Employee.company_id == selected_company_id,
        Employee.status == "active",
    ).count()
    roles_count = Role.query.filter(Role.company_id == selected_company_id).count()
    projects_count = Project.query.filter(Project.company_id == selected_company_id).count()
    open_tasks_count = (
        db.session.query(ProjectTask)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == selected_company_id)
        .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
        .count()
    )
    processes_count = Process.query.filter(Process.company_id == selected_company_id).count()
    open_instances_count = ProcessInstance.query.filter(
        ProcessInstance.company_id == selected_company_id,
        ProcessInstance.status != "completed",
    ).count()
    meetings_count = Meeting.query.filter(Meeting.company_id == selected_company_id).count()

    employees_with_telegram = Employee.query.filter(
        Employee.company_id == selected_company_id,
        _has_text_expr(Employee.telegram),
    ).count()
    employees_with_whatsapp = Employee.query.filter(
        Employee.company_id == selected_company_id,
        _has_text_expr(Employee.whatsapp),
    ).count()
    employees_with_email = Employee.query.filter(
        Employee.company_id == selected_company_id,
        _has_text_expr(Employee.email),
    ).count()
    employees_with_any_contact = Employee.query.filter(
        Employee.company_id == selected_company_id,
        Employee.status == "active",
        or_(
            _has_text_expr(Employee.telegram),
            _has_text_expr(Employee.whatsapp),
            _has_text_expr(Employee.email),
        ),
    ).count()

    pending: List[str] = []
    suggestions: List[str] = []

    # Base cadastral checks (sempre aplicados)
    if not company.client_code:
        pending.append("Definir codigo da empresa (client_code).")
    if not company.segment:
        pending.append("Preencher segmento da empresa.")
    if not company.city or not company.state:
        pending.append("Preencher cidade/estado da empresa.")
    if not company.mission or not company.vision:
        pending.append("Preencher missao e visao.")

    # Objective-specific checks
    if objective in {"afazeres", "projetos", "trabalho"}:
        if projects_count == 0:
            pending.append("Nao ha projetos cadastrados.")
            suggestions.append("Use menu 1.1 para criar o primeiro projeto.")
        if open_tasks_count == 0:
            pending.append("Nao ha atividades de projeto em aberto.")
            suggestions.append("Use menu 1.4 para cadastrar atividades.")

    if objective in {"processos"}:
        if processes_count == 0:
            pending.append("Nao ha processos cadastrados.")
            suggestions.append("Cadastre processos e rotinas antes de abrir instancias.")
        if open_instances_count == 0:
            pending.append("Nao ha instancias de processo em aberto.")
            suggestions.append("Use menu 2.1 para iniciar instancias.")

    if objective in {"reunioes"}:
        if meetings_count == 0:
            pending.append("Nao ha reunioes cadastradas.")
            suggestions.append("Use menu 4.1 para agendar reunioes.")
        if employees_with_any_contact == 0:
            pending.append("Nenhum colaborador possui contato (email/whatsapp/telegram) para convites.")
            suggestions.append("Atualize contatos no cadastro de colaboradores.")
        else:
            min_recommended = max(1, int(active_employees * 0.6)) if active_employees else 1
            if employees_with_any_contact < min_recommended:
                pending.append(
                    f"Cobertura de contatos baixa para reunioes: {employees_with_any_contact}/{active_employees} colaboradores ativos com contato."
                )
                suggestions.append("Completar email/whatsapp/telegram dos colaboradores para melhorar convites e notificacoes.")

    if objective in {"telegram"} and employees_with_telegram == 0:
        pending.append("Nenhum colaborador ativo possui Telegram cadastrado.")
        suggestions.append("Atualize o Telegram no perfil dos colaboradores.")

    if objective in {"whatsapp"} and employees_with_whatsapp == 0:
        pending.append("Nenhum colaborador ativo possui WhatsApp cadastrado.")
        suggestions.append("Atualize o WhatsApp no perfil dos colaboradores.")

    if objective in {"onboarding", "geral"}:
        if roles_count == 0:
            pending.append("Nao ha cargos/funcoes cadastrados.")
            suggestions.append("Cadastre ao menos um cargo para estruturar a equipe.")
        if active_employees == 0:
            pending.append("Nao ha colaboradores ativos vinculados.")
            suggestions.append("Vincule colaboradores ativos a empresa.")

    company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
    objective_label = _format_objective_label(objective_raw or "geral")
    lines = [
        f"Diagnostico de funcionamento ({objective_label}) - {company_label}",
        "",
        "Resumo atual:",
        f"- Colaboradores ativos: {active_employees}",
        f"- Cargos: {roles_count}",
        f"- Projetos: {projects_count} | Atividades em aberto: {open_tasks_count}",
        f"- Processos: {processes_count} | Instancias em aberto: {open_instances_count}",
        f"- Reunioes: {meetings_count}",
        f"- Contatos: Telegram={employees_with_telegram}, WhatsApp={employees_with_whatsapp}, Email={employees_with_email}",
        "",
    ]

    if not pending:
        lines.append("Status: pronto para operacao no objetivo informado.")
        return "\n".join(lines)

    lines.append("Pendencias para funcionar melhor:")
    for idx, item in enumerate(pending, start=1):
        lines.append(f"{idx}. {item}")

    if suggestions:
        lines.append("")
        lines.append("Proximos passos sugeridos:")
        for idx, item in enumerate(suggestions, start=1):
            lines.append(f"{idx}. {item}")

    return "\n".join(lines)


def _execute_onboarding_start(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.cadastro_session import CadastroSession

    tipo_raw = str(
        payload.get("tipo_cadastro")
        or payload.get("tipo")
        or payload.get("modelo")
        or ""
    ).strip().lower()

    if tipo_raw in {"", "real", "empresa_real", "oficial"}:
        tipo = "real"
    elif tipo_raw in {"modelo", "exemplo", "mock"}:
        tipo = "modelo"
    else:
        return "Tipo de cadastro invalido. Use: real ou modelo."

    selected_company_id, _ = _resolve_single_company_for_operation(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
        allow_none_company=True,
    )

    session = CadastroSession.criar_sessao(
        user_id=user_id,
        tipo_cadastro=tipo,
        empresa_id=selected_company_id,
    )

    if tipo == "real":
        prompt = "Para comecar o cadastro da empresa real, informe o CNPJ."
    else:
        prompt = "Vamos criar uma empresa modelo. Informe o nome da empresa exemplo."

    return (
        f"Sessao de onboarding iniciada com sucesso (ID {session.id}).\n"
        f"Tipo: {tipo}\n"
        f"{prompt}\n"
        "Quando quiser cancelar, responda: nao."
    )


def _execute_onboarding_go_live_check(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.company import Company
    from models.employee import Employee
    from models.project import Project, ProjectTask
    from models.process import Process, ProcessInstance
    from models.meeting import Meeting

    selected_company_id, err = _resolve_single_company_for_operation(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
    )
    if not selected_company_id:
        return err or "Nao foi possivel identificar a empresa para o checklist de producao."

    company = Company.query.get(selected_company_id)
    if not company:
        return "Empresa nao encontrada."

    active_employees = Employee.query.filter(
        Employee.company_id == selected_company_id,
        Employee.status == "active",
    ).count()
    employees_with_any_contact = Employee.query.filter(
        Employee.company_id == selected_company_id,
        Employee.status == "active",
        or_(
            _has_text_expr(Employee.telegram),
            _has_text_expr(Employee.whatsapp),
            _has_text_expr(Employee.email),
        ),
    ).count()

    projects_count = Project.query.filter(Project.company_id == selected_company_id).count()
    open_tasks_count = (
        db.session.query(ProjectTask)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == selected_company_id)
        .filter(~ProjectTask.status.in_(["completed", "cancelled"]))
        .count()
    )
    processes_count = Process.query.filter(Process.company_id == selected_company_id).count()
    open_instances_count = ProcessInstance.query.filter(
        ProcessInstance.company_id == selected_company_id,
        ProcessInstance.status != "completed",
    ).count()
    meetings_count = Meeting.query.filter(Meeting.company_id == selected_company_id).count()

    field_map = [
        ("client_code", "Codigo da Empresa"),
        ("name", "Nome da Empresa"),
        ("segment", "Segmento"),
        ("city", "Cidade"),
        ("state", "Estado (UF)"),
        ("mission", "Missao"),
        ("vision", "Visao"),
    ]
    missing_core = [label for field, label in field_map if not getattr(company, field, None)]

    blockers: List[str] = []
    warnings: List[str] = []

    if missing_core:
        blockers.append("Campos cadastrais essenciais pendentes: " + ", ".join(missing_core))
    if active_employees == 0:
        blockers.append("Nao ha colaboradores ativos vinculados a empresa.")
    if employees_with_any_contact == 0:
        blockers.append("Nenhum colaborador ativo possui contato para notificacoes.")
    elif active_employees > 0:
        coverage = employees_with_any_contact / active_employees
        if coverage < 0.4:
            warnings.append(
                f"Cobertura de contatos baixa ({employees_with_any_contact}/{active_employees})."
            )

    if projects_count == 0 and processes_count == 0:
        blockers.append("Nao ha projetos nem processos cadastrados para operacao.")
    else:
        if open_tasks_count == 0 and open_instances_count == 0:
            warnings.append("Nao ha atividades ou instancias em aberto para acompanhamento.")
        if meetings_count == 0:
            warnings.append("Nao ha reunioes cadastradas para registro de decisoes.")

    if blockers:
        go_live_status = "NAO PRONTO"
    elif warnings:
        go_live_status = "PRONTO COM ALERTAS"
    else:
        go_live_status = "PRONTO"

    company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
    lines = [
        f"Checklist de prontidao para producao - {company_label}",
        f"Status: {go_live_status}",
        "",
        "Resumo operacional:",
        f"- Colaboradores ativos: {active_employees}",
        f"- Colaboradores com contato: {employees_with_any_contact}",
        f"- Projetos: {projects_count} | Atividades abertas: {open_tasks_count}",
        f"- Processos: {processes_count} | Instancias abertas: {open_instances_count}",
        f"- Reunioes cadastradas: {meetings_count}",
    ]

    if blockers:
        lines.append("")
        lines.append("Bloqueadores:")
        for idx, item in enumerate(blockers, start=1):
            lines.append(f"{idx}. {item}")

    if warnings:
        lines.append("")
        lines.append("Alertas:")
        for idx, item in enumerate(warnings, start=1):
            lines.append(f"{idx}. {item}")

    lines.append("")
    if go_live_status == "PRONTO":
        lines.append("Conclusao: empresa apta para subir em producao e iniciar monitoramento.")
    elif go_live_status == "PRONTO COM ALERTAS":
        lines.append("Conclusao: pode subir em producao, mas com plano de ajuste fino durante estabilizacao.")
    else:
        lines.append("Conclusao: resolver bloqueadores antes da subida para producao.")

    return "\n".join(lines)


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


def _execute_complete_project_task(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.project import ProjectTask
    from models.company import Company

    code_value = str(
        payload.get("codigo_atividade")
        or payload.get("activity_code")
        or payload.get("task_code")
        or payload.get("codigo")
        or ""
    ).strip()
    if not code_value:
        return "Nao encontrei o codigo da atividade. Informe no formato: codigo_atividade: AA.J.26.175"

    task_id = _extract_id_from_code(code_value)
    if not task_id:
        return f"Nao consegui identificar o ID no codigo '{code_value}'."

    task = ProjectTask.query.get(task_id)
    if not task:
        return f"Atividade de projeto com codigo '{code_value}' nao encontrada."

    project = task.project
    if not project:
        return f"A atividade '{task.what}' nao possui projeto vinculado."

    if company_id and project.company_id != company_id and not _user_can_access_company(user_id, project.company_id):
        return "A atividade informada nao pertence ao contexto da empresa ativa."

    desired_date = _parse_completion_date(
        str(payload.get("completion_date") or payload.get("data_finalizacao") or "")
    ) if (payload.get("completion_date") or payload.get("data_finalizacao")) else None
    if (payload.get("completion_date") or payload.get("data_finalizacao")) and not desired_date:
        return "Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."

    final_date = desired_date or _local_today()

    if task.status != "completed" or task.stage != "completed":
        task.status = "completed"
        task.stage = "completed"
        task.completion_date = final_date
        db.session.commit()
    else:
        if desired_date and task.completion_date != desired_date:
            task.completion_date = desired_date
            db.session.commit()
        final_date = task.completion_date or final_date

    try:
        project.update_progress()
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Recarrega e mantém conclusão já persistida
        task = ProjectTask.query.get(task_id)
        project = task.project if task else None

    company = Company.query.get(project.company_id) if project else None
    company_code = (company.client_code if company and company.client_code else "CP")
    project_code = f"{company_code}.J.{project.id}" if project else "-"
    activity_code = f"{project_code}.{task.id}"
    project_name = project.name if project and project.name else f"Projeto {project.id if project else '-'}"

    return (
        f"A atividade de projeto com o codigo \"{activity_code}\" foi concluida com sucesso!\n\n"
        f"- Projeto: {project_code} - {project_name}\n"
        f"- Atividade: {task.what}\n"
        f"- Data de Conclusao: {final_date.isoformat()}"
    )


def _execute_complete_process_instance(payload: Dict[str, Any], company_id: Optional[int], user_id: int) -> str:
    from models.process import ProcessInstance
    from models.company import Company

    code_value = str(
        payload.get("codigo_instancia")
        or payload.get("instance_code")
        or payload.get("codigo")
        or ""
    ).strip()
    if not code_value:
        return "Nao encontrei o codigo da instancia. Informe no formato: codigo_instancia: CODIGO"

    instance_id = _extract_id_from_code(code_value)
    if not instance_id:
        return f"Nao consegui identificar o ID no codigo '{code_value}'."

    instance = ProcessInstance.query.get(instance_id)
    if not instance:
        return f"Instancia de processo com codigo '{code_value}' nao encontrada."

    if company_id and instance.company_id != company_id and not _user_can_access_company(user_id, instance.company_id):
        return "A instancia informada nao pertence ao contexto da empresa ativa."

    desired_date = _parse_completion_date(
        str(payload.get("completion_date") or payload.get("data_finalizacao") or "")
    ) if (payload.get("completion_date") or payload.get("data_finalizacao")) else None
    if (payload.get("completion_date") or payload.get("data_finalizacao")) and not desired_date:
        return "Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."

    final_date = desired_date or _local_today()
    if instance.status != "completed":
        instance.status = "completed"
    instance.actual_end_date = final_date
    instance.completed_at = datetime.combine(final_date, datetime.min.time())
    db.session.commit()

    company = Company.query.get(instance.company_id)
    company_code = company.client_code if company and company.client_code else "CP"
    instance_code = instance.instance_code or f"{company_code}.C.{instance.process_id}.{instance.id}"
    title = instance.title or f"Instancia {instance.id}"

    return (
        f"A instancia de processo com o codigo \"{instance_code}\" foi concluida com sucesso!\n\n"
        f"- Instancia: {title}\n"
        f"- Data de Conclusao: {final_date.isoformat()}"
    )


def _execute_my_work_report(
    action: str,
    payload: Dict[str, Any],
    company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> str:
    company_ids, company_label_or_error = _resolve_company_ids_for_payload(
        payload=payload,
        active_company_id=company_id,
        user_id=user_id,
    )
    if not company_ids:
        return company_label_or_error or "Nao foi possivel identificar a empresa para consulta."

    start_date = None
    end_date = None
    if action in {"my_work.due_range", "my_work.completed_range"}:
        start_date, end_date = _resolve_period_from_payload(payload)
        if not start_date or not end_date:
            return (
                "Para esta consulta, informe o periodo no formato:\n"
                "periodo: 01/03/2026 a 07/03/2026\n"
                "ou use periodos relativos: hoje | esta semana | este mes | proximos 15 dias"
            )

    tasks = _load_project_tasks_report(
        company_ids=company_ids,
        mode=action,
        start_date=start_date,
        end_date=end_date,
    )
    processes = _load_process_instances_report(
        company_ids=company_ids,
        mode=action,
        start_date=start_date,
        end_date=end_date,
    )
    meetings = _load_meetings_report(
        company_ids=company_ids,
        mode=action,
        start_date=start_date,
        end_date=end_date,
    )

    return _format_my_work_report(
        action=action,
        company_label=company_label_or_error,
        tasks=tasks,
        processes=processes,
        meetings=meetings,
        start_date=start_date,
        end_date=end_date,
        channel=channel,
        payload=payload,
        user_id=user_id,
    )


def _execute_summary_menu_report(
    payload: Dict[str, Any],
    active_company_id: Optional[int],
    user_id: int,
    channel: str = "web",
) -> str:
    from models.company import Company
    from models.employee import Employee

    selected_company_id = payload.get("_summary_company_id")
    if not selected_company_id:
        return "Nao consegui identificar a empresa selecionada para o resumo."
    selected_company_id = int(selected_company_id)

    if not _user_can_access_company(user_id, selected_company_id):
        return "Voce nao possui acesso a empresa selecionada."

    company = Company.query.get(selected_company_id)
    if not company:
        return "Empresa selecionada nao encontrada."

    start_date, end_date = _resolve_period_from_payload(payload)
    if not start_date or not end_date:
        return (
            "Nao consegui identificar o periodo do resumo.\n"
            "Use o formato: DD/MM/AAAA a DD/MM/AAAA."
        )

    selected_employee_id = payload.get("_summary_employee_id")
    if not selected_employee_id:
        return "Nao consegui identificar o colaborador selecionado."
    selected_employee_id = int(selected_employee_id)
    employee = Employee.query.get(selected_employee_id)
    if not employee or int(employee.company_id or 0) != selected_company_id:
        return "Colaborador selecionado nao pertence a empresa escolhida."

    employee_ids = [selected_employee_id]
    collaborator_terms = []
    employee_name = str(employee.name or "").strip()
    employee_email = str(employee.email or "").strip().lower()
    if employee_name:
        collaborator_terms.append(employee_name.lower())
    if employee_email:
        collaborator_terms.append(employee_email)

    status_key = str(payload.get("_summary_status") or "open").strip().lower()
    company_label = (
        f"empresa {company.client_code} - {company.name}"
        if company.client_code else
        f"empresa {company.name}"
    )

    normalized_payload = dict(payload or {})
    if employee_name:
        normalized_payload["colaborador"] = employee_name

    open_tasks = _merge_report_items(
        _load_project_tasks_report(
            company_ids=[selected_company_id],
            mode="my_work.overdue",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        ) + _load_project_tasks_report(
            company_ids=[selected_company_id],
            mode="my_work.due_range",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        ),
        unique_key="activity_code",
    )
    open_processes = _merge_report_items(
        _load_process_instances_report(
            company_ids=[selected_company_id],
            mode="my_work.overdue",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        ) + _load_process_instances_report(
            company_ids=[selected_company_id],
            mode="my_work.due_range",
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        ),
        unique_key="instance_code",
    )
    open_meetings = _merge_report_items(
        _load_meetings_report(
            company_ids=[selected_company_id],
            mode="my_work.overdue",
            start_date=start_date,
            end_date=end_date,
            collaborator_terms=collaborator_terms,
        ) + _load_meetings_report(
            company_ids=[selected_company_id],
            mode="my_work.due_range",
            start_date=start_date,
            end_date=end_date,
            collaborator_terms=collaborator_terms,
        ),
        unique_key="meeting_code",
    )

    completed_tasks = _load_project_tasks_report(
        company_ids=[selected_company_id],
        mode="my_work.completed_range",
        start_date=start_date,
        end_date=end_date,
        employee_ids=employee_ids,
    )
    completed_processes = _load_process_instances_report(
        company_ids=[selected_company_id],
        mode="my_work.completed_range",
        start_date=start_date,
        end_date=end_date,
        employee_ids=employee_ids,
    )
    completed_meetings = _load_meetings_report(
        company_ids=[selected_company_id],
        mode="my_work.completed_range",
        start_date=start_date,
        end_date=end_date,
        collaborator_terms=collaborator_terms,
    )

    open_report = _format_my_work_report(
        action="my_work.due_range",
        company_label=company_label,
        tasks=open_tasks,
        processes=open_processes,
        meetings=open_meetings,
        start_date=start_date,
        end_date=end_date,
        channel=channel,
        payload=normalized_payload,
        user_id=user_id,
    )
    completed_report = _format_my_work_report(
        action="my_work.completed_range",
        company_label=company_label,
        tasks=completed_tasks,
        processes=completed_processes,
        meetings=completed_meetings,
        start_date=start_date,
        end_date=end_date,
        channel=channel,
        payload=normalized_payload,
        user_id=user_id,
    )

    if status_key == "open":
        return open_report
    if status_key == "completed":
        return completed_report
    if status_key == "all":
        return (
            "STATUS: ABERTAS\n"
            f"{open_report}\n\n"
            "STATUS: CONCLUIDAS\n"
            f"{completed_report}"
        )

    return "Status invalido para resumo. Use: abertas, concluidas ou todas."


def _merge_report_items(items: List[Dict[str, Any]], unique_key: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in items or []:
        code = str(item.get(unique_key) or "").strip()
        if not code:
            code = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if code not in merged:
            merged[code] = item
    return list(merged.values())


def _resolve_company_ids_for_payload(
    payload: Dict[str, Any],
    active_company_id: Optional[int],
    user_id: int,
) -> Tuple[List[int], str]:
    from models.company import Company
    from models.employee import Employee
    from models.user import User

    user = User.query.get(user_id)
    is_admin = bool(user and str(getattr(user, "role", "")).lower() == "admin")

    if is_admin:
        accessible = Company.query.order_by(Company.name.asc()).all()
    else:
        accessible = (
            db.session.query(Company)
            .join(Employee, Employee.company_id == Company.id)
            .filter(Employee.user_id == user_id)
            .order_by(Company.name.asc())
            .all()
        )

    if not accessible:
        return [], "Nenhuma empresa vinculada ao seu usuário."

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

    return [c.id for c in accessible], "empresas vinculadas"


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
    style = _get_my_work_channel_style(channel=channel)
    base_date = _format_date_br(_local_today())
    period_label = _describe_my_work_period(
        action=action,
        start_date=start_date,
        end_date=end_date,
    )
    manager_name = _resolve_report_user_name(user_id=user_id)
    collaborator_label = _resolve_my_work_collaborator_label(
        payload=payload,
        tasks=tasks,
        processes=processes,
        fallback_name=manager_name,
    )
    normalized_company_label = str(company_label or "").strip().lower()
    company_phrase = (
        company_label
        if normalized_company_label.startswith("empresa")
        or normalized_company_label.startswith("empresas")
        else f"empresa {company_label}"
    )
    manager_name_norm = manager_name.strip().lower()
    collaborator_label_norm = collaborator_label.strip().lower()
    if collaborator_label_norm == f"do colaborador {manager_name_norm}":
        collaborator_label = "do seu contexto de atuação"

    title = (
        f"Resumo das atividades {period_label} nas {company_phrase}, "
        f"{collaborator_label}, com referência em {base_date}."
    )

    company_groups = _group_my_work_by_company(tasks=tasks, processes=processes, meetings=meetings)
    if not company_groups:
        return f"{_sanitize_for_channel(title, channel)}\n\nNenhum item encontrado para o filtro informado."

    date_name = "Conclusao" if action == "my_work.completed_range" else "Prazo"

    lines = [_sanitize_for_channel(title, channel), ""]
    for group_idx, comp in enumerate(company_groups):
        if group_idx > 0:
            lines.append("")

        company_code = comp.get("company_code") or "CP"
        company_name = comp.get("company_name") or "Empresa"
        lines.append(style["header"]("Empresa"))
        lines.append(
            f"{style['bullet']}{_sanitize_for_channel(f'{company_code} - {company_name}', channel)}"
        )
        lines.append("")

        lines.append(style["header"]("Projetos"))
        projects = comp.get("projects") or []
        if projects:
            for project in projects:
                project_label = f"{project['project_code']} - {project['project_name']}"
                lines.append(f"{style['bullet']}{_sanitize_for_channel(project_label, channel)}")
                lines.append(f"{style['sub_bullet']}{_sanitize_for_channel('Atividades', channel)}")
                for activity in project.get("activities") or []:
                    date_label = activity["completion_date"] if action == "my_work.completed_range" else activity["due_date"]
                    activity_line = (
                        f"{activity['activity_code']} - {activity['title']} | "
                        f"Responsavel: {activity['responsible']} | {date_name}: {_format_date_br(date_label)}"
                    )
                    lines.append(f"{style['item_bullet']}{_sanitize_for_channel(activity_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem atividades no periodo.")
        lines.append("")

        lines.append(style["header"]("Processos"))
        process_groups = comp.get("processes") or []
        if process_groups:
            for proc in process_groups:
                process_label = f"{proc['process_code']} - {proc['process_name']}"
                lines.append(f"{style['bullet']}{_sanitize_for_channel(process_label, channel)}")
                lines.append(f"{style['sub_bullet']}{_sanitize_for_channel('Instancias', channel)}")
                for instance in proc.get("instances") or []:
                    date_label = instance["completion_date"] if action == "my_work.completed_range" else instance["due_date"]
                    instance_line = (
                        f"{instance['instance_code']} - {instance['title']} | "
                        f"Dono do Processo: {instance['owner']} | {date_name}: {_format_date_br(date_label)}"
                    )
                    lines.append(f"{style['item_bullet']}{_sanitize_for_channel(instance_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem instancias no periodo.")
        lines.append("")

        lines.append(style["header"]("Reunioes Agendadas"))
        meeting_items = comp.get("meetings") or []
        if meeting_items:
            for meeting in meeting_items:
                date_label = meeting["completion_date"] if action == "my_work.completed_range" else meeting["due_date"]
                project_ref = f"{meeting['project_code']} - {meeting['project_name']}" if meeting.get("project_code") else "-"
                meeting_line = (
                    f"{meeting['meeting_code']} - {meeting['meeting_name']} | "
                    f"Projeto: {project_ref} | {date_name}: {_format_date_br(date_label)}"
                )
                if action != "my_work.completed_range" and meeting.get("scheduled_time") and meeting.get("scheduled_time") != "-":
                    meeting_line += f" | Hora: {meeting['scheduled_time']}"
                lines.append(f"{style['bullet']}{_sanitize_for_channel(meeting_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem reunioes agendadas no periodo.")

    return "\n".join(lines)


def _group_my_work_by_company(
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[int, Dict[str, Any]] = {}

    def _ensure_company(item: Dict[str, Any]) -> Dict[str, Any]:
        cid = int(item.get("company_id") or 0)
        company = grouped.get(cid)
        if company:
            return company

        company = {
            "company_id": cid,
            "company_code": item.get("company_code") or "CP",
            "company_name": item.get("company_name") or f"Empresa {cid}" if cid else "Empresa",
            "projects_map": {},
            "processes_map": {},
            "meetings": [],
        }
        grouped[cid] = company
        return company

    for task in tasks or []:
        company = _ensure_company(task)
        project_code = task.get("project_code") or "SEM-CODIGO"
        project_entry = company["projects_map"].get(project_code)
        if not project_entry:
            project_entry = {
                "project_code": project_code,
                "project_name": task.get("project_name") or "Sem nome",
                "activities": [],
            }
            company["projects_map"][project_code] = project_entry
        project_entry["activities"].append(task)

    for proc in processes or []:
        company = _ensure_company(proc)
        process_code = proc.get("process_code") or "SEM-CODIGO"
        process_entry = company["processes_map"].get(process_code)
        if not process_entry:
            process_entry = {
                "process_code": process_code,
                "process_name": proc.get("process_name") or "Sem nome",
                "instances": [],
            }
            company["processes_map"][process_code] = process_entry
        process_entry["instances"].append(proc)

    for meeting in meetings or []:
        company = _ensure_company(meeting)
        company["meetings"].append(meeting)

    companies: List[Dict[str, Any]] = []
    for item in grouped.values():
        projects = list(item["projects_map"].values())
        projects.sort(key=lambda p: ((p.get("project_code") or ""), (p.get("project_name") or "")))
        for p in projects:
            p["activities"].sort(key=lambda a: ((a.get("due_date") or ""), (a.get("activity_code") or "")))

        process_groups = list(item["processes_map"].values())
        process_groups.sort(key=lambda p: ((p.get("process_code") or ""), (p.get("process_name") or "")))
        for p in process_groups:
            p["instances"].sort(key=lambda i: ((i.get("due_date") or ""), (i.get("instance_code") or "")))

        meetings_sorted = sorted(
            item["meetings"],
            key=lambda m: ((m.get("due_date") or ""), (m.get("scheduled_time") or ""), (m.get("meeting_code") or "")),
        )

        companies.append({
            "company_id": item["company_id"],
            "company_code": item["company_code"],
            "company_name": item["company_name"],
            "projects": projects,
            "processes": process_groups,
            "meetings": meetings_sorted,
        })

    companies.sort(key=lambda c: ((c.get("company_code") or ""), (c.get("company_name") or "")))
    return companies


def _get_my_work_channel_style(channel: str) -> Dict[str, Any]:
    normalized = str(channel or "web").strip().lower()
    if normalized == "whatsapp":
        return {
            "header": lambda text: f"*{text}*",
            "bullet": "• ",
            "sub_bullet": "  ◦ ",
            "item_bullet": "    ▪ ",
        }
    return {
        "header": lambda text: text,
        "bullet": "- ",
        "sub_bullet": "  - ",
        "item_bullet": "    - ",
    }


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
    explicit = str(
        payload.get("colaborador")
        or payload.get("colaborador_nome")
        or payload.get("responsavel")
        or payload.get("responsável")
        or ""
    ).strip()
    if explicit:
        return f"do colaborador {explicit}"

    names = {
        str(t.get("responsible") or "").strip()
        for t in (tasks or [])
        if str(t.get("responsible") or "").strip() and str(t.get("responsible")).strip().lower() != "sem responsavel"
    }
    names.update(
        str(p.get("owner") or "").strip()
        for p in (processes or [])
        if str(p.get("owner") or "").strip() and str(p.get("owner")).strip().lower() != "sem dono definido"
    )
    names = {n for n in names if n}

    if not names:
        return f"do colaborador {fallback_name}"

    ordered = sorted(names)
    if len(ordered) == 1:
        return f"do colaborador {ordered[0]}"
    if len(ordered) == 2:
        return f"dos colaboradores {ordered[0]} e {ordered[1]}"
    return f"dos colaboradores {', '.join(ordered[:3])}"


def _describe_my_work_period(
    action: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    today = _local_today()
    if action == "my_work.open":
        return "em aberto"
    if action == "my_work.overdue":
        return "atrasadas"
    if action == "my_work.completed_range":
        return (
            f"concluidas no periodo de {_format_date_br(start_date)} a {_format_date_br(end_date)}"
            if start_date and end_date else
            "concluidas no periodo informado"
        )
    if action != "my_work.due_range" or not start_date or not end_date:
        return "com vencimento no periodo informado"

    if start_date == today and end_date == today:
        return f"vencendo hoje ({_format_date_br(today)})"

    if start_date == today:
        if end_date == today + timedelta(days=6):
            return (
                f"vencendo nesta semana ({_format_date_br(start_date)} a {_format_date_br(end_date)})"
            )
        if end_date == today + timedelta(days=14):
            return (
                f"vencendo nos proximos 15 dias ({_format_date_br(start_date)} a {_format_date_br(end_date)})"
            )
        first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_day_next_month - timedelta(days=1)
        if end_date == end_of_month:
            return (
                f"com vencimento neste mes ({_format_date_br(start_date)} a {_format_date_br(end_date)})"
            )

    return (
        f"com vencimento no periodo de {_format_date_br(start_date)} a {_format_date_br(end_date)}"
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
    text = str(value or "")
    if str(channel or "").strip().lower() == "telegram":
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return text


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
    if not roots:
        return "Nenhuma opcao de menu ativa encontrada."
    lines = ["Selecione uma opcao do menu principal:"]
    for opt in roots:
        lines.append(f"{opt.code} - {opt.title}")
    lines.append("")
    lines.append("Voce pode responder com o codigo (ex: 1.4) ou 'menu 1.4 executar ...'.")
    return "\n".join(lines)


def _format_submenu(parent: AgentMenuOption, children: List[AgentMenuOption]) -> str:
    lines = [f"Submenu {parent.code} - {parent.title}:"]
    for child in children:
        lines.append(f"{child.code} - {child.title}")
    lines.append("")
    lines.append("Digite o codigo desejado. Exemplo: menu 1.4 executar")
    return "\n".join(lines)


def _format_ambiguous_options(candidates: List[AgentMenuOption]) -> str:
    lines = ["Nao tive certeza do que voce quer executar. Escolha uma das opcoes:"]
    for opt in candidates[:8]:
        lines.append(f"{opt.code} - {opt.title}")
    lines.append("")
    lines.append("Se preferir, envie: menu CODIGO executar com os dados necessarios.")
    return "\n".join(lines)


def _format_item_selection_prompt(
    option: AgentMenuOption,
    selection: Dict[str, Any],
) -> str:
    choices = selection.get("choices") or []
    scope_label = selection.get("scope_label") or "empresa ativa"
    item_label_plural = selection.get("item_label_plural") or "itens"
    article = "os"
    if item_label_plural.strip().lower() in {"atividades", "instancias de processo", "reunioes"}:
        article = "as"

    if not choices:
        return (
            f"Nao encontrei {item_label_plural} em aberto no contexto atual.\n"
            "Se quiser, informe o codigo diretamente no formato campo: valor."
        )

    action = (option.action_key or "").strip().lower()
    header = f"{option.code} - {option.title}"
    if action == "onboarding.diagnose":
        lines = [
            header,
            "",
            "Selecione o objetivo do diagnostico:",
        ]
        for item in choices:
            lines.append(f"{item['index']} - {item.get('title') or item.get('code') or '-'}")
        lines.append("")
        lines.append("Informe o numero da opcao.")
        lines.append("Exemplo: 1")
        return "\n".join(lines)

    if action in {"meeting.start", "meeting.summarize"}:
        lines = [
            header,
            "",
            f"Existem {article} seguintes {item_label_plural} disponiveis para a {scope_label}:",
        ]
    else:
        lines = [
            header,
            "",
            f"Existem {article} seguintes {item_label_plural} em aberto para a {scope_label}:",
        ]
    for item in choices:
        code = item.get("code") or "-"
        title = item.get("title") or "-"
        if action in {"meeting.start", "meeting.summarize"}:
            status = item.get("status") or "-"
            when = f"{item.get('scheduled_date') or '-'} {item.get('scheduled_time') or ''}".strip()
            lines.append(f"{item['index']} - ID {code} - {title} | Status: {status} | Data: {when}")
        else:
            due_str = item.get("due_date") or "-"
            detail = item.get("project_name") or item.get("process_code") or ""
            if detail:
                lines.append(f"{item['index']} - {code} - {title} | {detail} | Prazo: {due_str}")
            else:
                lines.append(f"{item['index']} - {code} - {title} | Prazo: {due_str}")

    lines.append("")
    if action in {"meeting.start", "meeting.summarize"}:
        lines.append("Informe o numero da reuniao no formato:")
        lines.append("numero")
        lines.append("Exemplo: 1")
    else:
        lines.append(
            "Informe o numero da atividade / instancia e a data que voce quer registrar como finalizacao, no formato:"
        )
        lines.append("numero: data")
        lines.append("Exemplo: 1: 27/02/2026")
        lines.append("Se quiser usar a data de hoje, envie apenas o numero. Exemplo: 1")
    return "\n".join(lines)


def _format_confirmation(option: AgentMenuOption, payload: Dict[str, Any]) -> str:
    payload = _public_payload(payload)
    lines = [
        "Confirme que voce quer:",
        f"{option.code} - {option.title}",
    ]
    if payload:
        lines.append("com os dados:")
        for item in _build_confirmation_display_items(option, payload):
            lines.append(f"- {item}")
    else:
        lines.append("sem dados adicionais.")
    lines.append("Se estiver correto, responda 'sim'. Para cancelar, responda 'nao'.")
    return "\n".join(lines)


def _build_confirmation_display_items(option: AgentMenuOption, payload: Dict[str, Any]) -> List[str]:
    action = (option.action_key or "").strip().lower()
    items: List[str] = []

    if action == "project_task.complete":
        activity_code = str(payload.get("codigo_atividade") or "").strip()
        if activity_code:
            pretty = _format_project_task_choice_line(activity_code)
            items.append(pretty or f"codigo_atividade: {activity_code}")

        if payload.get("data_finalizacao"):
            items.append(f"data_finalizacao: {payload['data_finalizacao']}")

        for key, value in payload.items():
            if key in {"codigo_atividade", "data_finalizacao"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action == "process_instance.complete":
        instance_code = str(payload.get("codigo_instancia") or "").strip()
        if instance_code:
            pretty = _format_process_instance_choice_line(instance_code)
            items.append(pretty or f"codigo_instancia: {instance_code}")

        if payload.get("data_finalizacao"):
            items.append(f"data_finalizacao: {payload['data_finalizacao']}")

        for key, value in payload.items():
            if key in {"codigo_instancia", "data_finalizacao"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action in {"meeting.start", "meeting.summarize"}:
        meeting_value = str(
            payload.get("id_reuniao")
            or payload.get("meeting_id")
            or payload.get("codigo_reuniao")
            or payload.get("codigo")
            or ""
        ).strip()
        if meeting_value:
            pretty = _format_meeting_choice_line(meeting_value)
            items.append(pretty or f"id_reuniao: {meeting_value}")

        for key, value in payload.items():
            if key in {"id_reuniao", "meeting_id", "codigo_reuniao", "codigo"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action == "onboarding.diagnose":
        objective_raw = str(
            payload.get("objetivo")
            or payload.get("o_que_quer_funcionar")
            or payload.get("objetivo_de_funcionamento")
            or ""
        ).strip()
        if objective_raw:
            items.append(f"objetivo: {_format_objective_label(objective_raw)}")

        for key, value in payload.items():
            if key in {"objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento"}:
                continue
            items.append(f"{key}: {value}")
        return items

    for key, value in payload.items():
        items.append(f"{key}: {value}")
    return items


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
) -> str:
    action = (option.action_key or "").strip().lower()
    lines = [
        f"Voce quer fazer {option.code} - {option.title}.",
        "Para executar, faltam os seguintes dados:",
    ]
    for idx, field in enumerate(missing_fields, start=1):
        lines.append(f"{idx} - {field['label']} ({field['key']})")
    if payload:
        lines.append("")
        lines.append("Dados ja recebidos:")
        for key, value in payload.items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Envie no formato: numero: valor")
    if action == "onboarding.start":
        lines.append("Exemplos:")
        lines.append("1: real")
        lines.append("1: modelo")
    return "\n".join(lines)


def _get_or_create_session(
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
) -> AgentMenuSession:
    session = AgentMenuSession.query.filter(
        AgentMenuSession.user_id == user_id,
        AgentMenuSession.company_id == company_id,
        AgentMenuSession.channel == channel,
        AgentMenuSession.thread_id == thread_id,
    ).first()
    if session:
        return session

    session = AgentMenuSession(
        user_id=user_id,
        company_id=company_id,
        channel=channel,
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


def _match_options_by_keywords(company_id: Optional[int], lower_text: str) -> List[AgentMenuOption]:
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

    options = _dedupe_by_code(query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all(), company_id)
    scored: List[Tuple[int, AgentMenuOption]] = []
    for option in options:
        score = 0
        for keyword in option.keywords or []:
            if _normalize_text(str(keyword)) in lower_text:
                score += 2
        # fallback pelo título
        title_parts = _normalize_text(option.title).split()
        for part in title_parts:
            if len(part) > 3 and part in lower_text:
                score += 1
        if score > 0:
            scored.append((score, option))
    scored.sort(key=lambda item: (-item[0], item[1].sort_order, item[1].code))
    return [item[1] for item in scored[:10]]


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


def _ensure_default_menu_seed() -> None:
    has_global = AgentMenuOption.query.filter(
        AgentMenuOption.company_id.is_(None)
    ).first()
    if has_global:
        _ensure_default_menu_upgrades()
        return

    seed_items = [
        {"code": "1", "title": "Gestao de Projetos", "parent_code": None, "sort_order": 10},
        {"code": "1.1", "title": "Cadastrar Projeto", "parent_code": "1", "action_key": "project.create", "required_fields": [{"key": "nome_projeto", "label": "Nome do Projeto"}], "keywords": ["cadastrar projeto", "criar projeto", "novo projeto"], "sort_order": 11},
        {"code": "1.2", "title": "Editar Projeto", "parent_code": "1", "action_key": "project.update", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto"}, {"key": "dados", "label": "Dados para atualizacao"}], "keywords": ["editar projeto", "alterar projeto"], "sort_order": 12},
        {"code": "1.3", "title": "Finalizar Projeto", "parent_code": "1", "action_key": "project.complete", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto"}], "keywords": ["finalizar projeto", "encerrar projeto"], "sort_order": 13},
        {"code": "1.4", "title": "Cadastrar Atividade de Projeto", "parent_code": "1", "action_key": "project_task.create", "required_fields": [{"key": "codigo_projeto", "label": "Codigo do Projeto"}, {"key": "nome_atividade", "label": "Nome da Atividade"}], "keywords": ["cadastrar atividade", "nova atividade de projeto"], "sort_order": 14},
        {"code": "1.5", "title": "Finalizar Atividade de Projeto", "parent_code": "1", "action_key": "project_task.complete", "required_fields": [{"key": "codigo_atividade", "label": "Codigo da Atividade"}], "keywords": ["finalizar atividade de projeto", "concluir atividade"], "sort_order": 15},
        {"code": "1.6", "title": "Editar Atividade de Projeto", "parent_code": "1", "action_key": "project_task.update", "required_fields": [{"key": "codigo_atividade", "label": "Codigo da Atividade"}, {"key": "dados", "label": "Dados para atualizacao"}], "keywords": ["editar atividade", "alterar atividade de projeto"], "sort_order": 16},
        {"code": "2", "title": "Gestao de Processos", "parent_code": None, "sort_order": 20},
        {"code": "2.1", "title": "Iniciar Instancia de Processo", "parent_code": "2", "action_key": "process_instance.start", "required_fields": [{"key": "codigo_processo", "label": "Codigo do Processo"}], "keywords": ["iniciar instancia", "abrir processo"], "sort_order": 21},
        {"code": "2.2", "title": "Finalizar Instancia de Processo", "parent_code": "2", "action_key": "process_instance.complete", "required_fields": [{"key": "codigo_instancia", "label": "Codigo da Instancia"}], "keywords": ["finalizar instancia", "encerrar processo"], "sort_order": 22},
        {"code": "3", "title": "Consultas de Trabalho", "parent_code": None, "sort_order": 30},
        {"code": "3.1", "title": "Atividades em Aberto", "parent_code": "3", "action_key": "my_work.open", "required_fields": [{"key": "empresa", "label": "Empresa"}], "keywords": ["atividades em aberto", "tarefas em aberto"], "sort_order": 31},
        {"code": "3.2", "title": "Atividades Vencidas", "parent_code": "3", "action_key": "my_work.overdue", "required_fields": [{"key": "empresa", "label": "Empresa"}], "keywords": ["atividades vencidas", "tarefas vencidas"], "sort_order": 32},
        {"code": "3.3", "title": "Atividades a Vencer no Periodo", "parent_code": "3", "action_key": "my_work.due_range", "required_fields": [{"key": "empresa", "label": "Empresa"}, {"key": "periodo", "label": "Periodo"}], "keywords": ["a vencer", "proximo vencimento"], "sort_order": 33},
        {"code": "3.4", "title": "Atividades Concluidas no Periodo", "parent_code": "3", "action_key": "my_work.completed_range", "required_fields": [{"key": "empresa", "label": "Empresa"}, {"key": "periodo", "label": "Periodo"}], "keywords": ["concluidas no periodo", "atividades concluidas"], "sort_order": 34},
        {"code": "3.5", "title": "Resumos", "parent_code": "3", "sort_order": 35},
        {"code": "3.5.1", "title": "Hoje", "parent_code": "3.5", "action_key": "summary.today", "required_fields": [], "keywords": ["resumo hoje", "resumo do dia"], "sort_order": 36},
        {"code": "3.5.2", "title": "Esta Semana", "parent_code": "3.5", "action_key": "summary.week", "required_fields": [], "keywords": ["resumo semana", "esta semana"], "sort_order": 37},
        {"code": "3.5.3", "title": "Este Mes", "parent_code": "3.5", "action_key": "summary.month", "required_fields": [], "keywords": ["resumo mes", "este mes"], "sort_order": 38},
        {"code": "3.5.4", "title": "Personalizado", "parent_code": "3.5", "action_key": "summary.custom", "required_fields": [{"key": "periodo", "label": "Periodo (Data inicial e final)"}], "keywords": ["resumo personalizado", "periodo personalizado"], "sort_order": 39},
        {"code": "4", "title": "Gestao de Reunioes", "parent_code": None, "sort_order": 40},
        {"code": "4.1", "title": "Agendar Reuniao", "parent_code": "4", "action_key": "meeting.schedule", "required_fields": [{"key": "titulo", "label": "Titulo da Reuniao"}, {"key": "data_hora", "label": "Data/Hora"}], "keywords": ["agendar reuniao", "marcar reuniao"], "sort_order": 41},
        {"code": "4.2", "title": "Iniciar Reuniao", "parent_code": "4", "action_key": "meeting.start", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao"}], "keywords": ["iniciar reuniao", "comecar reuniao"], "sort_order": 42},
        {"code": "4.3", "title": "Resumir Reuniao", "parent_code": "4", "action_key": "meeting.summarize", "required_fields": [{"key": "id_reuniao", "label": "ID da Reuniao"}], "keywords": ["resumo da reuniao", "resumir reuniao"], "sort_order": 43},
        {"code": "5", "title": "Funcionamento e Onboarding", "parent_code": None, "sort_order": 50},
        {"code": "5.1", "title": "Diagnosticar Funcionamento", "parent_code": "5", "action_key": "onboarding.diagnose", "required_fields": [{"key": "objetivo", "label": "O que voce quer fazer funcionar"}], "keywords": ["diagnosticar funcionamento", "fazer funcionar", "checklist"], "sort_order": 51},
        {"code": "5.2", "title": "Status do Onboarding", "parent_code": "5", "action_key": "onboarding.status", "required_fields": [], "keywords": ["status onboarding", "campos faltantes", "onboarding"], "sort_order": 52},
        {"code": "5.3", "title": "Iniciar Onboarding Assistido", "parent_code": "5", "action_key": "onboarding.start", "required_fields": [{"key": "tipo_cadastro", "label": "Tipo de Cadastro (real ou modelo)"}], "keywords": ["iniciar onboarding", "cadastro assistido", "onboarding assistido"], "sort_order": 53},
        {"code": "5.4", "title": "Checklist para Producao", "parent_code": "5", "action_key": "onboarding.go_live_check", "required_fields": [], "keywords": ["checklist producao", "prontidao producao", "go live"], "sort_order": 54},
    ]

    code_to_id: Dict[str, int] = {}
    for item in seed_items:
        parent_id = None
        parent_code = item.get("parent_code")
        if parent_code:
            parent_id = code_to_id.get(parent_code)
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
    root_3 = _ensure_menu_option_exists(
        code="3",
        title="Consultas de Trabalho",
        parent_code=None,
        sort_order=30,
    )
    if root_3:
        _ensure_menu_option_exists(
            code="3.5",
            title="Resumos",
            parent_code="3",
            sort_order=35,
        )
        _ensure_menu_option_exists(
            code="3.5.1",
            title="Hoje",
            parent_code="3.5",
            action_key="summary.today",
            required_fields=[],
            keywords=["resumo hoje", "resumo do dia"],
            sort_order=36,
        )
        _ensure_menu_option_exists(
            code="3.5.2",
            title="Esta Semana",
            parent_code="3.5",
            action_key="summary.week",
            required_fields=[],
            keywords=["resumo semana", "esta semana"],
            sort_order=37,
        )
        _ensure_menu_option_exists(
            code="3.5.3",
            title="Este Mes",
            parent_code="3.5",
            action_key="summary.month",
            required_fields=[],
            keywords=["resumo mes", "este mes"],
            sort_order=38,
        )
        _ensure_menu_option_exists(
            code="3.5.4",
            title="Personalizado",
            parent_code="3.5",
            action_key="summary.custom",
            required_fields=[{"key": "periodo", "label": "Periodo (Data inicial e final)"}],
            keywords=["resumo personalizado", "periodo personalizado"],
            sort_order=39,
        )

    root_5 = _ensure_menu_option_exists(
        code="5",
        title="Funcionamento e Onboarding",
        parent_code=None,
        sort_order=50,
    )
    if not root_5:
        return

    _ensure_menu_option_exists(
        code="5.1",
        title="Diagnosticar Funcionamento",
        parent_code="5",
        action_key="onboarding.diagnose",
        required_fields=[{"key": "objetivo", "label": "O que voce quer fazer funcionar"}],
        keywords=["diagnosticar funcionamento", "fazer funcionar", "checklist"],
        sort_order=51,
    )
    _ensure_menu_option_exists(
        code="5.2",
        title="Status do Onboarding",
        parent_code="5",
        action_key="onboarding.status",
        required_fields=[],
        keywords=["status onboarding", "campos faltantes", "onboarding"],
        sort_order=52,
    )
    _ensure_menu_option_exists(
        code="5.3",
        title="Iniciar Onboarding Assistido",
        parent_code="5",
        action_key="onboarding.start",
        required_fields=[{"key": "tipo_cadastro", "label": "Tipo de Cadastro (real ou modelo)"}],
        keywords=["iniciar onboarding", "cadastro assistido", "onboarding assistido"],
        sort_order=53,
    )
    _ensure_menu_option_exists(
        code="5.4",
        title="Checklist para Producao",
        parent_code="5",
        action_key="onboarding.go_live_check",
        required_fields=[],
        keywords=["checklist producao", "prontidao producao", "go live"],
        sort_order=54,
    )
    db.session.commit()


def _ensure_menu_option_exists(
    code: str,
    title: str,
    parent_code: Optional[str],
    sort_order: int,
    action_key: Optional[str] = None,
    required_fields: Optional[List[Dict[str, Any]]] = None,
    keywords: Optional[List[str]] = None,
) -> Optional[AgentMenuOption]:
    existing = AgentMenuOption.query.filter(
        AgentMenuOption.company_id.is_(None),
        AgentMenuOption.code == code,
    ).first()
    if existing:
        return existing

    parent_id = None
    if parent_code:
        parent = AgentMenuOption.query.filter(
            AgentMenuOption.company_id.is_(None),
            AgentMenuOption.code == parent_code,
        ).first()
        if not parent:
            return None
        parent_id = parent.id

    option = AgentMenuOption(
        company_id=None,
        parent_id=parent_id,
        code=code,
        title=title,
        action_key=action_key,
        required_fields=required_fields or [],
        keywords=keywords or [],
        sort_order=sort_order,
        is_active=True,
    )
    db.session.add(option)
    db.session.flush()
    return option
