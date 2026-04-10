from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from src.intelligence.mcp_contracts import APP32_PROFILE_CONTRACTS_MANIFEST

ROLE_ALIASES = {
    "admin": "administrador",
    "administrator": "administrador",
    "administrador": "administrador",
    "admin_tecnico": "administrador_tecnico",
    "technical_admin": "administrador_tecnico",
    "tech_admin": "administrador_tecnico",
    "collaborator": "colaborador",
    "colaborador": "colaborador",
    "client": "cliente",
    "cliente": "cliente",
}

ADMIN_ROLES = {"administrador", "administrador_tecnico"}
READ_ACTIONS = {"discover", "read", "list", "search", "analyze", "audit", "export"}
WRITE_ACTIONS = {"create", "update", "delete", "approve", "execute"}
ACTION_ALIASES = {
    "list": "read",
    "search": "discover",
    "export": "read",
    "approve": "update",
}
DOMAIN_MATRIX = {
    "routine": {
        "colaborador": READ_ACTIONS | {"create", "update"},
        "cliente": {"discover", "read", "list", "search"},
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "projects": {
        "colaborador": READ_ACTIONS | {"create", "update"},
        "cliente": {"discover", "read", "list", "search"},
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "meetings": {
        "colaborador": READ_ACTIONS | {"create", "update"},
        "cliente": {"discover", "read", "list", "search"},
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "strategy": {
        "colaborador": {"discover", "read", "list", "search", "analyze"},
        "cliente": {"discover", "read", "list", "search", "analyze"},
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "finance": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "governance": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "analytics": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": {"discover", "read", "list", "search", "analyze"},
        "administrador_tecnico": {"discover", "read", "list", "search", "analyze"},
    },
    "workload": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": {"discover", "read", "list", "search", "analyze"},
        "administrador_tecnico": {"discover", "read", "list", "search", "analyze", "audit"},
    },
    "identity_self_service": {
        "colaborador": {"discover", "read", "list", "search", "update"},
        "cliente": {"discover", "read", "list", "search", "update"},
        "administrador": {"discover", "read", "list", "search", "update"},
        "administrador_tecnico": {"discover", "read", "list", "search", "update"},
    },
    "identity_admin": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "operations": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": set(),
        "administrador_tecnico": {"discover", "read", "list", "search", "create", "update", "audit"},
    },
    "admin": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": READ_ACTIONS | WRITE_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | WRITE_ACTIONS,
    },
    "diagnostics": {
        "colaborador": set(),
        "cliente": set(),
        "administrador": READ_ACTIONS,
        "administrador_tecnico": READ_ACTIONS | {"create", "update"},
    },
}


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_role(role: Any) -> str:
    normalized = _normalize_text(role).lower()
    if not normalized:
        return "colaborador"
    return ROLE_ALIASES.get(normalized, normalized)


