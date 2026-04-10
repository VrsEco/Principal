from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .tenant_rbac import PrincipalContext, resolve_identity_context, validate_company_id


@dataclass(frozen=True)
class RuntimeSecuritySnapshot:
    principal: PrincipalContext
    accessible_company_ids: tuple[int, ...]
    resolved_company_id: Optional[int]
    tenant_allowed: bool
    tenant_reason: str
    tenant_checks: tuple[str, ...]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "principal": {
                "user_id": self.principal.user_id,
                "company_id": self.principal.company_id,
                "employee_id": self.principal.employee_id,
                "role": self.principal.role,
                "channel": self.principal.channel,
                "thread_id": self.principal.thread_id,
                "permissions": sorted(self.principal.permissions),
            },
            "accessible_company_ids": list(self.accessible_company_ids),
            "resolved_company_id": self.resolved_company_id,
            "tenant_allowed": self.tenant_allowed,
            "tenant_reason": self.tenant_reason,
            "tenant_checks": list(self.tenant_checks),
        }


def build_runtime_security_snapshot(
    *,
    user_id: int,
    requested_company_id: Optional[int],
    channel: str = "web",
    thread_id: Optional[str] = None,
    role: Optional[str] = None,
    employee_id: Optional[int] = None,
    accessible_company_ids: Optional[Sequence[int]] = None,
    permissions: Optional[Sequence[str]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> RuntimeSecuritySnapshot:
    """
    Prepara um snapshot de segurança para o runtime oficial do Sapiens.

    Esta função é propositalmente pura para permitir testes sem banco.
    """
    normalized_companies = tuple(
        sorted(
            {
                int(company_id)
                for company_id in (accessible_company_ids or ())
                if company_id is not None
            }
        )
    )

    inferred_company_id = requested_company_id
    principal_company_id = None

    if requested_company_id is not None:
        if not normalized_companies or requested_company_id in normalized_companies:
            principal_company_id = requested_company_id
    elif len(normalized_companies) == 1:
        inferred_company_id = normalized_companies[0]
        principal_company_id = normalized_companies[0]

    principal = resolve_identity_context(
        {
            "user_id": user_id,
            "company_id": principal_company_id,
            "employee_id": employee_id,
            "role": role,
            "channel": channel,
            "thread_id": thread_id,
            "permissions": permissions,
            "metadata": dict(metadata or {}),
        }
    )

    tenant = validate_company_id(
        principal,
        inferred_company_id,
        accessible_company_ids=normalized_companies,
    )

    return RuntimeSecuritySnapshot(
        principal=principal,
        accessible_company_ids=normalized_companies,
        resolved_company_id=tenant.resolved_company_id,
        tenant_allowed=tenant.allowed,
        tenant_reason=tenant.reason,
        tenant_checks=tenant.checks,
    )
