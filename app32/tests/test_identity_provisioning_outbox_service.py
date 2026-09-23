from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import identity_provisioning_outbox_service as outbox


@pytest.fixture
def harness(monkeypatch):
    event = SimpleNamespace(id=7, user_id=4, operation="disable_user", status="failed",
                            attempts=0, external_subject=None)
    user = SimpleNamespace(id=4, is_active=True, email="test@example.com", name="Test")
    event_model = MagicMock()
    event_model.query.get.return_value = event
    user_model = MagicMock()
    user_model.query.get.return_value = user
    principal_model = MagicMock()
    principal_model.query.filter_by.return_value.first.return_value = None
    provisioner = MagicMock()
    provisioner.ensure_user.return_value = "subject-test"
    provisioner.disable_user.return_value = "subject-test"
    monkeypatch.setattr(outbox, "IdentityProvisioningOutbox", event_model)
    monkeypatch.setattr(outbox, "User", user_model)
    monkeypatch.setattr(outbox, "IdentityPrincipal", principal_model)
    monkeypatch.setattr(outbox, "db", MagicMock())
    monkeypatch.setattr(outbox, "KeycloakIdentityProvisioningService", lambda: provisioner)
    service = outbox.IdentityProvisioningOutboxService()
    monkeypatch.setattr(service, "_sync_principal_and_grants", MagicMock())
    return service, event, user, provisioner


@pytest.mark.parametrize("active,old_operation", [(True, "disable_user"), (False, "upsert_user")])
def test_outbox_projects_current_user_state_not_stale_operation(harness, active, old_operation):
    service, event, user, provisioner = harness
    user.is_active = active
    event.operation = old_operation
    assert service.process_event(event.id)["success"] is True
    if active:
        provisioner.ensure_user.assert_called_once()
        assert provisioner.ensure_user.call_args.kwargs["enabled"] is True
        provisioner.disable_user.assert_not_called()
    else:
        provisioner.disable_user.assert_called_once_with(email=user.email, name=user.name)
        provisioner.ensure_user.assert_not_called()


def test_retry_after_remote_checkpoint_does_not_repeat_invite(harness):
    service, event, user, provisioner = harness
    service._sync_principal_and_grants.side_effect = [RuntimeError("local failure"), None]
    assert service.process_event(event.id)["success"] is False
    assert event.external_subject == "subject-test"
    assert service.process_event(event.id)["success"] is True
    assert [call.kwargs["send_password_setup_email"] for call in provisioner.ensure_user.call_args_list] == [True, False]


@pytest.mark.parametrize("status,reused", [("pending", True), ("failed", True),
                                        ("succeeded", False), ("processing", False)])
def test_queue_does_not_reuse_completed_or_running_projection(monkeypatch, status, reused):
    user = SimpleNamespace(id=4, email="test@example.com", name="Test", is_active=True, role="client")
    payload = {"email": user.email, "name": user.name, "is_active": True, "role": user.role}
    previous = SimpleNamespace(id=7, operation="upsert_user", status=status, payload=payload)
    model = MagicMock()
    model.query.filter_by.return_value.order_by.return_value.first.return_value = previous
    database = MagicMock()
    monkeypatch.setattr(outbox, "IdentityProvisioningOutbox", model)
    monkeypatch.setattr(outbox, "db", database)
    service = outbox.IdentityProvisioningOutboxService()
    result = service.queue_user_state(user)
    if reused:
        assert result is previous
        database.session.add.assert_not_called()
    else:
        assert result is model.return_value
        database.session.add.assert_called_once_with(result)
        assert model.call_args.kwargs["dedupe_key"] != service._dedupe_key(user, "upsert_user")


def test_projection_key_changes_when_same_state_returns_after_another_event():
    user = SimpleNamespace(id=4, email="test@example.com", name="Test", is_active=True, role="client")
    service = outbox.IdentityProvisioningOutboxService()
    assert service._dedupe_key(user, "upsert_user", 7) != service._dedupe_key(user, "upsert_user", 9)