def _extract_value(source: Any, key: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def _normalize_permissions(permissions: Any) -> frozenset[str]:
    if permissions is None:
        return frozenset()
    if isinstance(permissions, str):
        raw_items: Iterable[Any] = [item.strip() for item in permissions.split(",")]
    elif isinstance(permissions, Iterable):
        raw_items = permissions
    else:
        raw_items = [permissions]

    normalized = {_normalize_text(item).lower() for item in raw_items if _normalize_text(item)}
    return frozenset(normalized)


def _normalize_action(action: Any) -> Optional[str]:
    normalized = _normalize_text(action).lower()
    if not normalized:
        return None
    return ACTION_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class PrincipalContext:
    user_id: Optional[int] = None
    company_id: Optional[int] = None
    employee_id: Optional[int] = None
    role: str = "colaborador"
    channel: str = "web"
    thread_id: Optional[str] = None
    permissions: frozenset[str] = field(default_factory=frozenset)
    metadata: Optional[Mapping[str, Any]] = None

    def is_admin(self) -> bool:
        return _normalize_role(self.role) in ADMIN_ROLES


@dataclass(frozen=True)
class TenantScopeDecision:
    allowed: bool
    principal: PrincipalContext
    requested_company_id: Optional[int]
    resolved_company_id: Optional[int]
    reason: str
    checks: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    principal: PrincipalContext
    domain: Optional[str]
    action: Optional[str]
    reason: str
    checks: Tuple[str, ...] = ()


@dataclass(frozen=True)
class EnforcementPlan:
    principal: PrincipalContext
    tenant: TenantScopeDecision
    permission: PermissionDecision
    required_permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def allowed(self) -> bool:
        return self.tenant.allowed and self.permission.allowed

    @property
    def reason(self) -> str:
        if self.allowed:
            return "ok"
        if not self.tenant.allowed:
            return self.tenant.reason
        return self.permission.reason


class TenantScopeError(ValueError):
    def __init__(self, decision: TenantScopeDecision):
        super().__init__(decision.reason)
        self.decision = decision


class PermissionDeniedError(PermissionError):
    def __init__(self, decision: PermissionDecision):
        super().__init__(decision.reason)
        self.decision = decision


def resolve_identity_context(source: Any = None, **overrides: Any) -> PrincipalContext:
    """
    Normaliza a identidade da IA/MCP sem depender de Flask, banco ou services.

    Aceita mapping, objeto com atributos ou valores diretos por keyword.
    """
    candidate = source
    if isinstance(source, PrincipalContext):
        candidate = source

    user_id = _coerce_optional_int(overrides.get("user_id", _extract_value(candidate, "user_id")))
    company_id = _coerce_optional_int(overrides.get("company_id", _extract_value(candidate, "company_id")))
    employee_id = _coerce_optional_int(overrides.get("employee_id", _extract_value(candidate, "employee_id")))
    role = _normalize_role(overrides.get("role", _extract_value(candidate, "role")))
    channel = _normalize_text(overrides.get("channel", _extract_value(candidate, "channel"))) or "web"
    thread_id = _normalize_text(overrides.get("thread_id", _extract_value(candidate, "thread_id"))) or None

    permissions = overrides.get("permissions", _extract_value(candidate, "permissions"))
    metadata = overrides.get("metadata", _extract_value(candidate, "metadata"))

    return PrincipalContext(
        user_id=user_id,
        company_id=company_id,
        employee_id=employee_id,
        role=role,
        channel=channel,
        thread_id=thread_id,
        permissions=_normalize_permissions(permissions),
        metadata=metadata,
    )


def validate_company_id(
    principal: PrincipalContext,
    requested_company_id: Any,
    *,
    accessible_company_ids: Optional[Sequence[Any]] = None,
) -> TenantScopeDecision:
    requested = _coerce_optional_int(requested_company_id)
    principal_company_id = _coerce_optional_int(principal.company_id)
    accessible_ids = {
        company_id
        for company_id in (_coerce_optional_int(item) for item in (accessible_company_ids or ()))
        if company_id is not None
    }

    checks = ["coerce_requested_company_id", "coerce_principal_company_id"]

    if requested is None:
        if principal_company_id is not None:
            return TenantScopeDecision(
                allowed=True,
                principal=principal,
                requested_company_id=None,
                resolved_company_id=principal_company_id,
                reason="ok",
                checks=(*checks, "fallback_to_principal_company_id"),
            )
        return TenantScopeDecision(
            allowed=False,
            principal=principal,
            requested_company_id=None,
            resolved_company_id=None,
            reason="company_id ausente e sem contexto de tenant para resolução",
            checks=(*checks, "missing_company_context"),
        )

    if principal_company_id is not None and requested == principal_company_id:
        return TenantScopeDecision(
            allowed=True,
            principal=principal,
            requested_company_id=requested,
            resolved_company_id=requested,
            reason="ok",
            checks=(*checks, "requested_matches_principal"),
        )

    if principal.is_admin() and requested in accessible_ids:
        return TenantScopeDecision(
            allowed=True,
            principal=principal,
            requested_company_id=requested,
            resolved_company_id=requested,
            reason="ok",
            checks=(*checks, "admin_accessible_company_match"),
        )

    if principal.is_admin() and not accessible_ids and principal_company_id is None:
        return TenantScopeDecision(
            allowed=False,
            principal=principal,
            requested_company_id=requested,
            resolved_company_id=None,
            reason="admin sem company_id base ou lista de empresas acessíveis para validar o escopo",
            checks=(*checks, "admin_without_company_catalog"),
        )

    if requested in accessible_ids:
        return TenantScopeDecision(
            allowed=True,
            principal=principal,
            requested_company_id=requested,
            resolved_company_id=requested,
            reason="ok",
            checks=(*checks, "requested_in_accessible_companies"),
        )

    return TenantScopeDecision(
        allowed=False,
        principal=principal,
        requested_company_id=requested,
        resolved_company_id=principal_company_id,
        reason="company_id solicitado não pertence ao escopo do principal",
        checks=(*checks, "requested_company_mismatch"),
    )


def validate_permission(
    principal: PrincipalContext,
    *,
    domain: Optional[str] = None,
    action: Optional[str] = None,
    required_permissions: Optional[Sequence[str]] = None,
) -> PermissionDecision:
    normalized_domain = _normalize_text(domain).lower() or None
    normalized_action = _normalize_action(action)
    normalized_role = _normalize_role(principal.role)
    required = {perm.lower() for perm in (required_permissions or ()) if _normalize_text(perm)}
    checks = ["normalize_domain", "normalize_action"]
    profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(normalized_role)

    if profile_contract is not None and normalized_domain in set(profile_contract.forbidden_domains):
        return PermissionDecision(
            allowed=False,
            principal=principal,
            domain=normalized_domain,
            action=normalized_action,
            reason=f"domínio '{normalized_domain}' não permitido para o perfil '{profile_contract.profile}'",
            checks=(*checks, "domain_forbidden_by_profile_contract"),
        )

    if required and required.issubset(principal.permissions):
        return PermissionDecision(
            allowed=True,
            principal=principal,
            domain=normalized_domain,
            action=normalized_action,
            reason="ok",
            checks=(*checks, "explicit_permissions_match"),
        )

    if normalized_domain is None:
        allowed = principal.is_admin() or bool(required and required.issubset(principal.permissions))
        reason = "ok" if allowed else "domínio ausente e permissões insuficientes"
        return PermissionDecision(
            allowed=allowed,
            principal=principal,
            domain=None,
            action=normalized_action,
            reason=reason,
            checks=(*checks, "domain_missing"),
        )

    domain_rules = DOMAIN_MATRIX.get(normalized_domain)
    if domain_rules is None:
        return PermissionDecision(
            allowed=False,
            principal=principal,
            domain=normalized_domain,
            action=normalized_action,
            reason=f"domínio '{normalized_domain}' não suportado para o role atual",
            checks=(*checks, "unknown_domain_rejected"),
        )

    allowed_actions = domain_rules.get(normalized_role, set())
    if normalized_action is None:
        allowed = bool(allowed_actions) or principal.is_admin()
        reason = "ok" if allowed else f"role '{normalized_role}' sem acesso ao domínio '{normalized_domain}'"
        return PermissionDecision(
            allowed=allowed,
            principal=principal,
            domain=normalized_domain,
            action=None,
            reason=reason,
            checks=(*checks, "action_missing"),
        )

    if normalized_action in allowed_actions:
        return PermissionDecision(
            allowed=True,
            principal=principal,
            domain=normalized_domain,
            action=normalized_action,
            reason="ok",
            checks=(*checks, "action_in_role_matrix"),
        )

    if principal.is_admin():
        return PermissionDecision(
            allowed=True,
            principal=principal,
            domain=normalized_domain,
            action=normalized_action,
            reason="ok",
            checks=(*checks, "admin_override"),
        )

    return PermissionDecision(
        allowed=False,
        principal=principal,
        domain=normalized_domain,
        action=normalized_action,
        reason=f"role '{normalized_role}' sem permissão para '{normalized_action}' em '{normalized_domain}'",
        checks=(*checks, "action_not_allowed"),
    )


def prepare_enforcement(
    source: Any = None,
    *,
    requested_company_id: Any = None,
    domain: Optional[str] = None,
    action: Optional[str] = None,
    accessible_company_ids: Optional[Sequence[Any]] = None,
    required_permissions: Optional[Sequence[str]] = None,
    **identity_overrides: Any,
) -> EnforcementPlan:
    principal = resolve_identity_context(source, **identity_overrides)
    tenant = validate_company_id(
        principal,
        requested_company_id,
        accessible_company_ids=accessible_company_ids,
    )
    permission = validate_permission(
        principal,
        domain=domain,
        action=action,
        required_permissions=required_permissions,
    )
    return EnforcementPlan(
        principal=principal,
        tenant=tenant,
        permission=permission,
        required_permissions=_normalize_permissions(required_permissions),
    )


def require_company_scope(
    source: Any = None,
    *,
    requested_company_id: Any = None,
    accessible_company_ids: Optional[Sequence[Any]] = None,
    raise_on_deny: bool = True,
    **identity_overrides: Any,
) -> TenantScopeDecision:
    decision = validate_company_id(
        resolve_identity_context(source, **identity_overrides),
        requested_company_id,
        accessible_company_ids=accessible_company_ids,
    )
    if raise_on_deny and not decision.allowed:
        raise TenantScopeError(decision)
    return decision


def require_permission(
    source: Any = None,
    *,
    domain: Optional[str] = None,
    action: Optional[str] = None,
    required_permissions: Optional[Sequence[str]] = None,
    raise_on_deny: bool = True,
    **identity_overrides: Any,
) -> PermissionDecision:
    decision = validate_permission(
        resolve_identity_context(source, **identity_overrides),
        domain=domain,
        action=action,
        required_permissions=required_permissions,
    )
    if raise_on_deny and not decision.allowed:
        raise PermissionDeniedError(decision)
    return decision
