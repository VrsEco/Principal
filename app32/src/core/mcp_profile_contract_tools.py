from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_PROFILE_CONTRACTS_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)

_OFFICIAL_SQUAD_CLIENTE_OVERLAYS = (
    "coordenador_cliente",
    "comercial_cliente",
    "operacional_cliente",
    "admfin_cliente",
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
    def describe_app32_profile_contracts_tool(
        profile: Optional[str] = None,
        overlay_role: Optional[str] = None,
        runtime_profile: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Descreve os contratos MCP por perfil:
        colaborador, cliente, administrador e admin_tecnico.
        """
        if runtime_profile:
            normalized_runtime = runtime_profile.strip().lower()
            overlays = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlays_for_profile("cliente")
            if normalized_runtime == "squad_cliente":
                official_overlays = [
                    overlay.model_dump(mode="json")
                    for overlay in overlays
                    if overlay.overlay in _OFFICIAL_SQUAD_CLIENTE_OVERLAYS
                ]
                return _success(
                    "profile_contracts.describe",
                    {
                        "runtime_profile": "squad_cliente",
                        "official_phase_label": "Fase 1 oficial",
                        "official_overlays": official_overlays,
                    },
                    profile="squad_cliente",
                )
            runtime_overlays = [
                overlay.model_dump(mode="json")
                for overlay in APP32_PROFILE_CONTRACTS_MANIFEST.role_overlays
                if overlay.runtime_profile == normalized_runtime
            ]
            if not runtime_overlays:
                return _error(
                    "profile_contracts.describe",
                    f"Runtime profile MCP inválido ou não encontrado: {runtime_profile}.",
                    profile=normalized_runtime or None,
                )
            return _success(
                "profile_contracts.describe",
                {
                    "runtime_profile": normalized_runtime,
                    "overlays": runtime_overlays,
                },
                profile=normalized_runtime,
            )

        if not profile and not overlay_role:
            return _success(
                "profile_contracts.describe",
                APP32_PROFILE_CONTRACTS_MANIFEST.model_dump(mode="json"),
            )

        if overlay_role:
            normalized_overlay = overlay_role.strip().lower()
            overlay = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay(normalized_overlay)
            if overlay is None:
                return _error(
                    "profile_contracts.describe",
                    f"Overlay MCP inválido ou não encontrado: {overlay_role}.",
                    profile=normalized_overlay or None,
                )
            return _success(
                "profile_contracts.describe",
                overlay.model_dump(mode="json"),
                profile=overlay.overlay,
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
