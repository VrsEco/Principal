import os
import sys
from datetime import datetime
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

    def revalidate(self, *, action, approver_user_id, approver_name, active_company_id):
        assert approver_user_id == 7
        assert approver_name == "Fabiano Ferreira"
        assert active_company_id == 9
        action.status = "pending"
        return SimpleNamespace(
            success=True,
            message="Solicitação revalidada com sucesso. O prazo de aprovação foi renovado.",
            action_status="pending",
            http_status=200,
            resume_payload={"action_key": "meeting.start"},
            resume_result={},
            audit_metadata={
                "workflow_approval": {
                    "event": "revalidated",
                    "action_id": action.id,
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


class _FakeApprovalQuery:
    def __init__(self, actions):
        self._actions = list(actions)
        self._status = None
        self._company_id = None
        self._type = None
        self._limit = None

    def filter_by(self, **kwargs):
        if 'company_id' in kwargs:
            self._company_id = kwargs['company_id']
        if 'type' in kwargs:
            self._type = kwargs['type']
        if 'status' in kwargs:
            self._status = kwargs['status']
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def all(self):
        items = [
            action for action in self._actions
            if (self._company_id is None or action.company_id == self._company_id)
            and (self._type is None or action.type == self._type)
            and (self._status is None or action.status == self._status)
        ]
        if self._limit is not None:
            items = items[: self._limit]
        return items


def test_list_workflow_approvals_returns_structured_payload(monkeypatch):
    app = _build_app()
    created_at = datetime(2026, 3, 8, 10, 15, 0)
    action_pending = _FakeAction()
    action_pending.created_at = created_at
    action_pending.resolved_at = None
    action_pending.executed_at = None
    action_pending.title = 'Aprovação necessária: o início da reunião R-55'
    action_pending.description = 'Fluxo sensível iniciado via WhatsApp.'
    action_pending.requesting_agent = 'sapiens'
    action_pending.handling_agent = 'operations'
    action_pending.payload = {
        'approval_key': 'meeting.start|3|9|R-55',
        'action_key': 'meeting.start',
        'channel': 'whatsapp',
        'object_code': 'R-55',
        'request_payload': {'codigo_reuniao': 'R-55'},
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'whatsapp'},
        'created_via': 'workflow_policy_guard',
    }

    action_executed = _FakeAction(action_id=92, status='executed')
    action_executed.created_at = created_at
    action_executed.resolved_at = created_at
    action_executed.executed_at = created_at
    action_executed.title = 'Aprovação necessária: a conclusão da atividade AA.J.31.190'
    action_executed.description = 'Fluxo sensível iniciado via Telegram.'
    action_executed.requesting_agent = 'sapiens'
    action_executed.handling_agent = 'operations'
    action_executed.payload = {
        'approval_key': 'project_task.complete|3|9|AA.J.31.190',
        'action_key': 'project_task.complete',
        'channel': 'telegram',
        'object_code': 'AA.J.31.190',
        'request_payload': {'codigo_atividade': 'AA.J.31.190'},
        'resume_payload': {'action_key': 'project_task.complete', 'channel': 'telegram'},
        'resume_result': {'executed': True},
        'approval_status': 'approved',
        'approved_by_user_id': 7,
        'approved_at': '2026-03-08T10:20:00',
        'created_via': 'workflow_policy_guard',
    }

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import models.agent_action as agent_action_module
    from services.workflow_approval_service import serialize_workflow_approval_action

    fake_agent_action_class = type(
        'FakeAgentAction',
        (),
        {
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeApprovalQuery([action_pending, action_executed]),
        },
    )
    monkeypatch.setattr(agent_action_module, 'AgentAction', fake_agent_action_class)

    with app.test_request_context('/api/agents/actions/workflow-approvals?status=all&channel=whatsapp&limit=20', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.list_workflow_approvals.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['count'] == 1
    assert body['filters'] == {
        'status': 'all',
        'action_key': None,
        'channel': 'whatsapp',
        'user_id': None,
        'limit': 20,
    }
    assert body['workflow_approvals'][0] == serialize_workflow_approval_action(action_pending)
    assert body['workflow_approvals'][0]['approval']['channel'] == 'whatsapp'
    assert body['workflow_approvals'][0]['approval']['action_key'] == 'meeting.start'


def test_list_workflow_approvals_blocks_unauthorized_role(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/actions/workflow-approvals', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.list_workflow_approvals.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False
    assert 'Sem permissão' in body['error']


def test_list_workflow_approvals_validates_limit(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    with app.test_request_context('/api/agents/actions/workflow-approvals?limit=abc', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.list_workflow_approvals.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert body['success'] is False
    assert 'limit inválido' in body['error']


def test_revalidate_action_returns_audit_metadata_and_logs_message(monkeypatch):
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

    with app.test_request_context("/api/agents/actions/revalidate/91", method="POST"):
        session["active_company_id"] = 9
        response, status_code = agents_route.revalidate_action.__wrapped__(91)

    body = response.get_json()
    assert status_code == 200
    assert body["success"] is True
    assert body["approval_metadata"]["workflow_approval"]["event"] == "revalidated"
    assert captured["metadata"] == body["approval_metadata"]
    assert fake_db_session.committed is True


def test_list_workflow_approvals_supports_expired_filter(monkeypatch):
    app = _build_app()
    created_at = datetime(2026, 3, 7, 10, 15, 0)
    expired_action = _FakeAction(action_id=93)
    expired_action.created_at = created_at
    expired_action.resolved_at = None
    expired_action.executed_at = None
    expired_action.title = 'Aprovação necessária: o início da reunião R-99'
    expired_action.description = 'Fluxo sensível expirado.'
    expired_action.requesting_agent = 'sapiens'
    expired_action.handling_agent = 'operations'
    expired_action.payload = {
        'approval_key': 'meeting.start|3|9|R-99',
        'approval_status': 'expired',
        'action_key': 'meeting.start',
        'channel': 'whatsapp',
        'object_code': 'R-99',
        'request_payload': {'codigo_reuniao': 'R-99'},
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'whatsapp'},
        'approval_expires_at': '2026-03-08T08:00:00',
        'expired_at': '2026-03-08T08:30:00',
        'created_via': 'workflow_policy_guard',
    }

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import models.agent_action as agent_action_module

    fake_agent_action_class = type(
        'FakeAgentAction',
        (),
        {
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeApprovalQuery([expired_action]),
        },
    )
    monkeypatch.setattr(agent_action_module, 'AgentAction', fake_agent_action_class)

    with app.test_request_context('/api/agents/actions/workflow-approvals?status=expired', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.list_workflow_approvals.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['count'] == 1
    assert body['workflow_approvals'][0]['approval']['expired'] is True
    assert body['workflow_approvals'][0]['approval']['approval_status'] == 'expired'


def test_workflow_approval_metrics_returns_aggregated_view(monkeypatch):
    app = _build_app()
    action_a = _FakeAction()
    action_a.created_at = datetime(2026, 3, 8, 10, 0, 0)
    action_a.payload = {
        'action_key': 'meeting.start',
        'channel': 'whatsapp',
        'approval_status': 'pending',
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'whatsapp'},
    }

    action_b = _FakeAction(action_id=92, status='executed')
    action_b.created_at = datetime(2026, 3, 8, 9, 0, 0)
    action_b.payload = {
        'action_key': 'project_task.complete',
        'channel': 'telegram',
        'approval_status': 'approved',
        'approved_by_user_id': 7,
        'resume_payload': {'action_key': 'project_task.complete', 'channel': 'telegram'},
        'resume_result': {'executed': True},
    }

    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    import models.agent_action as agent_action_module

    fake_agent_action_class = type(
        'FakeAgentAction',
        (),
        {
            'created_at': SimpleNamespace(desc=lambda: None),
            'query': _FakeApprovalQuery([action_a, action_b]),
        },
    )
    monkeypatch.setattr(agent_action_module, 'AgentAction', fake_agent_action_class)

    with app.test_request_context('/api/agents/actions/workflow-approvals/metrics?limit=150', method='GET'):
        session['active_company_id'] = 9
        response = agents_route.workflow_approval_metrics.__wrapped__()

    body = response.get_json()
    assert body['success'] is True
    assert body['limit'] == 150
    assert body['metrics']['total'] == 2
    assert body['metrics']['by_action_key']['meeting.start'] == 1
    assert body['metrics']['by_channel']['telegram'] == 1
    assert body['metrics']['by_approver_user_id']['7'] == 1


def test_workflow_approval_metrics_blocks_unauthorized_role(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=8, name='Colaborador', role='user'))

    with app.test_request_context('/api/agents/actions/workflow-approvals/metrics', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.workflow_approval_metrics.__wrapped__()

    body = response.get_json()
    assert status_code == 403
    assert body['success'] is False
    assert 'Sem permissão' in body['error']


def test_workflow_approval_metrics_validates_limit(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, 'current_user', SimpleNamespace(id=7, name='Fabiano Ferreira', role='admin'))

    with app.test_request_context('/api/agents/actions/workflow-approvals/metrics?limit=oops', method='GET'):
        session['active_company_id'] = 9
        response, status_code = agents_route.workflow_approval_metrics.__wrapped__()

    body = response.get_json()
    assert status_code == 400
    assert body['success'] is False
    assert 'limit inválido' in body['error']
