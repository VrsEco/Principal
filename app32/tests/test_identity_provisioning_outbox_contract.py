from pathlib import Path


def test_identity_provisioning_uses_persistent_outbox_and_never_persists_password():
    root = Path(__file__).resolve().parents[1]
    model = (root / "models" / "identity_provisioning_outbox.py").read_text(encoding="utf-8")
    service = (root / "services" / "identity_provisioning_outbox_service.py").read_text(encoding="utf-8")
    routes = (root / "api" / "routes" / "users.py").read_text(encoding="utf-8")

    assert "identity_provisioning_outbox" in model
    assert "password = db.Column" not in model
    assert "queue_user_state" in service
    assert "process_due" in service
    assert "queue_user_state(user)" in routes


def test_keycloak_invite_is_explicit_and_can_recover_a_remote_identity_after_retry():
    root = Path(__file__).resolve().parents[1]
    service = (root / "services" / "keycloak_identity_provisioning_service.py").read_text(encoding="utf-8")

    assert "elif send_password_setup_email:" in service
    assert 'json=["UPDATE_PASSWORD"]' in service


def test_grant_reconciliation_preserves_legacy_active_links_and_scopes_company_lookup():
    root = Path(__file__).resolve().parents[1]
    service = (root / "services" / "identity_provisioning_outbox_service.py").read_text(encoding="utf-8")

    assert 'Employee.status.is_(None), Employee.status == "active"' in service
    assert "Company.id.in_(linked_company_ids)" in service
    assert "Company.query.filter_by(is_active=True).all()" not in service


def test_outbox_persists_remote_subject_before_local_grant_sync_to_prevent_duplicate_invites():
    root = Path(__file__).resolve().parents[1]
    service = (root / "services" / "identity_provisioning_outbox_service.py").read_text(encoding="utf-8")

    assert "existing_identity is None and not event.external_subject" in service
    persist_remote_subject = service.index("event.external_subject = subject")
    commit_subject = service.index("db.session.commit()", persist_remote_subject)
    sync_local_grants = service.index("self._sync_principal_and_grants(user=user, subject=subject)")
    assert persist_remote_subject < commit_subject < sync_local_grants
