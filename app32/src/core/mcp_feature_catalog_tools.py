from __future__ import annotations

import os
from typing import Any

from services.mcp_feature_catalog_service import (
    MCPDocumentationContext,
    MCPFeatureCatalogAccessError,
    MCPFeatureCatalogContextError,
    MCPFeatureCatalogNotFoundError,
    MCPFeatureCatalogService,
)
from src.core.mcp_http_auth import get_http_request_context
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _resolve_documentation_context(payload: dict[str, Any] | None = None) -> MCPDocumentationContext:
    source = dict(payload or {})
    http_context = dict(get_http_request_context() or {})

    return MCPDocumentationContext(
        company_id=_coerce_optional_int(
            source.get("company_id")
            or http_context.get("company_id")
            or os.environ.get("APP32_MCP_COMPANY_ID")
            or os.environ.get("ACTIVE_COMPANY_ID")
        ),
        user_id=_coerce_optional_int(
            source.get("user_id")
            or http_context.get("user_id")
            or os.environ.get("APP32_MCP_USER_ID")
            or os.environ.get("ACTIVE_USER_ID")
        ),
        role=str(
            source.get("role")
            or http_context.get("fallback_role")
            or os.environ.get("APP32_MCP_FALLBACK_ROLE")
            or "colaborador"
        ).strip().lower(),
        surface=str(
            source.get("surface")
            or http_context.get("surface")
            or os.environ.get("APP32_MCP_SURFACE")
            or "user"
        ).strip().lower(),
        client=str(
            source.get("client")
            or http_context.get("client")
            or os.environ.get("APP32_MCP_CLIENT")
            or "claude_code"
        ).strip().lower(),
        transport=str(
            source.get("transport")
            or http_context.get("transport")
            or "stdio"
        ).strip().lower(),
        thread_id=str(
            source.get("thread_id")
            or http_context.get("thread_id")
            or os.environ.get("APP32_MCP_THREAD_ID")
            or os.environ.get("APP32_MCP_SESSION_ID")
            or ""
        ).strip()
        or None,
    )


def _meta(context: MCPDocumentationContext, operation: str) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_feature_catalog",
        operation=operation,
        scope=f"mcp_{context.surface}",
        company_id=context.company_id,
        user_id=context.user_id,
        actor_role=context.role,
        capability=f"mcp_feature_catalog.{operation}",
        permissions=["mcp.feature_catalog.read"],
        tags=["documentation", "catalog", f"surface:{context.surface}", f"client:{context.client}"],
    )


def register_feature_catalog_tools(mcp: Any) -> None:
    service = MCPFeatureCatalogService()

    @mcp.tool()
    def bootstrap_session_context(
        company_id: int | None = None,
        user_id: int | None = None,
        domain: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Resolve contexto documental inicial e retorna catálogo resumido filtrado."""

        payload = {
            "company_id": company_id,
            "user_id": user_id,
        }
        context = _resolve_documentation_context(payload)
        try:
            data = service.bootstrap_context(context, domain=domain, search=search)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(context, "bootstrap_session_context"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogContextError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_missing_context",
                    message=str(exc),
                ),
                meta=_meta(context, "bootstrap_session_context"),
            ).model_dump(mode="json")

    @mcp.tool()
    def list_feature_catalog(
        company_id: int | None = None,
        user_id: int | None = None,
        domain: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Lista o catálogo resumido de features permitido para a surface atual."""

        payload = {
            "company_id": company_id,
            "user_id": user_id,
        }
        context = _resolve_documentation_context(payload)
        try:
            service._require_company_context(context)
            data = {
                "features": service.list_features(context.surface, domain=domain, search=search),
            }
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(context, "list_feature_catalog"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogContextError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_missing_context",
                    message=str(exc),
                ),
                meta=_meta(context, "list_feature_catalog"),
            ).model_dump(mode="json")

    @mcp.tool()
    def get_feature_guide(
        feature_id: str,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Retorna o guia operacional da feature solicitada."""

        context = _resolve_documentation_context(
            {
                "company_id": company_id,
                "user_id": user_id,
            }
        )
        try:
            service._require_company_context(context)
            data = service.get_feature_guide(feature_id, context.surface)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(context, "get_feature_guide"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogContextError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_missing_context",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_guide"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogAccessError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_forbidden_surface",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_guide"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogNotFoundError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_feature_not_found",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_guide"),
            ).model_dump(mode="json")

    @mcp.tool()
    def get_feature_examples(
        feature_id: str,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Retorna exemplos operacionais autorizados da feature."""

        context = _resolve_documentation_context(
            {
                "company_id": company_id,
                "user_id": user_id,
            }
        )
        try:
            service._require_company_context(context)
            data = service.get_feature_examples(feature_id, context.surface)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(context, "get_feature_examples"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogContextError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_missing_context",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_examples"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogAccessError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_forbidden_surface",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_examples"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogNotFoundError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_feature_not_found",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_examples"),
            ).model_dump(mode="json")

    @mcp.tool()
    def get_feature_constraints(
        feature_id: str,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Retorna restrições funcionais e de segurança da feature."""

        context = _resolve_documentation_context(
            {
                "company_id": company_id,
                "user_id": user_id,
            }
        )
        try:
            service._require_company_context(context)
            data = service.get_feature_constraints(feature_id, context.surface)
            return MCPSuccessEnvelope[Any](
                data=data,
                meta=_meta(context, "get_feature_constraints"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogContextError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_missing_context",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_constraints"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogAccessError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_forbidden_surface",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_constraints"),
            ).model_dump(mode="json")
        except MCPFeatureCatalogNotFoundError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="mcp_feature_catalog_feature_not_found",
                    message=str(exc),
                ),
                meta=_meta(context, "get_feature_constraints"),
            ).model_dump(mode="json")


__all__ = ["register_feature_catalog_tools"]
