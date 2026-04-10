from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_PROFILE_CONTRACTS_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, profile: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_profiles",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_profiles.{operation}",
        permissions=["mcp.profiles.read"],
        tags=["profile", "surface", *(["profile:" + profile] if profile else [])],
    )


def _success(operation: str, data: Any, profile: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, profile=profile),
    ).model_dump(mode="json")


def _error(operation: str, message: str, profile: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="profile_contract_not_found", message=message),
        meta=_meta(operation, profile=profile),
    ).model_dump(mode="json")


def register_profile_contract_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta dos contratos por perfil."""

    @mcp.tool()
    def describe_app32_profile_contracts_tool(profile: Optional[str] = None) -> dict[str, Any]:
        """
        Descreve os contratos MCP por perfil:
        colaborador, cliente, administrador e admin_tecnico.
        """
        if not profile:
            return _success(
                "profile_contracts.describe",
                APP32_PROFILE_CONTRACTS_MANIFEST.model_dump(mode="json"),
            )

        normalized = profile.strip().lower()
        contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(normalized)
        if contract is None:
            return _error(
                "profile_contracts.describe",
                f"Perfil MCP inválido ou não encontrado: {profile}.",
                profile=normalized or None,
            )

        return _success(
            "profile_contracts.describe",
            contract.model_dump(mode="json"),
            profile=contract.profile,
        )


__all__ = ["register_profile_contract_tools"]
