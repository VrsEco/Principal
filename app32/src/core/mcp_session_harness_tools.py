from __future__ import annotations

from typing import Any

from services.user_mcp_token_service import user_mcp_token_service
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_identity
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(operation: str, *, company_id: int | None = None, user_id: int | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="identity_self_service",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability=f"session_harness.{operation}",
        permissions=["identity_self_service.read"],
        tags=["session", "harness", "routing", "tenant_safe"],
    )


def register_session_harness_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_session_harness_tool() -> dict[str, Any]:
        """Descreve o harness ativo e os especialistas disponíveis na sessão MCP."""
        identity = get_http_request_identity()
        if identity is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_session_harness_unauthorized", message="Sessão MCP sem identidade autenticada."),
                meta=_meta("describe_app32_session_harness_tool"),
            ).model_dump(mode="json")
        try:
            data = user_mcp_token_service.describe_runtime_harness_scope(token=identity.token)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta("describe_app32_session_harness_tool", company_id=data.get("active_company_id"), user_id=data.get("user_id")),
            ).model_dump(mode="json")
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_session_harness_invalid_token", message=str(exc)),
                meta=_meta("describe_app32_session_harness_tool"),
            ).model_dump(mode="json")

    @mcp.tool()
    def select_app32_session_harness_tool(harness_key: str) -> dict[str, Any]:
        """Ativa um harness oficial do mesmo Squad Cliente e solicita refresh do catálogo efetivo."""
        identity = get_http_request_identity()
        if identity is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_session_harness_unauthorized", message="Sessão MCP sem identidade autenticada."),
                meta=_meta("select_app32_session_harness_tool"),
            ).model_dump(mode="json")
        try:
            data = user_mcp_token_service.select_runtime_harness(token=identity.token, harness_key=harness_key)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta("select_app32_session_harness_tool", company_id=data.get("active_company_id"), user_id=data.get("user_id")),
            ).model_dump(mode="json")
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_session_harness_invalid_selection", message=str(exc)),
                meta=_meta("select_app32_session_harness_tool"),
            ).model_dump(mode="json")


__all__ = ["register_session_harness_tools"]
