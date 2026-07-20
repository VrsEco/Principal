from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from src.intelligence.tooling.capabilities import TOOL_CONTEXT_COMPANY, TOOL_CONTEXT_USER

from src.intelligence.mcp_contracts import APP32_PERMISSION_MATRIX_MANIFEST, APP32_PROFILE_CONTRACTS_MANIFEST
from .mcp_channel_gate import McpChannelGateRequest, evaluate_mcp_channel_gate
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
MUTATING_ACTIONS = {"create", "update", "delete", "approve", "review"}
DESTRUCTIVE_ACTIONS = {"delete", "approve"}
ADMIN_DOMAINS = {"admin", "diagnostics", "identity_admin"}


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
    required_context: tuple[str, ...] = ()
    catalog_discovery: bool = False
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
            "required_context": list(self.request.required_context),
            "catalog_discovery": self.request.catalog_discovery,
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


def _normalize_required_context(required_context: Sequence[str] | None) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in required_context or ():
        value = str(item or "").strip().lower()
        if value in {TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY} and value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _validate_required_context(
    principal: PrincipalContext,
    request: ToolPolicyRequest,
    *,
    checks: Sequence[str],
) -> ToolPolicyDecision | None:
    required_context = _normalize_required_context(request.required_context)
    requested_company_id = request.requested_company_id
    metadata = dict(principal.metadata or {})
    metadata.update(dict(request.metadata or {}))

    if TOOL_CONTEXT_USER in required_context and principal.user_id is None:
        return _deny(
            request,
            principal,
            _normalize_surface(request.surface),
            _normalize_risk(request.risk),
            _coerce_optional_company_id(requested_company_id, principal.company_id),
            "feature exige user_id no contexto antes da execução",
            (*checks, "missing_required_user_context"),
        )

    if (
        TOOL_CONTEXT_COMPANY in required_context
        and _coerce_optional_company_id(requested_company_id, principal.company_id) is None
        and not request.catalog_discovery
    ):
        missing_company_reason = "feature exige company_id no contexto antes da execução"
        if bool(metadata.get("selection_required_for_mutations")) or bool(metadata.get("multi_company")):
            missing_company_reason = (
                "empresa não selecionada para esta sessão multiempresa; use "
                "select_app32_session_company_tool ou informe company_id explicitamente antes da mutação"
            )
        return _deny(
            request,
            principal,
            _normalize_surface(request.surface),
            _normalize_risk(request.risk),
            None,
            missing_company_reason,
            (*checks, "missing_required_company_context"),
        )

    return None


