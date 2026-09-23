from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import oauth_connection_recovery_service as recovery


@pytest.fixture
def recovery_harness(monkeypatch):
    events = []
    user_model = MagicMock()
    user_model.query.get.return_value = SimpleNamespace(
        id=4, email="test@example.com", name="Test", is_active=True
    )
    audit_model = MagicMock()
    audit_model.created_at.__ge__.return_value = True
    audit_model.query.filter.return_value.count.return_value = 0
    audit_model.return_value.id = 73
    database = MagicMock()
    database.session.commit.side_effect = lambda: events.append("commit")
    provisioner = MagicMock()

    def ensure(**kwargs):
        assert kwargs["send_password_setup_email"] is False
        events.append("ensure")
        return "subject-test"

    provisioner.ensure_user.side_effect = ensure
    provisioner.send_password_setup_email.side_effect = lambda **kw: events.append("email")
    grants = MagicMock()
    grants.reconcile_user_identity_and_grants.side_effect = lambda **kw: events.append("grants") or [1]
    monkeypatch.setattr(recovery, "User", user_model)
    monkeypatch.setattr(recovery, "OAuthConnectionRecoveryAudit", audit_model)
    monkeypatch.setattr(recovery, "db", database)
    monkeypatch.setattr(recovery, "KeycloakIdentityProvisioningService", lambda: provisioner)
    monkeypatch.setattr(recovery, "identity_provisioning_outbox_service", grants)
    service = recovery.OAuthConnectionRecoveryService()
    monkeypatch.setattr(service, "_mark_failed", MagicMock())
    return service, events, provisioner, grants


def test_recovery_commits_validated_grants_before_sending_email(recovery_harness):
    service, events, provisioner, grants = recovery_harness
    result = service.recover_authenticated_user(user_id=4)
    assert result["success"] is True
    assert events == ["commit", "ensure", "grants", "commit", "email", "commit"]
    provisioner.send_password_setup_email.assert_called_once_with(subject="subject-test")
    assert grants.reconcile_user_identity_and_grants.call_args.kwargs["suspend_stale_grants"] is True


def test_recovery_does_not_email_when_identity_reconciliation_fails(recovery_harness):
    service, events, provisioner, grants = recovery_harness
    grants.reconcile_user_identity_and_grants.side_effect = recovery.KeycloakProvisioningError("identity collision")
    with pytest.raises(recovery.OAuthConnectionRecoveryError):
        service.recover_authenticated_user(user_id=4)
    provisioner.send_password_setup_email.assert_not_called()
    service._mark_failed.assert_called_once_with(73, "identity collision", "oauth_recovery_failed")


def test_unexpected_error_does_not_persist_credentials(recovery_harness):
    service, events, provisioner, grants = recovery_harness
    grants.reconcile_user_identity_and_grants.side_effect = RuntimeError('password=SECRET token=PRIVATE')
    with pytest.raises(recovery.OAuthConnectionRecoveryError):
        service.recover_authenticated_user(user_id=4)
    detail = service._mark_failed.call_args.args[1]
    assert 'SECRET' not in detail and 'PRIVATE' not in detail
    provisioner.send_password_setup_email.assert_not_called()
