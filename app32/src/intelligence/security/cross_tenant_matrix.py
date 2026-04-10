from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrossTenantDomainRequirement:
    domain: str
    requires_read_isolation: bool
    requires_mutation_isolation: bool
    requires_surface_rbac: bool
    requires_analytics_guard: bool
    minimum_asserts: tuple[str, ...]


REQUIRED_PROFILES = ("colaborador", "cliente", "administrador", "administrador_tecnico")
REQUIRED_SURFACES = ("user", "admin", "analytics", "ops")
REQUIRED_ASSERTS = (
    "tenant_deny_cross_company",
    "tenant_allow_same_company",
    "admin_accessible_company_scope",
    "surface_denies_admin_domain_to_user",
    "analytics_surface_is_read_only",
    "high_risk_mutation_requires_confirmation",
    "audit_payload_is_serializable_without_secrets",
)

CROSS_TENANT_DOMAIN_MATRIX: tuple[CrossTenantDomainRequirement, ...] = (
    CrossTenantDomainRequirement("routine", True, True, True, True, REQUIRED_ASSERTS[:3]),
    CrossTenantDomainRequirement("process", True, True, True, True, REQUIRED_ASSERTS[:3]),
    CrossTenantDomainRequirement("project", True, True, True, True, REQUIRED_ASSERTS[:3]),
    CrossTenantDomainRequirement("meeting", True, True, True, True, REQUIRED_ASSERTS[:3]),
    CrossTenantDomainRequirement("strategy", True, False, True, True, (REQUIRED_ASSERTS[0], REQUIRED_ASSERTS[1], REQUIRED_ASSERTS[6])),
    CrossTenantDomainRequirement("finance", True, True, True, True, REQUIRED_ASSERTS),
    CrossTenantDomainRequirement("admin", True, True, True, False, (REQUIRED_ASSERTS[2], REQUIRED_ASSERTS[3], REQUIRED_ASSERTS[5])),
    CrossTenantDomainRequirement("analytics", True, False, True, True, (REQUIRED_ASSERTS[0], REQUIRED_ASSERTS[4], REQUIRED_ASSERTS[6])),
    CrossTenantDomainRequirement("diagnostics", True, False, True, False, ("ops_surface_requires_technical_admin", REQUIRED_ASSERTS[6])),
)


def get_cross_tenant_domain_requirement(domain: str) -> CrossTenantDomainRequirement:
    normalized = str(domain or "").strip().lower()
    for requirement in CROSS_TENANT_DOMAIN_MATRIX:
        if requirement.domain == normalized:
            return requirement
    raise KeyError(f"domínio IA/MCP sem matriz cross-tenant: {domain!r}")


def domains_requiring_mutation_isolation() -> tuple[str, ...]:
    return tuple(item.domain for item in CROSS_TENANT_DOMAIN_MATRIX if item.requires_mutation_isolation)


def domains_requiring_analytics_guard() -> tuple[str, ...]:
    return tuple(item.domain for item in CROSS_TENANT_DOMAIN_MATRIX if item.requires_analytics_guard)
