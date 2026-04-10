from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_CRUD_CONTRACTS_MANIFEST,
    CRUDDomain,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _contract_meta(operation: str, domain: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain=domain or "mcp_contracts",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_contracts.{operation}",
        permissions=["mcp.contracts.read"],
        tags=["crud", "contracts", "ai_readable"],
    )


def _success(operation: str, data: Any, domain: str | None = None) -> dict[str, Any]:
    envelope = MCPSuccessEnvelope[Any](
        data=data,
        meta=_contract_meta(operation, domain=domain),
    )
    return envelope.model_dump(mode="json")


def _error(operation: str, message: str, domain: str | None = None) -> dict[str, Any]:
    envelope = MCPErrorEnvelope(
        error=MCPErrorDetail(code="crud_contract_not_found", message=message),
        meta=_contract_meta(operation, domain=domain),
    )
    return envelope.model_dump(mode="json")


def register_crud_contract_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta dos contratos CRUD por domínio."""

    @mcp.tool()
    def describe_app32_crud_contracts_tool(domain: Optional[str] = None) -> dict[str, Any]:
        """
        Descreve os contratos CRUD MCP do APP32 por domínio:
        routine, projects, meetings, finance e strategy.
        """
        if not domain:
            return _success(
                "crud_contracts.describe",
                APP32_CRUD_CONTRACTS_MANIFEST.model_dump(mode="json"),
            )

        normalized = domain.strip().lower()
        if normalized not in {"routine", "projects", "meetings", "finance", "strategy"}:
            return _error(
                "crud_contracts.describe",
                f"Domínio CRUD MCP inválido: {domain}.",
                domain=normalized or None,
            )

        contract = APP32_CRUD_CONTRACTS_MANIFEST.get_domain(normalized)  # type: ignore[arg-type]
        if contract is None:
            return _error(
                "crud_contracts.describe",
                f"Contrato CRUD MCP não encontrado para domínio: {domain}.",
                domain=normalized,
            )
        return _success(
            "crud_contracts.describe",
            contract.model_dump(mode="json"),
            domain=normalized,
        )


__all__ = ["register_crud_contract_tools"]
