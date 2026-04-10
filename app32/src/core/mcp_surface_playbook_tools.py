from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_SURFACE_PLAYBOOKS_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, surface: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_playbooks",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_playbooks.{operation}",
        permissions=["mcp.playbooks.read"],
        tags=["playbook", "surface", *(["surface:" + surface] if surface else [])],
    )


def _success(operation: str, data: Any, surface: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, surface=surface),
    ).model_dump(mode="json")


def _error(operation: str, message: str, surface: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="surface_playbook_not_found", message=message),
        meta=_meta(operation, surface=surface),
    ).model_dump(mode="json")


def register_surface_playbook_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta dos playbooks por surface."""

    @mcp.tool()
    def describe_app32_surface_playbooks_tool(surface: Optional[str] = None) -> dict[str, Any]:
        """
        Descreve como agentes devem interagir com o APP32 por surface MCP:
        user, admin, analytics e ops.
        """
        if not surface:
            return _success(
                "surface_playbooks.describe",
                APP32_SURFACE_PLAYBOOKS_MANIFEST.model_dump(mode="json"),
            )

        normalized = surface.strip().lower()
        if normalized not in {"user", "admin", "analytics", "ops"}:
            return _error(
                "surface_playbooks.describe",
                f"Surface MCP inválida: {surface}.",
                surface=normalized or None,
            )

        playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(normalized)  # type: ignore[arg-type]
        if playbook is None:
            return _error(
                "surface_playbooks.describe",
                f"Playbook MCP não encontrado para a surface: {surface}.",
                surface=normalized,
            )

        return _success(
            "surface_playbooks.describe",
            playbook.model_dump(mode="json"),
            surface=normalized,
        )


__all__ = ["register_surface_playbook_tools"]
