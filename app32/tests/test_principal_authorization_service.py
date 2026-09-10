from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant
from services.principal_authorization_service import PrincipalAuthorizationService


NOW = datetime(2026, 9, 9, 12, 0, 0)


def _service(**kwargs) -> PrincipalAuthorizationService:
    return PrincipalAuthorizationService(now_provider=lambda: NOW, **kwargs)


def _principal(*, principal_id: int = 7, status: str = "active", revoked_at=None) -> IdentityPrincipal:
    return IdentityPrincipal(id=principal_id, subject_type="SERVICE", status=status, revoked_at=revoked_at)


def _grant(**overrides) -> PrincipalCompanyGrant:
    values = {
        "principal_id": 7,
        "company_id": 21,
        "role": "colaborador",
        "status": "active",
    }
    values.update(overrides)
    return PrincipalCompanyGrant(**values)


def test_evaluate_grant_allows_only_the_explicit_active_tenant_grant():
    decision = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(),
        company_id="21",
    )

    assert decision.allowed is True
    assert decision.company_id == 21
    assert decision.role == "colaborador"


def test_evaluate_grant_denies_company_fallback_and_cross_tenant_grant():
    missing_company = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(),
        company_id=None,
    )
    cross_tenant = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(company_id=22),
        company_id=21,
    )

    assert missing_company.allowed is False
    assert "company_id obrigatório" in missing_company.reason
    assert cross_tenant.allowed is False
    assert "não pertence à empresa solicitada" in cross_tenant.reason


def test_evaluate_grant_denies_inactive_principal_and_grant_lifecycle_states():
    inactive_principal = _service().evaluate_grant(
        principal=_principal(status="suspended"),
        grant=_grant(),
        company_id=21,
    )
    suspended_grant = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(status="suspended"),
        company_id=21,
    )
    revoked_grant = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(revoked_at=NOW),
        company_id=21,
    )
    expired_grant = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(expires_at=NOW - timedelta(seconds=1)),
        company_id=21,
    )
    future_grant = _service().evaluate_grant(
        principal=_principal(),
        grant=_grant(starts_at=NOW + timedelta(seconds=1)),
        company_id=21,
    )

    assert inactive_principal.allowed is False
    assert suspended_grant.allowed is False
    assert revoked_grant.allowed is False
    assert expired_grant.allowed is False
    assert future_grant.allowed is False
    assert "expirado" in expired_grant.reason
    assert "ainda não está vigente" in future_grant.reason


def test_evaluate_grant_denies_grant_from_other_principal():
    decision = _service().evaluate_grant(
        principal=_principal(principal_id=7),
        grant=_grant(principal_id=8),
        company_id=21,
    )

    assert decision.allowed is False
    assert "não pertence ao principal autenticado" in decision.reason


def test_external_identity_resolution_never_auto_links_unregistered_subject():
    lookup_calls = []

    def external_identity_lookup(issuer, subject):
        lookup_calls.append((issuer, subject))
        return None

    decision = _service(external_identity_lookup=external_identity_lookup).resolve_external_identity_for_company(
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="same-email-is-not-a-link",
        company_id=21,
    )

    assert decision.allowed is False
    assert decision.reason == "identidade externa não vinculada"
    assert lookup_calls == [("https://auth.gestaoversus.com.br/realms/versus", "same-email-is-not-a-link")]


def test_external_principal_resolution_returns_only_a_previously_linked_active_principal():
    external_identity = ExternalIdentity(
        principal_id=7,
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="service:erp-bomix",
    )
    service = _service(
        external_identity_lookup=lambda issuer, subject: external_identity,
        principal_lookup=lambda principal_id: _principal(principal_id=principal_id),
    )

    resolution = service.resolve_external_principal(
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="service:erp-bomix",
    )

    assert resolution.allowed is True
    assert resolution.principal_id == 7
    assert resolution.external_identity is external_identity


def test_external_principal_resolution_does_not_trim_or_casefold_persisted_identifiers():
    calls = []

    def external_identity_lookup(issuer, subject):
        calls.append((issuer, subject))
        return None

    resolution = _service(
        external_identity_lookup=external_identity_lookup,
    ).resolve_external_principal(
        issuer=" https://auth.gestaoversus.com.br/realms/versus ",
        subject=" service:erp-bomix ",
    )

    assert resolution.allowed is False
    assert resolution.reason == "identidade externa não vinculada"
    assert calls == [
        (" https://auth.gestaoversus.com.br/realms/versus ", " service:erp-bomix ")
    ]


def test_external_principal_resolution_denies_missing_unlinked_or_inactive_identity():
    missing = _service().resolve_external_principal(issuer="", subject="subject")
    unlinked = _service(external_identity_lookup=lambda issuer, subject: None).resolve_external_principal(
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="unknown",
    )
    inactive = _service(
        external_identity_lookup=lambda issuer, subject: SimpleNamespace(principal_id=7),
        principal_lookup=lambda principal_id: _principal(principal_id=principal_id, status="revoked"),
    ).resolve_external_principal(
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="revoked-service",
    )

    assert missing.allowed is False
    assert "obrigatórios" in missing.reason
    assert unlinked.allowed is False
    assert unlinked.reason == "identidade externa não vinculada"
    assert inactive.allowed is False
    assert "inativo" in inactive.reason


def test_external_identity_resolution_rechecks_the_principal_grant_for_requested_company():
    calls = []
    service = _service(
        external_identity_lookup=lambda issuer, subject: SimpleNamespace(principal_id=7),
        principal_lookup=lambda principal_id: _principal(principal_id=principal_id),
        grant_lookup=lambda principal_id, company_id: calls.append((principal_id, company_id)) or _grant(
            principal_id=principal_id,
            company_id=company_id,
        ),
    )

    decision = service.resolve_external_identity_for_company(
        issuer="https://auth.gestaoversus.com.br/realms/versus",
        subject="service:erp-bomix",
        company_id=21,
    )

    assert decision.allowed is True
    assert decision.role == "colaborador"
    assert calls == [(7, 21)]