def _coerce_optional_company_id(*values: Any) -> Optional[int]:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
    return None


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

    metadata = dict(principal.metadata or {})
    metadata.update(dict(request.metadata or {}))
    channel_gate = evaluate_mcp_channel_gate(
        McpChannelGateRequest(
            surface=surface,
            runtime_profile=str(metadata.get("runtime_profile") or "").strip() or None,
            actor_type=str(metadata.get("actor_type") or "").strip() or None,
            mcp_enabled=bool(metadata.get("mcp_enabled", True)),
            training_completed=bool(metadata.get("training_completed", True)),
        )
    )
    checks.append("mcp_channel_gate")
    if not channel_gate.allowed:
        return _deny(
            request,
            principal,
            surface,
            risk,
            None,
            channel_gate.reason,
            (*checks, *channel_gate.checks),
        )

    overlay_key = str(metadata.get("squad_overlay") or metadata.get("harness_key") or "").strip().lower() or None
    overlay_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay(overlay_key) if overlay_key else None
    if overlay_contract is not None:
        checks.append("runtime_overlay_contract")
        if principal.role not in set(overlay_contract.compatible_profiles):
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"overlay {overlay_contract.overlay} não é compatível com o perfil base {principal.role}",
                (*checks, "runtime_overlay_incompatible_profile"),
            )
        if surface != overlay_contract.surface:
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"overlay {overlay_contract.overlay} exige surface {overlay_contract.surface}",
                (*checks, "runtime_overlay_surface_mismatch"),
            )
        if domain and domain not in set(overlay_contract.allowed_domains):
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"overlay {overlay_contract.overlay} não permite o domínio {domain}",
                (*checks, "runtime_overlay_domain_blocked"),
            )
        if action and action not in set(overlay_contract.allowed_actions):
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"overlay {overlay_contract.overlay} não permite a ação {action}",
                (*checks, "runtime_overlay_action_blocked"),
            )

        overlay_matrices = [
            item
            for item in APP32_PERMISSION_MATRIX_MANIFEST.get_overlay(overlay_key)
            if item.surface == surface
        ]
        if not overlay_matrices:
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"matriz de permissão ausente para o overlay {overlay_contract.overlay}",
                (*checks, "runtime_overlay_matrix_missing"),
            )
        overlay_matrix = overlay_matrices[0]
        domain_rule = next(
            (item for item in overlay_matrix.domains if item.domain == domain),
            None,
        )
        if domain and domain_rule is None:
            return _deny(
                request,
                principal,
                surface,
                risk,
                None,
                f"matriz do overlay {overlay_contract.overlay} não permite o domínio {domain}",
                (*checks, "runtime_overlay_matrix_domain_blocked"),
            )
        if domain_rule is not None and action:
            if action in set(domain_rule.denied_actions) or action not in set(domain_rule.allowed_actions):
                return _deny(
                    request,
                    principal,
                    surface,
                    risk,
                    None,
                    f"matriz do overlay {overlay_contract.overlay} não permite {action} em {domain}",
                    (*checks, "runtime_overlay_matrix_action_blocked"),
                )
            if action in set(domain_rule.human_gate_for_actions) and not request.confirmed_mutation:
                return _deny(
                    request,
                    principal,
                    surface,
                    risk,
                    None,
                    f"matriz do overlay {overlay_contract.overlay} exige human gate para {action} em {domain}",
                    (*checks, "runtime_overlay_matrix_human_gate_required"),
                )
            if (
                domain_rule.requires_explicit_company_id
                and request.requested_company_id is None
                and not request.catalog_discovery
            ):
                return _deny(
                    request,
                    principal,
                    surface,
                    risk,
                    None,
                    f"matriz do overlay {overlay_contract.overlay} exige company_id explícito para {domain}",
                    (*checks, "runtime_overlay_matrix_company_required"),
                )
        checks.append("runtime_overlay_permission_matrix")

    context_decision = _validate_required_context(principal, request, checks=(*checks, "required_context"))
    if context_decision is not None:
        return context_decision

    normalized_required_context = _normalize_required_context(request.required_context)
    resolved_request_company_id = _coerce_optional_company_id(
        request.requested_company_id, principal.company_id
    )
    should_validate_tenant = bool(
        resolved_request_company_id is not None
        or (TOOL_CONTEXT_COMPANY in normalized_required_context and not request.catalog_discovery)
    )

    if should_validate_tenant:
        tenant_decision: TenantScopeDecision = validate_company_id(
            principal,
            request.requested_company_id,
            accessible_company_ids=request.accessible_company_ids,
        )
        checks.append("tenant_scope")

        if not tenant_decision.allowed:
            return _deny(request, principal, surface, risk, tenant_decision.resolved_company_id, tenant_decision.reason, (*checks, *tenant_decision.checks))
    else:
        tenant_decision = TenantScopeDecision(
            allowed=True,
            principal=principal,
            requested_company_id=request.requested_company_id,
            resolved_company_id=None,
            reason="ok",
            checks=("tenant_scope_not_required",),
        )
        checks.append("tenant_scope_not_required")

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

    explicit_permissions = {
        str(permission).strip().lower()
        for permission in (request.required_permissions or ())
        if str(permission).strip()
    }
    explicit_permission_match = bool(
        explicit_permissions and explicit_permissions.issubset(set(principal.permissions))
    )

    if domain and domain in set(profile_contract.forbidden_domains) and not explicit_permission_match:
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
