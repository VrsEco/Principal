import logging
import re
from typing import Dict, Any, Optional
from uuid import uuid4

from src.intelligence.tool_context import (
    set_sapiens_context,
    reset_sapiens_context,
    set_legacy_tool_context,
    reset_legacy_tool_context,
)
from src.intelligence.memory import get_checkpointer
from src.intelligence.work_agents.graph import create_work_agent_workflow
from src.intelligence.menu_engine import handle_menu_message

logger = logging.getLogger(__name__)

WORKFLOW_GAP_NOISE_IGNORED = "noise_ignored"
WORKFLOW_GAP_AMBIGUOUS_NEEDS_CLARIFICATION = "ambiguous_needs_clarification"
WORKFLOW_GAP_ENTITY_RESOLUTION_FAILED = "entity_resolution_failed"
WORKFLOW_GAP_PARSER_FAILED = "parser_failed"
WORKFLOW_GAP_NOT_SUPPORTED = "not_supported_workflow"
WORKFLOW_GAP_RESOLVED_BY_AI = "resolved_by_ai"
WORKFLOW_GAP_NOT_RESOLVED = "not_resolved"

_NOISE_PATTERNS = (
    r"mensagem automatica",
    r"mensagem automática",
    r"fora do horario",
    r"fora do horário",
    r"fora do expediente",
    r"ausencia",
    r"ausência",
    r"deixe sua mensagem",
    r"como posso ajudar\?? deixe sua mensagem",
    r"retornaremos",
    r"retornarei",
    r"proxima hora",
    r"próxima hora",
    r"proximo dia util",
    r"próximo dia útil",
)
_LOW_SIGNAL_MESSAGES = {
    "oi",
    "ola",
    "olá",
    "bom dia",
    "boa tarde",
    "boa noite",
    "ok",
    "blz",
    "ai lascou",
    "aí lascou",
}

_ENTITY_RESOLUTION_FAILURE_PATTERNS = (
    r"nao encontrei empresa",
    r"não encontrei empresa",
    r"encontrei mais de uma empresa",
    r"escolha uma empresa",
    r"informe a empresa",
    r"nao encontrei colaborador",
    r"não encontrei colaborador",
    r"encontrei mais de um colaborador",
    r"sem acesso ao colaborador",
)


def _classify_workflow_gap(
    *,
    user_msg: str,
    response_text: str,
    menu_metadata: Optional[Dict[str, Any]],
) -> tuple[bool, str]:
    raw_text = str(user_msg or "").strip()
    if not raw_text:
        return False, WORKFLOW_GAP_NOISE_IGNORED

    normalized_text = re.sub(r"\s+", " ", raw_text.casefold()).strip()
    if normalized_text in _LOW_SIGNAL_MESSAGES:
        return False, WORKFLOW_GAP_NOISE_IGNORED

    if any(re.search(pattern, normalized_text, flags=re.IGNORECASE) for pattern in _NOISE_PATTERNS):
        return False, WORKFLOW_GAP_NOISE_IGNORED

    workflow_discovery = dict((menu_metadata or {}).get("workflow_discovery") or {})
    confidence = dict(workflow_discovery.get("confidence") or {})
    route = str(confidence.get("route") or "").strip().lower()
    candidate_count = int(workflow_discovery.get("candidate_count") or confidence.get("candidate_count") or 0)
    normalized_response = re.sub(r"\s+", " ", str(response_text or "").casefold()).strip()

    if normalized_response and any(
        re.search(pattern, normalized_response, flags=re.IGNORECASE)
        for pattern in _ENTITY_RESOLUTION_FAILURE_PATTERNS
    ):
        return True, WORKFLOW_GAP_ENTITY_RESOLUTION_FAILED

    if route == "ambiguous" or candidate_count > 1:
        return True, WORKFLOW_GAP_AMBIGUOUS_NEEDS_CLARIFICATION
    if route == "no_match":
        return True, WORKFLOW_GAP_NOT_SUPPORTED
    if not response_text:
        return True, WORKFLOW_GAP_NOT_RESOLVED
    if workflow_discovery:
        return True, WORKFLOW_GAP_PARSER_FAILED
    return True, WORKFLOW_GAP_RESOLVED_BY_AI


