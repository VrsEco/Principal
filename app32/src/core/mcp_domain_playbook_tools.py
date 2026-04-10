from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_DOMAIN_PLAYBOOKS_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, domain: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_domain_playbooks",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_domain_playbooks.{operation}",
        permissions=["mcp.domain_playbooks.read"],
        tags=["playbook", "domain", *(["domain:" + domain] if domain else [])],
    )


def _success(operation: str, data: Any, domain: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, domain=domain),
    ).model_dump(mode="json")


def _error(operation: str, message: str, domain: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="domain_playbook_not_found", message=message),
        meta=_meta(operation, domain=domain),
    ).model_dump(mode="json")


def register_domain_playbook_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta dos playbooks canônicos por domínio."""

    @mcp.tool()
    def describe_app32_domain_playbooks_tool(domain: Optional[str] = None) -> dict[str, Any]:
        """
        Descreve como agentes devem interagir com o APP32 por domínio:
        routine, processes, projects, meetings, strategy, finance, analytics,
        workload, identity, operations e governance.
        """
        if not domain:
            return _success(
                "domain_playbooks.describe",
                APP32_DOMAIN_PLAYBOOKS_MANIFEST.model_dump(mode="json"),
            )

        normalized = domain.strip().lower()
        playbook = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain(normalized)
        if playbook is None:
            return _error(
                "domain_playbooks.describe",
                f"Playbook MCP não encontrado para o domínio: {domain}.",
                domain=normalized or None,
            )

        return _success(
            "domain_playbooks.describe",
            playbook.model_dump(mode="json"),
            domain=playbook.domain,
        )


__all__ = ["register_domain_playbook_tools"]
