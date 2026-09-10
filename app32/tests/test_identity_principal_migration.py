from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "20260909_1000_identity_principals_and_tenant_grants.py"
)


def test_identity_principal_migration_is_additive_and_uses_current_revision_chain():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260909_1000"' in source
    assert 'down_revision = "20260907_1900"' in source
    assert 'op.create_table(\n        "identity_principals"' in source
    assert 'op.create_table(\n        "external_identities"' in source
    assert 'op.create_table(\n        "principal_company_grants"' in source
    assert "op.alter_column" not in source
    assert "op.drop_column" not in source


def test_identity_principal_migration_enforces_tenant_grant_and_external_identity_uniqueness():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "uq_external_identity_issuer_subject" in source
    assert "responsible_user_id" in source
    assert "ck_identity_principal_subject_binding" in source
    assert "uq_principal_company_grant" in source
    assert "ck_principal_company_grant_validity" in source
    assert "ix_principal_company_grant_company_status" in source