def _merge_execution_metadata(*items: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for item in items:
        if not item:
            continue
        for key, value in item.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                nested = dict(merged[key])
                nested.update(value)
                merged[key] = nested
            elif isinstance(value, dict):
                merged[key] = dict(value)
            else:
                merged[key] = value
    return merged


def _build_execution_metadata(
    *,
    execution_id: str,
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
    thread_prefix: str,
    menu_intercepted: bool,
) -> Dict[str, Any]:
    return {
        "execution_context": {
            "execution_id": execution_id,
            "user_id": user_id,
            "company_id": company_id,
            "channel": channel,
            "thread_id": thread_id,
            "thread_prefix": thread_prefix,
            "menu_intercepted": menu_intercepted,
        }
    }




def _capture_workflow_gap_from_execution(
    *,
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
    user_msg: str,
    response_text: str,
    menu_metadata: Optional[Dict[str, Any]],
) -> None:
    from services.workflow_gap_service import capture_workflow_gap

    try:
        should_capture, resolution_type = _classify_workflow_gap(
            user_msg=user_msg,
            response_text=response_text,
            menu_metadata=menu_metadata,
        )
        if not should_capture:
            return
        final_telemetry = dict(menu_metadata or {})
        workflow_gap_meta = dict(final_telemetry.get("workflow_gap") or {})
        workflow_gap_meta["resolution_type"] = resolution_type
        final_telemetry["workflow_gap"] = workflow_gap_meta
        capture_workflow_gap(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
            request_text=user_msg,
            response_text=response_text,
            resolution_type=resolution_type,
            source="ai_fallback",
            telemetry=final_telemetry,
        )
    except Exception:
        logger.exception(
            "Falha ao capturar workflow gap | user=%s company=%s channel=%s thread=%s",
            user_id,
            company_id,
            channel,
            thread_id,
        )


def _capture_workflow_usage_from_execution(
    *,
    user_id: int,
    company_id: Optional[int],
    channel: str,
    thread_id: str,
    user_msg: str,
    response_text: str,
    menu_metadata: Optional[Dict[str, Any]],
) -> None:
    from services.workflow_usage_service import record_workflow_usage_event

    try:
        record_workflow_usage_event(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
            request_text=user_msg,
            response_text=response_text,
            menu_metadata=dict(menu_metadata or {}),
        )
    except Exception:
        logger.exception(
            "Falha ao auditar uso de workflow | user=%s company=%s channel=%s thread=%s",
            user_id,
            company_id,
            channel,
            thread_id,
        )

def run_agent_with_context(
    user_id: int,
    user_msg: str,
    channel: str = "web",
    thread_prefix: str = "chat",
    thread_id: Optional[str] = None,
    company_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executa o workflow do Agente Sapiens com gestão de contexto unificada (@ARQUITETO).
    Suporta: Web, Telegram, Instagram, WhatsApp, E-mail.
    """
    if not company_id:
        from models.employee import Employee
        first_emp = Employee.query.filter_by(user_id=user_id).first()
        if first_emp:
            company_id = first_emp.company_id

    if not thread_id:
        thread_id = f"{thread_prefix}_{user_id}"

    execution_id = uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    context_metadata = _merge_execution_metadata(
        metadata,
        _build_execution_metadata(
            execution_id=execution_id,
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
            thread_prefix=thread_prefix,
            menu_intercepted=False,
        ),
    )

    token = set_sapiens_context(
        user_id=user_id,
        company_id=company_id,
        channel=channel,
        thread_id=thread_id,
        metadata=context_metadata,
    )
    legacy_tokens = set_legacy_tool_context(user_id=user_id, company_id=company_id)

    try:
        menu_result = handle_menu_message(
            user_id=user_id,
            company_id=company_id,
            channel=channel,
            thread_id=thread_id,
            message=user_msg,
        )
        if menu_result.handled:
            final_menu_metadata = _merge_execution_metadata(
                menu_result.metadata,
                _build_execution_metadata(
                    execution_id=execution_id,
                    user_id=user_id,
                    company_id=company_id,
                    channel=channel,
                    thread_id=thread_id,
                    thread_prefix=thread_prefix,
                    menu_intercepted=True,
                ),
            )
            _capture_workflow_usage_from_execution(
                user_id=user_id,
                company_id=company_id,
                channel=channel,
                thread_id=thread_id,
                user_msg=user_msg,
                response_text=menu_result.response_text or "",
                menu_metadata=final_menu_metadata,
            )
            return {
                "messages": [("ai", menu_result.response_text or "")],
                "next_node": "sapiens",
                "menu_metadata": final_menu_metadata,
            }
        if menu_result.override_message:
            user_msg = menu_result.override_message

        with get_checkpointer() as checkpointer:
            graph = create_work_agent_workflow(checkpointer=checkpointer)

            inputs = {
                "messages": [("user", user_msg)],
                "user_id": user_id,
                "company_id": company_id
            }

            logger.info(
                "SAPIENS INVOKE [%s]: Thread %s | User %s | Company %s | Execution %s",
                channel.upper(),
                thread_id,
                user_id,
                company_id,
                execution_id,
            )
            response = graph.invoke(inputs, config=config)
            response["menu_metadata"] = _merge_execution_metadata(
                response.get("menu_metadata"),
                menu_result.metadata,
                _build_execution_metadata(
                    execution_id=execution_id,
                    user_id=user_id,
                    company_id=company_id,
                    channel=channel,
                    thread_id=thread_id,
                    thread_prefix=thread_prefix,
                    menu_intercepted=False,
                ),
            )
            response_text = extract_response_text(response)
            _capture_workflow_usage_from_execution(
                user_id=user_id,
                company_id=company_id,
                channel=channel,
                thread_id=thread_id,
                user_msg=user_msg,
                response_text=response_text,
                menu_metadata=response.get("menu_metadata"),
            )
            _capture_workflow_gap_from_execution(
                user_id=user_id,
                company_id=company_id,
                channel=channel,
                thread_id=thread_id,
                user_msg=user_msg,
                response_text=response_text,
                menu_metadata=response.get("menu_metadata"),
            )
            return response

    except Exception as e:
        logger.error(
            "SAPIENS ERROR [%s]: Thread %s | User %s | Company %s | Execution %s | Error=%s",
            channel.upper(),
            thread_id,
            user_id,
            company_id,
            execution_id,
            str(e),
        )
        raise e
    finally:
        reset_legacy_tool_context(legacy_tokens)
        reset_sapiens_context(token)


def extract_response_text(response: Dict[str, Any]) -> str:
    """Extrai o texto final da resposta do LangGraph."""
    final_messages = response.get("messages", [])
    if not final_messages:
        return "Desculpe, não consegui processar sua solicitação."

    last_message = final_messages[-1]

    if hasattr(last_message, 'content'):
        return last_message.content

    if isinstance(last_message, tuple):
        return last_message[1]

    return str(last_message)
