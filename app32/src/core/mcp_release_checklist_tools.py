from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_RELEASE_CHECKLIST_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, selector: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_release_checklist",
        operation=operation,
        scope="mcp_ops",
        capability=f"mcp_release_checklist.{operation}",
        permissions=["mcp.release_checklist.read"],
        tags=["release", "smoke", "ai", "mcp", *(["selector:" + selector] if selector else [])],
    )


def _success(operation: str, data: Any, selector: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](data=data, meta=_meta(operation, selector=selector)).model_dump(mode="json")


def _error(operation: str, message: str, selector: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="release_checklist_item_not_found", message=message),
        meta=_meta(operation, selector=selector),
    ).model_dump(mode="json")


def register_release_checklist_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta do checklist de release/smoke IA/MCP."""

    @mcp.tool()
    def describe_app32_release_checklist_tool(
        gate: Optional[str] = None,
        smoke_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Descreve o checklist de release IA/MCP completo ou filtra por gate
        (pre_release, deploy, post_deploy, rollback) ou por smoke_id.
        """
        if smoke_id:
            normalized_smoke = smoke_id.strip().lower()
            smoke = APP32_RELEASE_CHECKLIST_MANIFEST.get_smoke(normalized_smoke)
            if smoke is None:
                return _error(
                    "release_checklist.describe",
                    f"Smoke IA/MCP não encontrado: {smoke_id}.",
                    selector=normalized_smoke or None,
                )
            return _success("release_checklist.describe", smoke.model_dump(mode="json"), selector=smoke.smoke_id)

        if gate:
            normalized_gate = gate.strip().lower()
            items = APP32_RELEASE_CHECKLIST_MANIFEST.items_for_gate(normalized_gate)
            if not items:
                return _error(
                    "release_checklist.describe",
                    f"Gate de release IA/MCP não encontrado: {gate}.",
                    selector=normalized_gate or None,
                )
            return _success(
                "release_checklist.describe",
                [item.model_dump(mode="json") for item in items],
                selector=normalized_gate,
            )

        return _success(
            "release_checklist.describe",
            APP32_RELEASE_CHECKLIST_MANIFEST.model_dump(mode="json"),
        )


__all__ = ["register_release_checklist_tools"]
