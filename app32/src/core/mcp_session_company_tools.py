from __future__ import annotations

from typing import Any

from services.user_mcp_token_service import user_mcp_token_service
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_identity
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, *, company_id: int | None = None, user_id: int | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="session_company",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability=f"session_company.{operation}",
        permissions=["mcp.session_company.manage"],
        tags=["session", "company", "mcp:user"],
    )


def register_session_company_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_session_company_scope_tool() -> dict[str, Any]:
        """Descreve as empresas acessíveis e a seleção ativa da sessão MCP do usuário."""

        identity = get_http_request_identity()
        if identity is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_unauthorized",
                    message="Sessão MCP sem identidade autenticada.",
                ),
                meta=_meta("describe_app32_session_company_scope_tool"),
            ).model_dump(mode="json")

        try:
            data = user_mcp_token_service.describe_runtime_company_scope(token=identity.token)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(
                    "describe_app32_session_company_scope_tool",
                    company_id=data.get("active_company_id"),
                    user_id=data.get("user_id"),
                ),
            ).model_dump(mode="json")
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_invalid_token",
                    message=str(exc),
                ),
                meta=_meta("describe_app32_session_company_scope_tool"),
            ).model_dump(mode="json")

    @mcp.tool()
    def select_app32_session_company_tool(company_id: int) -> dict[str, Any]:
        """Seleciona explicitamente a empresa ativa da sessão MCP do usuário."""

        identity = get_http_request_identity()
        if identity is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_unauthorized",
                    message="Sessão MCP sem identidade autenticada.",
                ),
                meta=_meta("select_app32_session_company_tool"),
            ).model_dump(mode="json")

        try:
            data = user_mcp_token_service.select_runtime_company(
                token=identity.token,
                company_id=company_id,
                client_name=str(identity.metadata.get("client_name") or "claude_remote_connector"),
            )
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(
                    "select_app32_session_company_tool",
                    company_id=data.get("active_company_id"),
                    user_id=data.get("user_id"),
                ),
            ).model_dump(mode="json")
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_invalid_selection",
                    message=str(exc),
                ),
                meta=_meta("select_app32_session_company_tool"),
            ).model_dump(mode="json")

    @mcp.tool()
    def clear_app32_session_company_tool() -> dict[str, Any]:
        """Limpa a empresa ativa persistida da sessão/token MCP do usuário."""

        identity = get_http_request_identity()
        if identity is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_unauthorized",
                    message="Sessão MCP sem identidade autenticada.",
                ),
                meta=_meta("clear_app32_session_company_tool"),
            ).model_dump(mode="json")

        try:
            data = user_mcp_token_service.clear_runtime_company(token=identity.token)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(
                    "clear_app32_session_company_tool",
                    company_id=data.get("active_company_id"),
                    user_id=data.get("user_id"),
                ),
            ).model_dump(mode="json")
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_session_company_invalid_token",
                    message=str(exc),
                ),
                meta=_meta("clear_app32_session_company_tool"),
            ).model_dump(mode="json")


__all__ = ["register_session_company_tools"]
