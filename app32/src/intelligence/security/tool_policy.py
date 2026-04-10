from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from src.intelligence.mcp_contracts import APP32_PROFILE_CONTRACTS_MANIFEST
from .tenant_rbac import (
    ADMIN_ROLES,
    PrincipalContext,
    PermissionDecision,
    TenantScopeDecision,
    resolve_identity_context,
    validate_company_id,
    validate_permission,
)

SURFACE_ALIASES = {
    "mcp_user": "user",
    "user": "user",
    "usuario": "user",
    "mcp_admin": "admin",
    "admin": "admin",
    "administrator": "admin",
    "analytics": "analytics",
    "analise": "analytics",
    "analysis": "analytics",
    "ops": "ops",
    "operation": "ops",
    "operacao": "ops",
    "legacy": "legacy",
}

RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
MUTATING_ACTIONS = {"create", "update", "delete", "approve"}
DESTRUCTIVE_ACTIONS = {"delete", "approve"}
ADMIN_DOMAINS = {"admin", "diagnostics"}


@dataclass(frozen=True)
class ToolPolicyRequest:
    """Pedido puro de autorização para uma tool IA/MCP.

    A política não depende de Flask, banco ou MCP runtime específico. Ela recebe o
    principal já resolvido ou qualquer mapping/objeto compatível com
    ``resolve_identity_context`` e retorna uma decisão auditável.
    """

    tool_name: str
    surface: str
    domain: Optional[str] = None
    action: Optional[str] = None
    risk: str = "medium"
    requested_company_id: Optional[int] = None
    accessible_company_ids: tuple[int, ...] = ()
    required_permissions: tuple[str, ...] = ()
    confirmed_mutation: bool = False
    metadata: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    request: ToolPolicyRequest
    principal: PrincipalContext
    resolved_surface: str
    resolved_risk: str
    resolved_company_id: Optional[int]
    reason: str
    checks: tuple[str, ...]

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tool_name": self.request.tool_name,
            "surface": self.resolved_surface,
            "domain": self.request.domain,
            "action": self.request.action,
            "risk": self.resolved_risk,
            "company_id": self.resolved_company_id,
            "principal": {
                "user_id": self.principal.user_id,
                "employee_id": self.principal.employee_id,
                "role": self.principal.role,
                "channel": self.principal.channel,
                "thread_id": self.principal.thread_id,
                "permissions": sorted(self.principal.permissions),
            },
            "reason": self.reason,
            "checks": list(self.checks),
        }


def _normalize_surface(surface: Any) -> str:
    value = str(surface or "user").strip().lower()
    return SURFACE_ALIASES.get(value, value or "user")


def _normalize_risk(risk: Any) -> str:
    value = str(risk or "medium").strip().lower()
    return value if value in RISK_ORDER else "medium"


def _deny(request: ToolPolicyRequest, principal: PrincipalContext, surface: str, risk: str, company_id: Optional[int], reason: str, checks: Sequence[str]) -> ToolPolicyDecision:
    return ToolPolicyDecision(False, request, principal, surface, risk, company_id, reason, tuple(checks))


def _allow(request: ToolPolicyRequest, principal: PrincipalContext, surface: str, risk: str, company_id: Optional[int], checks: Sequence[str]) -> ToolPolicyDecision:
    return ToolPolicyDecision(True, request, principal, surface, risk, company_id, "ok", tuple(checks))


def evaluate_tool_policy(source: Any, request: ToolPolicyRequest) -> ToolPolicyDecision:
    """Avalia autorização de tool por tenant, RBAC, surface e risco operacional."""

    principal = resolve_identity_context(source)
    surface = _normalize_surface(request.surface)
    risk = _normalize_risk(request.risk)
    action = (request.action or "").strip().lower() or None
    domain = (request.domain or "").strip().lower() or None
    checks: list[str] = ["normalize_surface", "normalize_risk", "resolve_principal"]
    profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(principal.role)

    if profile_contract is None:
        return _deny(request, principal, surface, risk, None, "perfil MCP não suportado", (*checks, "profile_contract_missing"))

    checks.append("resolve_profile_contract")

    if not request.tool_name.strip():
        return _deny(request, principal, surface, risk, None, "tool_name ausente", (*checks, "missing_tool_name"))

    tenant_decision: TenantScopeDecision = validate_company_id(
        principal,
        request.requested_company_id,
        accessible_company_ids=request.accessible_company_ids,
    )
    checks.append("tenant_scope")

    if not tenant_decision.allowed:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, tenant_decision.reason, (*checks, *tenant_decision.checks))

    if surface not in profile_contract.allowed_surfaces:
        return _deny(
            request,
            principal,
            surface,
            risk,
            tenant_decision.resolved_company_id,
            f"surface {surface} não permitida para o perfil {profile_contract.profile}",
            (*checks, "surface_not_allowed_for_profile"),
        )

    if domain and domain in set(profile_contract.forbidden_domains):
        return _deny(
            request,
            principal,
            surface,
            risk,
            tenant_decision.resolved_company_id,
            f"domínio {domain} não permitido para o perfil {profile_contract.profile}",
            (*checks, "domain_forbidden_for_profile"),
        )

    permission_decision: PermissionDecision = validate_permission(
        principal,
        domain=domain,
        action=action,
        required_permissions=request.required_permissions,
    )
    checks.append("domain_rbac")

    if not permission_decision.allowed:
        return _deny(
            request,
            principal,
            surface,
            risk,
            tenant_decision.resolved_company_id,
            permission_decision.reason,
            (*checks, *permission_decision.checks),
        )

    if surface == "admin" and not principal.is_admin():
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "surface admin exige perfil administrador", (*checks, "surface_admin_requires_admin"))

    if surface == "ops" and principal.role not in {"administrador_tecnico", "admin_tecnico"}:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "surface ops exige administrador técnico", (*checks, "surface_ops_requires_technical_admin"))

    if surface == "user" and domain in ADMIN_DOMAINS:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "surface user não expõe domínio administrativo", (*checks, "surface_user_blocks_admin_domain"))

    if surface == "analytics" and action in MUTATING_ACTIONS:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "surface analytics é somente leitura/análise", (*checks, "surface_analytics_read_only"))

    if surface == "analytics" and risk in {"high", "critical"} and not principal.is_admin():
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "analytics de alto risco exige administrador", (*checks, "surface_analytics_high_risk_admin_only"))

    if risk == "critical" and not principal.is_admin():
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "risco crítico exige administrador", (*checks, "critical_risk_requires_admin"))

    if action in DESTRUCTIVE_ACTIONS and not request.confirmed_mutation:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "mutação destrutiva exige confirmação explícita", (*checks, "destructive_action_requires_confirmation"))

    if risk in {"high", "critical"} and action in MUTATING_ACTIONS and not request.confirmed_mutation:
        return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, "mutação de alto risco exige confirmação explícita", (*checks, "high_risk_mutation_requires_confirmation"))

    return _allow(request, principal, surface, risk, tenant_decision.resolved_company_id, (*checks, "policy_allowed"))


def require_tool_policy(source: Any, request: ToolPolicyRequest) -> ToolPolicyDecision:
    decision = evaluate_tool_policy(source, request)
    if not decision.allowed:
        raise PermissionError(decision.reason)
    return decision
