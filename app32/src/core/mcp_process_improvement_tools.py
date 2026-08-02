from __future__ import annotations

from typing import Any, Optional

from services.process_bpms_analysis_service import (
    build_squad_analysis_context,
    list_bpms_analyses,
    submit_squad_analysis,
)
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, *, company_id: int, write: bool = False) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="processes",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        actor_role=get_http_actor_role(),
        capability=f"process_improvement.{operation}",
        human_gate_required=write,
        permissions=["processes.ai_assistant.view"] if not write else ["processes.ai_assistant.execute"],
        tags=["processes", "improvement", "squad_cliente", "mcp_first", "tenant_safe"],
    )


def _success(operation: str, data: Any, *, company_id: int, write: bool = False) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](data=data, meta=_meta(operation, company_id=company_id, write=write)).model_dump(mode="json")


def _error(operation: str, exc: Exception, *, company_id: int, write: bool = False) -> dict[str, Any]:
    code = "process_improvement_error"
    if isinstance(exc, PermissionError):
        code = "process_improvement_forbidden"
    elif isinstance(exc, ValueError):
        code = "process_improvement_invalid_request"
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=str(exc)),
        meta=_meta(operation, company_id=company_id, write=write),
    ).model_dump(mode="json")


def _authenticated_user_id() -> int | None:
    value = dict(get_http_request_context() or {}).get("user_id")
    return int(value) if value not in (None, "") else None


def register_process_improvement_tools(mcp: Any) -> None:
    """Registra o contrato MCP da Central de Melhorias para o Squad Cliente."""

    @mcp.tool()
    def list_process_improvement_requests_tool(
        company_id: int,
        process_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Lista solicitações e análises da empresa, opcionalmente filtradas por processo."""
        operation = "request.list"
        try:
            return _success(
                operation,
                list_bpms_analyses(company_id=company_id, process_id=process_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def get_process_improvement_analysis_context_tool(
        company_id: int,
        analysis_id: int,
    ) -> dict[str, Any]:
        """Obtém briefing, contexto do processo e contrato esperado para a análise."""
        operation = "analysis_context.get"
        try:
            return _success(
                operation,
                build_squad_analysis_context(company_id=company_id, analysis_id=analysis_id),
                company_id=company_id,
            )
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id)

    @mcp.tool()
    def submit_process_improvement_analysis_tool(
        company_id: int,
        analysis_id: int,
        payload: dict[str, Any],
        human_gate_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Grava a sugestão do Squad Cliente após confirmação humana explícita."""
        operation = "analysis.submit"
        try:
            if human_gate_confirmed is not True:
                raise PermissionError("Confirmação humana explícita é obrigatória para gravar a análise.")
            analysis = submit_squad_analysis(
                company_id=company_id,
                analysis_id=analysis_id,
                payload=payload,
                actor_user_id=_authenticated_user_id(),
            )
            return _success(operation, analysis.to_dict(), company_id=company_id, write=True)
        except Exception as exc:  # pragma: no cover - envelope defensivo
            return _error(operation, exc, company_id=company_id, write=True)


__all__ = ["register_process_improvement_tools"]
