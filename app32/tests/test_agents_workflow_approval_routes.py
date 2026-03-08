import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import agents as agents_route


class _FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def add(self, _obj):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _FakeAction:
    def __init__(self, *, action_id=91, action_type="workflow_approval_request", company_id=9, status="pending"):
        self.id = action_id
        self.type = action_type
        self.company_id = company_id
        self.user_id = 3
        self.status = status
        self.payload = {
            "resume_payload": {
                "action_key": "meeting.start",
                "thread_id": "wa_3_sapiens",
                "channel": "whatsapp",
            }
        }

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "company_id": self.company_id,
            "payload": self.payload,
        }


class _FakeWorkflowApprovalService:
    def __init__(self, *, resume_executor):
        self.resume_executor = resume_executor

    def approve(self, *, action, approver_user_id, approver_name, active_company_id):
        assert approver_user_id == 7
        assert approver_name == "Fabiano Ferreira"
        assert active_company_id == 9
        action.status = "executed"
        return SimpleNamespace(
            success=True,
            message="Solicitação aprovada e executada.",
            action_status="executed",
            http_status=200,
            resume_payload={"action_key": "meeting.start"},
            resume_result={"executed": True, "response_text": "ok"},
            audit_metadata={
                "workflow_approval": {
                    "event": "approved_and_executed",
                    "action_id": action.id,
                }
            },
        )

    def reject(self, *, action, approver_user_id, approver_name, active_company_id, feedback=None):
        assert approver_user_id == 7
        assert approver_name == "Fabiano Ferreira"
        assert active_company_id == 9
        assert feedback == "Segurar até validarmos com o cliente."
        action.status = "rejected"
        return SimpleNamespace(
            success=True,
            message="Solicitação rejeitada.",
            action_status="rejected",
            http_status=200,
            resume_payload={"action_key": "meeting.start"},
            resume_result={},
            audit_metadata={
                "workflow_approval": {
                    "event": "rejected",
                    "action_id": action.id,
                    "feedback": feedback,
                }
            },
        )


def _build_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_approve_action_returns_audit_metadata_and_logs_message(monkeypatch):
    app = _build_app()
    fake_action = _FakeAction()
    fake_db_session = _FakeSession()
    captured = {}

    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, name="Fabiano Ferreira", role="admin"))
    monkeypatch.setattr(agents_route, "_log_workflow_approval_message", lambda action, message, metadata: captured.update({"action": action, "message": message, "metadata": metadata}))

    import models
    import models.agent_action as agent_action_module
    import services.workflow_approval_service as workflow_approval_module
    import src.intelligence.menu_engine as menu_engine_module

    monkeypatch.setattr(models, "db", SimpleNamespace(session=fake_db_session))
    fake_agent_action_class = type("FakeAgentAction", (), {"query": SimpleNamespace(get=lambda action_id: fake_action)})
    monkeypatch.setattr(agent_action_module, "AgentAction", fake_agent_action_class)
    monkeypatch.setattr(workflow_approval_module, "WorkflowApprovalService", _FakeWorkflowApprovalService)
    monkeypatch.setattr(menu_engine_module, "execute_approved_resume_payload", lambda payload: None)

    with app.test_request_context("/api/agents/actions/approve/91", method="POST"):
        session["active_company_id"] = 9
        response, status_code = agents_route.approve_action.__wrapped__(91)

    body = response.get_json()
    assert status_code == 200
    assert body["success"] is True
    assert body["approval_metadata"]["workflow_approval"]["event"] == "approved_and_executed"
    assert body["resume_result"]["executed"] is True
    assert captured["message"] == "Solicitação aprovada e executada."
    assert captured["metadata"] == body["approval_metadata"]
    assert fake_db_session.committed is True
    assert fake_db_session.rolled_back is False


def test_reject_action_returns_audit_metadata_and_logs_message(monkeypatch):
    app = _build_app()
    fake_action = _FakeAction()
    fake_db_session = _FakeSession()
    captured = {}

    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, name="Fabiano Ferreira", role="admin"))
    monkeypatch.setattr(agents_route, "_log_workflow_approval_message", lambda action, message, metadata: captured.update({"action": action, "message": message, "metadata": metadata}))

    import models
    import models.agent_action as agent_action_module
    import services.workflow_approval_service as workflow_approval_module
    import src.intelligence.menu_engine as menu_engine_module

    monkeypatch.setattr(models, "db", SimpleNamespace(session=fake_db_session))
    fake_agent_action_class = type("FakeAgentAction", (), {"query": SimpleNamespace(get=lambda action_id: fake_action)})
    monkeypatch.setattr(agent_action_module, "AgentAction", fake_agent_action_class)
    monkeypatch.setattr(workflow_approval_module, "WorkflowApprovalService", _FakeWorkflowApprovalService)
    monkeypatch.setattr(menu_engine_module, "execute_approved_resume_payload", lambda payload: None)

    with app.test_request_context(
        "/api/agents/actions/reject/91",
        method="POST",
        json={"feedback": "Segurar até validarmos com o cliente."},
    ):
        session["active_company_id"] = 9
        response, status_code = agents_route.reject_action.__wrapped__(91)

    body = response.get_json()
    assert status_code == 200
    assert body["success"] is True
    assert body["approval_metadata"]["workflow_approval"]["event"] == "rejected"
    assert body["approval_metadata"]["workflow_approval"]["feedback"] == "Segurar até validarmos com o cliente."
    assert captured["message"] == "Solicitação rejeitada."
    assert captured["metadata"] == body["approval_metadata"]
    assert fake_db_session.committed is True
    assert fake_db_session.rolled_back is False


def test_reject_action_blocks_non_workflow_action(monkeypatch):
    app = _build_app()
    fake_action = _FakeAction(action_type="technical_fix")

    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, name="Fabiano Ferreira", role="admin"))

    import models.agent_action as agent_action_module

    fake_agent_action_class = type("FakeAgentAction", (), {"query": SimpleNamespace(get=lambda action_id: fake_action)})
    monkeypatch.setattr(agent_action_module, "AgentAction", fake_agent_action_class)

    with app.test_request_context("/api/agents/actions/reject/91", method="POST", json={}):
        session["active_company_id"] = 9
        response, status_code = agents_route.reject_action.__wrapped__(91)

    body = response.get_json()
    assert status_code == 400
    assert body["success"] is False
    assert "não suporta rejeição operacional" in body["error"]
