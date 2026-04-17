from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


MCPProfileName = Literal["colaborador", "cliente", "administrador", "admin_tecnico"]
MCPAllowedSurface = Literal["user", "admin", "analytics", "ops"]
MCPMutationRisk = Literal["low", "medium", "high", "critical"]


class MCPProfileContract(_StrictModel):
    profile: MCPProfileName
    allowed_surfaces: list[MCPAllowedSurface] = Field(default_factory=list, min_length=1)
    default_surface: MCPAllowedSurface
    allowed_domains: list[str] = Field(default_factory=list, min_length=1)
    forbidden_domains: list[str] = Field(default_factory=list)
    max_risk_without_human_gate: MCPMutationRisk = "medium"
    requires_explicit_company_for_admin_surfaces: bool = True
    can_execute_mutations: bool = False
    can_execute_financial_mutations: bool = False
    can_access_admin_domains: bool = False
    can_access_analytics: bool = False
    can_access_ops: bool = False
    tenant_scope_required: bool = True
    audit_required: bool = True

    @model_validator(mode="after")
    def _validate_profile_contract(self):
        if self.default_surface not in self.allowed_surfaces:
            raise ValueError("default_surface deve pertencer a allowed_surfaces.")
        if not self.tenant_scope_required or not self.audit_required:
            raise ValueError("Contratos de perfil MCP exigem tenant_scope_required=True e audit_required=True.")
        if self.profile in {"colaborador", "cliente"} and any(
            surface in {"admin", "analytics", "ops"} for surface in self.allowed_surfaces
        ):
            raise ValueError("Perfis não administrativos não podem acessar surfaces privilegiadas.")
        if self.can_execute_financial_mutations and self.profile not in {"administrador", "admin_tecnico"}:
            raise ValueError("Mutações financeiras ficam restritas a perfis administrativos.")
        if self.can_access_ops and self.profile != "admin_tecnico":
            raise ValueError("Surface ops fica restrita ao perfil admin_tecnico.")
        return self


class MCPProfileContractsManifest(_StrictModel):
    version: str = Field(default="app32.mcp.profiles.v1", min_length=1, max_length=80)
    profiles: list[MCPProfileContract] = Field(default_factory=list, min_length=1)

    def get_profile(self, profile: MCPProfileName | str) -> MCPProfileContract | None:
        normalized = str(profile).strip().lower()
        alias = "admin_tecnico" if normalized == "administrador_tecnico" else normalized
        for contract in self.profiles:
            if contract.profile == alias:
                return contract
        return None


MCPProfileContractsEnvelope = MCPSuccessEnvelope[MCPProfileContractsManifest | MCPProfileContract]


def build_app32_profile_contracts_manifest() -> MCPProfileContractsManifest:
    return MCPProfileContractsManifest(
        profiles=[
            MCPProfileContract(
                profile="colaborador",
                allowed_surfaces=["user"],
                default_surface="user",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "identity_self_service"],
                forbidden_domains=["finance", "governance", "admin", "analytics", "operations", "workload", "identity_admin"],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
            ),
            MCPProfileContract(
                profile="cliente",
                allowed_surfaces=["user"],
                default_surface="user",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "identity_self_service"],
                forbidden_domains=["finance", "governance", "admin", "analytics", "operations", "workload", "identity_admin"],
                max_risk_without_human_gate="low",
                can_execute_mutations=False,
            ),
            MCPProfileContract(
                profile="administrador",
                allowed_surfaces=["user", "admin", "analytics"],
                default_surface="admin",
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "finance",
                    "strategy",
                    "governance",
                    "analytics",
                    "workload",
                    "identity_self_service",
                    "identity_admin",
                ],
                forbidden_domains=["operations"],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
                can_execute_financial_mutations=True,
                can_access_admin_domains=True,
                can_access_analytics=True,
            ),
            MCPProfileContract(
                profile="admin_tecnico",
                allowed_surfaces=["admin", "analytics", "ops"],
                default_surface="ops",
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "finance",
                    "strategy",
                    "governance",
                    "analytics",
                    "workload",
                    "operations",
                    "identity_self_service",
                    "identity_admin",
                ],
                forbidden_domains=[],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
                can_execute_financial_mutations=True,
                can_access_admin_domains=True,
                can_access_analytics=True,
                can_access_ops=True,
            ),
        ]
    )


APP32_PROFILE_CONTRACTS_MANIFEST = build_app32_profile_contracts_manifest()


__all__ = [
    "APP32_PROFILE_CONTRACTS_MANIFEST",
    "MCPAllowedSurface",
    "MCPMutationRisk",
    "MCPProfileContract",
    "MCPProfileContractsEnvelope",
    "MCPProfileContractsManifest",
    "MCPProfileName",
    "build_app32_profile_contracts_manifest",
]
