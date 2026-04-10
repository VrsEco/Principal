from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_TOOL_FREEZE_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, trigger: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_tool_freeze",
        operation=operation,
        scope="mcp_ops",
        capability=f"mcp_tool_freeze.{operation}",
        permissions=["mcp.tool_freeze.read"],
        tags=["freeze", "tool", "security", "ai", "mcp", *(["trigger:" + trigger] if trigger else [])],
    )


def register_tool_freeze_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_tool_freeze_procedure_tool(trigger: Optional[str] = None) -> dict[str, Any]:
        """Descreve o procedimento de congelamento de tool insegura IA/MCP."""
        if not trigger:
            return MCPSuccessEnvelope[Any](
                data=APP32_TOOL_FREEZE_MANIFEST.model_dump(mode="json"),
                meta=_meta("tool_freeze.describe"),
            ).model_dump(mode="json")

        normalized = trigger.strip().lower()
        rule = APP32_TOOL_FREEZE_MANIFEST.get_trigger(normalized)
        if rule is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="tool_freeze_trigger_not_found",
                    message=f"Trigger de congelamento não encontrado: {trigger}.",
                ),
                meta=_meta("tool_freeze.describe", trigger=normalized or None),
            ).model_dump(mode="json")

        return MCPSuccessEnvelope[Any](
            data=rule.model_dump(mode="json"),
            meta=_meta("tool_freeze.describe", trigger=rule.trigger),
        ).model_dump(mode="json")


__all__ = ["register_tool_freeze_tools"]
