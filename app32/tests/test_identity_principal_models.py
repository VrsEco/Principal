from __future__ import annotations

from datetime import datetime, timedelta

from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant


def test_identity_principal_contract_keeps_human_and_technical_identities_distinct():
    human = IdentityPrincipal(subject_type="USER", user_id=7, status="active")
    service = IdentityPrincipal(
        subject_type="SERVICE", user_id=None, responsible_user_id=7, purpose="Integração ERP", status="active"
    )
    agent = IdentityPrincipal(
        subject_type="AGENT", user_id=None, responsible_user_id=7, purpose="Análise financeira", status="suspended"
    )

    assert human.user_id == 7
    assert service.user_id is None
    assert service.responsible_user_id == 7
    assert service.purpose == "Integração ERP"
    assert agent.user_id is None
    assert human.is_active is True
    assert service.is_active is True
    assert agent.is_active is False
    constraint_names = {constraint.name for constraint in IdentityPrincipal.__table__.constraints}

    assert "ck_identity_principal_subject_binding" in constraint_names


def test_external_identity_is_uniquely_bound_by_issuer_and_subject():
    constraint_names = {constraint.name for constraint in ExternalIdentity.__table__.constraints}

    assert "uq_external_identity_issuer_subject" in constraint_names
    assert not ExternalIdentity.__table__.c.issuer.foreign_keys
    assert ExternalIdentity.__table__.c.principal_id.nullable is False


def test_principal_company_grant_is_explicitly_tenant_scoped_and_expires():
    grant = PrincipalCompanyGrant(
        principal_id=10,
        company_id=21,
        status="active",
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    constraint_names = {constraint.name for constraint in PrincipalCompanyGrant.__table__.constraints}

    assert grant.company_id == 21
    assert grant.is_active is False
    assert "uq_principal_company_grant" in constraint_names
    assert "ck_principal_company_grant_validity" in constraint_names


def test_principal_company_grant_uses_one_lifecycle_evaluation_for_start_revoke_and_expiry():
    now = datetime(2026, 9, 9, 12, 0, 0)
    future = PrincipalCompanyGrant(status="active", starts_at=now + timedelta(seconds=1))
    revoked = PrincipalCompanyGrant(status="active", revoked_at=now)
    expired = PrincipalCompanyGrant(status="active", expires_at=now - timedelta(seconds=1))
    active = PrincipalCompanyGrant(status="active", starts_at=now, expires_at=now)

    assert future.inactive_reason_at(now) == "not_started"
    assert revoked.inactive_reason_at(now) == "inactive"
    assert expired.inactive_reason_at(now) == "expired"
    assert active.is_active_at(now) is True
