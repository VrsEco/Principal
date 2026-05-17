from __future__ import annotations

from typing import Any, Optional

from services.sapiens_activation_service import SapiensActivationService
from src.core.mcp_http_auth import get_http_request_context
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(operation: str, *, company_id: int | None = None, user_id: int | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_sapiens_activation",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        capability=f"mcp_sapiens_activation.{operation}",
        permissions=["mcp.sapiens_activation.read"],
        tags=["sapiens", "activation", "squad_selection"],
    )


def _success(operation: str, data: Any, *, company_id: int | None = None, user_id: int | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, company_id=company_id, user_id=user_id),
    ).model_dump(mode="json")


def _error(operation: str, message: str, *, company_id: int | None = None, user_id: int | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="sapiens_activation_invalid_request", message=message),
        meta=_meta(operation, company_id=company_id, user_id=user_id),
    ).model_dump(mode="json")


def register_sapiens_activation_tools(mcp: Any) -> None:
    """Registra tools MCP para descoberta de squads disponíveis e ativação genérica do Sapiens."""

    @mcp.tool()
    def describe_app32_available_sapiens_squads_tool(
        installed_squads: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Lista quais squads Sapiens estão disponíveis para o contexto atual e qual pergunta deve ser feita ao usuário no comando genérico Sapiens On.
        """
        http_context = dict(get_http_request_context() or {})
        company_id = http_context.get("company_id") if isinstance(http_context.get("company_id"), int) else None
        user_id = http_context.get("user_id") if isinstance(http_context.get("user_id"), int) else None
        role = str(http_context.get("fallback_role") or "").strip().lower() or None
        squads = SapiensActivationService.list_available_squads(role=role, installed_squads=installed_squads)
        payload = {
            "available_squads": squads,
            "selection_prompt": SapiensActivationService.selection_prompt_for_squads(squads),
            "free_text_aliases": ["Sapiens On", "sapiens on", "/sapiens-on"],
        }
        return _success("sapiens_activation.available_squads", payload, company_id=company_id, user_id=user_id)

    @mcp.tool()
    def resolve_app32_sapiens_activation_tool(
        squad: Optional[str] = None,
        installed_squads: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Resolve o comportamento do comando genérico Sapiens On: pedir escolha quando houver mais de um squad ou devolver o payload de ativação do squad escolhido.
        """
        http_context = dict(get_http_request_context() or {})
        company_id = http_context.get("company_id") if isinstance(http_context.get("company_id"), int) else None
        user_id = http_context.get("user_id") if isinstance(http_context.get("user_id"), int) else None
        role = str(http_context.get("fallback_role") or "").strip().lower() or None
        try:
            payload = SapiensActivationService.resolve_activation(
                role=role,
                squad=squad,
                installed_squads=installed_squads,
                company_id=company_id,
            )
        except ValueError as exc:
            return _error("sapiens_activation.resolve", str(exc), company_id=company_id, user_id=user_id)
        return _success("sapiens_activation.resolve", payload, company_id=company_id, user_id=user_id)


__all__ = ["register_sapiens_activation_tools"]
