from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_EXTERNAL_AI_ONBOARDING_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, surface: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_external_ai_onboarding",
        operation=operation,
        scope="mcp_admin",
        capability=f"mcp_external_ai_onboarding.{operation}",
        permissions=["mcp.external_ai_onboarding.read"],
        tags=["onboarding", "external-ai", "mcp", *(["surface:" + surface] if surface else [])],
    )


def register_external_ai_onboarding_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_external_ai_onboarding_tool(surface: Optional[str] = None) -> dict[str, Any]:
        """Descreve o manual de onboarding de IAs externas via MCP."""
        if not surface:
            return MCPSuccessEnvelope[Any](
                data=APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.model_dump(mode="json"),
                meta=_meta("external_ai_onboarding.describe"),
            ).model_dump(mode="json")

        normalized = surface.strip().lower()
        rule = APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.get_surface_rule(normalized)
        if rule is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="external_ai_onboarding_surface_not_found",
                    message=f"Surface de onboarding não encontrada: {surface}.",
                ),
                meta=_meta("external_ai_onboarding.describe", surface=normalized or None),
            ).model_dump(mode="json")

        return MCPSuccessEnvelope[Any](
            data=rule.model_dump(mode="json"),
            meta=_meta("external_ai_onboarding.describe", surface=rule.surface),
        ).model_dump(mode="json")


__all__ = ["register_external_ai_onboarding_tools"]
