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


def test_keycloak_invite_is_only_for_new_identity_and_profile_changes_do_not_reset_password():
    root = Path(__file__).resolve().parents[1]
    service = (root / "services" / "keycloak_identity_provisioning_service.py").read_text(encoding="utf-8")

    assert "elif send_password_setup_email and created" in service
    assert 'json=["UPDATE_PASSWORD"]' in service
