import os
import sys
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.backlog_human_gate_service as backlog_human_gate_service
from api.resources import project_task as project_task_resource
from api.resources import project_task_operational as project_task_operational_resource
from services.backlog_human_gate_service import BacklogHumanGateOutcome


def _build_workflow_action(**overrides):
    payload = {
        "approval_status": "pending",
        "action_key": "project_task.complete",
        "object_code": "AA.J.31.270",
        "resume_payload": {"action_key": "project_task.complete", "channel": "whatsapp"},
    }
    data = {
        "id": 25,
        "type": "workflow_approval_request",
        "status": "pending",
        "title": "Aprovação necessária: concluir atividade",
        "description": "Solicitação sensível aberta via canal operacional.",
        "company_id": 1,
        "user_id": 7,
        "requesting_agent": "work_agent_squad",
        "handling_agent": "operations",
        "payload": payload,
        "created_at": None,
        "resolved_at": None,
        "executed_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _build_backlog_task(**overrides):
    data = {
        "id": 270,
        "project_id": 31,
        "code": "AA.J.31.270",
        "what": "[HITL][Workflow] Aprovação necessária: concluir atividade",
        "who": "Operação",
        "employee_id": None,
        "due_date": None,
        "completion_date": None,
        "how": None,
        "amount": None,
        "status": "planned",
        "stage": "waiting",
        "priority": "high",
        "employee_name": "Operação",
        "project_name": "Backlog AA.J.31",
        "notes": "",
        "score_weight": 1.0,
        "estimated_hours": 0.0,
        "worked_hours": 0.0,
        "logs": [],
        "created_at": None,
        "updated_at": None,
        "project": SimpleNamespace(company_id=9),
        "agent_action_backlog_link": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_backlog_human_gate_context_exposes_available_workflow_operations():
    action = _build_workflow_action()
    link = SimpleNamespace(
        project_task_id=270,
        backlog_project_code="AA.J.31",
        link_type="workflow_approval_request",
        action=action,
    )
    task = _build_backlog_task(agent_action_backlog_link=link)
    link.task = task

    context = backlog_human_gate_service.build_backlog_human_gate_context(task)

    assert context is not None
    assert context["enabled"] is True
    assert context["agent_action_id"] == 25
    assert context["effective_status"] == "pending"
    assert [item["id"] for item in context["available_operations"]] == [
        "approve",
        "reject",
        "revalidate",
    ]


def test_build_backlog_human_gate_context_exposes_timeline_from_task_logs():
    action = _build_workflow_action()
    task = _build_backlog_task(
        logs=[
            {
                "timestamp": "2026-03-20T10:00:00Z",
                "author": "Sistema",
                "type": "agent_action_sync",
                "summary": "Card sincronizado com AgentAction.",
                "action_status": "pending",
                "approval_status": "pending",
            },
            {
                "timestamp": "2026-03-20T11:00:00Z",
                "author": "Fabiano Ferreira",
                "type": "backlog_human_gate_operation",
                "operation": "approve",
                "operation_label": "Aprovação",
                "summary": "Solicitação aprovada e executada.",
                "message": "Solicitação aprovada e executada.",
                "success": True,
                "status_before": "pending",
                "status_after": "executed",
                "details": {"audit_metadata": {"source": "test"}},
            },
        ]
    )
    link = SimpleNamespace(
        project_task_id=270,
        backlog_project_code="AA.J.31",
        link_type="workflow_approval_request",
        action=action,
        task=task,
    )
    task.agent_action_backlog_link = link

    context = backlog_human_gate_service.build_backlog_human_gate_context(task)

    assert context is not None
    assert context["last_event"]["type"] == "backlog_human_gate_operation"
    assert context["last_event"]["label"] == "Aprovação"
    assert [entry["type"] for entry in context["timeline"]] == [
        "backlog_human_gate_operation",
        "agent_action_sync",
    ]
    assert context["timeline"][0]["status_after"] == "executed"
    assert context["timeline"][1]["status_after"] == "pending"


def test_build_backlog_human_gate_context_exposes_operational_health_badges():
    action = _build_workflow_action(
        created_at=datetime.utcnow() - timedelta(hours=52),
        payload={
            "approval_status": "expired",
            "action_key": "project_task.complete",
            "object_code": "AA.J.31.271",
            "resume_payload": {"action_key": "project_task.complete"},
        },
    )
    task = _build_backlog_task(
        logs=[
            {
                "timestamp": "2026-03-21T08:00:00Z",
                "author": "Sistema",
                "type": "agent_action_sync",
                "summary": "Card sincronizado com AgentAction.",
                "action_status": "pending",
                "approval_status": "expired",
            }
        ]
    )
    link = SimpleNamespace(
        project_task_id=271,
        backlog_project_code="AA.J.31",
        link_type="workflow_approval_request",
        action=action,
        task=task,
    )
    task.agent_action_backlog_link = link

    context = backlog_human_gate_service.build_backlog_human_gate_context(task)

    assert context is not None
    health = context["operational_health"]
    assert health["sla"]["tone"] == "danger"
    assert health["requires_attention"] is True
    assert health["requires_reprocess"] is True
    assert any(badge["id"] == "reprocess" for badge in health["badges"])


def test_execute_backlog_human_gate_operation_applies_legacy_deadline_extension(monkeypatch):
    target_task = SimpleNamespace(
        id=205,
        due_date=date(2026, 3, 25),
        logs=[],
        project=SimpleNamespace(company_id=9),
    )
    action = SimpleNamespace(
        id=88,
        type="approval_request",
        status="pending",
        company_id=9,
        user_id=3,
        title="Solicitação de Adiamento: Fechar contrato",
        description="Solicitação legada de adiamento.",
        requesting_agent="sapiens",
        handling_agent="operations",
        payload={
            "task_type": "project_task",
            "task_id": 205,
            "new_deadline": "2026-04-15",
            "reason": "Cliente pediu mais prazo",
            "requester": "Analista",
        },
        resolved_at=None,
        executed_at=None,
        user_feedback=None,
    )
    task = _build_backlog_task(id=310, code="AA.J.31.310")
    link = SimpleNamespace(
        backlog_project_code="AA.J.31",
        link_type="approval_request",
        action=action,
    )

    fake_project_task_class = type(
        "FakeProjectTask",
        (),
        {"query": SimpleNamespace(get=lambda task_id: target_task if int(task_id) == 205 else None)},
    )
    monkeypatch.setattr(backlog_human_gate_service, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(backlog_human_gate_service, "find_backlog_link_by_task_id", lambda task_id: link)
    monkeypatch.setattr(backlog_human_gate_service, "sync_backlog_task_for_action", lambda action: None)
    monkeypatch.setattr(backlog_human_gate_service.db.session, "commit", lambda: None)

    outcome = backlog_human_gate_service.execute_backlog_human_gate_operation(
        task=task,
        operation="approve",
        actor_user_id=7,
        actor_name="Fabiano Ferreira",
    )

    assert outcome.success is True
    assert outcome.message == "Solicitação de prazo aprovada e aplicada com sucesso."
    assert action.status == "executed"
    assert action.payload["approval_status"] == "approved"
    assert action.payload["approved_by_user_id"] == 7
    assert target_task.due_date == date(2026, 4, 15)
    assert target_task.logs[-1]["details"]["new_due_date"] == "2026-04-15"
    assert task.logs[-1]["type"] == "backlog_human_gate_operation"
    assert task.logs[-1]["operation"] == "approve"
    assert task.logs[-1]["status_before"] == "pending"
    assert task.logs[-1]["status_after"] == "executed"


def test_project_task_resource_get_includes_backlog_human_gate(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    task = _build_backlog_task()

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

    fake_project_task_class = type("FakeProjectTask", (), {"query": _FakeQuery()})
    monkeypatch.setattr(project_task_resource, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(project_task_resource, "apply_task_employee_filter", lambda query, company_id: query)
    monkeypatch.setattr(
        project_task_resource,
        "project_task_schema",
        SimpleNamespace(dump=lambda obj: {"id": obj.id, "code": obj.code, "project_id": obj.project_id}),
    )
    monkeypatch.setattr(
        backlog_human_gate_service,
        "build_backlog_human_gate_context",
        lambda obj: {"enabled": True, "agent_action_id": 25, "available_operations": [{"id": "approve"}]},
    )

    with app.test_request_context("/api/projects/31/tasks/270", method="GET"):
        session["active_company_id"] = 9
        response, status_code = project_task_resource.ProjectTaskResource().get.__wrapped__(
            project_task_resource.ProjectTaskResource(),
            31,
            270,
        )

    assert status_code == 200
    assert response["backlog_human_gate"]["enabled"] is True
    assert response["backlog_human_gate"]["agent_action_id"] == 25


def test_project_task_backlog_action_resource_returns_updated_card(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    task = _build_backlog_task()
    fake_action = _build_workflow_action(status="executed")

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

    fake_project_task_class = type("FakeProjectTask", (), {"query": _FakeQuery()})
    monkeypatch.setattr(project_task_operational_resource, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(project_task_operational_resource, "apply_task_employee_filter", lambda query, company_id: query)
    monkeypatch.setattr(project_task_operational_resource, "get_request_company_id", lambda: 9)
    monkeypatch.setattr(project_task_operational_resource, "has_company_full_access", lambda company_id: True)
    monkeypatch.setattr(
        project_task_operational_resource,
        "execute_backlog_human_gate_operation",
        lambda **kwargs: BacklogHumanGateOutcome(
            success=True,
            message="Solicitação aprovada e executada.",
            http_status=200,
            action=fake_action,
            resume_result={"executed": True},
            audit_metadata={"workflow_approval": {"event": "approved_and_executed"}},
        ),
    )
    monkeypatch.setattr(
        project_task_operational_resource,
        "build_backlog_human_gate_context",
        lambda obj: {"enabled": True, "agent_action_id": fake_action.id, "available_operations": []},
    )
    monkeypatch.setattr(
        project_task_operational_resource,
        "serialize_linked_agent_action",
        lambda action: {"id": action.id, "type": action.type, "status": action.status},
    )
    monkeypatch.setattr(
        project_task_operational_resource,
        "project_task_schema",
        SimpleNamespace(dump=lambda obj: {"id": obj.id, "code": obj.code, "project_id": obj.project_id}),
    )
    monkeypatch.setattr(
        project_task_operational_resource,
        "current_user",
        SimpleNamespace(id=7, name="Fabiano Ferreira", role="admin"),
    )

    with app.test_request_context(
        "/api/projects/31/tasks/270/backlog-actions/approve",
        method="POST",
        json={},
    ):
        session["active_company_id"] = 9
        response, status_code = project_task_operational_resource.ProjectTaskBacklogActionResource().post.__wrapped__(
            project_task_operational_resource.ProjectTaskBacklogActionResource(),
            31,
            270,
            "approve",
        )

    body = response
    assert status_code == 200
    assert body["success"] is True
    assert body["message"] == "Solicitação aprovada e executada."
    assert body["task"]["backlog_human_gate"]["agent_action_id"] == 25
    assert body["action"]["status"] == "executed"



def test_project_task_resource_put_blocks_manual_edit_on_human_gate_card(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    task = _build_backlog_task(
        agent_action_backlog_link=SimpleNamespace(
            project_task_id=270,
            backlog_project_code="AA.J.31",
            link_type="workflow_approval_request",
        )
    )

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

    fake_project_task_class = type("FakeProjectTask", (), {"query": _FakeQuery()})
    monkeypatch.setattr(project_task_resource, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(project_task_resource, "apply_task_employee_filter", lambda query, company_id: query)
    monkeypatch.setattr(project_task_resource, "_user_can_update_task", lambda company_id, project_id, task_id: True)
    monkeypatch.setattr(project_task_resource, "has_permission", lambda company_id, module, action: True)
    monkeypatch.setattr(project_task_resource, "project_task_schema", SimpleNamespace(load=lambda data, instance=None, partial=False: instance))
    monkeypatch.setattr(project_task_resource.db.session, "commit", lambda: None)
    monkeypatch.setattr(project_task_resource.db.session, "rollback", lambda: None)

    with app.test_request_context(
        "/api/projects/31/tasks/270",
        method="PUT",
        json={"what": "Tentativa manual"},
    ):
        session["active_company_id"] = 9
        response, status_code = project_task_resource.ProjectTaskResource().put.__wrapped__(
            project_task_resource.ProjectTaskResource(),
            31,
            270,
        )

    assert status_code == 409
    assert "fila HITL" in response["error"]


def test_project_task_stage_resource_patch_blocks_manual_move_on_human_gate_card(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    task = _build_backlog_task(
        agent_action_backlog_link=SimpleNamespace(
            project_task_id=270,
            backlog_project_code="AA.J.31",
            link_type="workflow_approval_request",
        )
    )

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

    fake_project_task_class = type("FakeProjectTask", (), {"query": _FakeQuery()})
    monkeypatch.setattr(project_task_resource, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(project_task_resource, "apply_task_employee_filter", lambda query, company_id: query)
    monkeypatch.setattr(project_task_resource, "_user_can_update_task", lambda company_id, project_id, task_id: True)

    with app.test_request_context(
        "/api/projects/31/tasks/270/stage",
        method="PATCH",
        json={"stage": "completed"},
    ):
        session["active_company_id"] = 9
        response, status_code = project_task_resource.ProjectTaskStageResource().patch.__wrapped__(
            project_task_resource.ProjectTaskStageResource(),
            31,
            270,
        )

    assert status_code == 409
    assert "ações do backlog" in response["error"]


def test_project_task_transfer_resource_post_blocks_manual_transfer_on_human_gate_card(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    task = _build_backlog_task(
        agent_action_backlog_link=SimpleNamespace(
            project_task_id=270,
            backlog_project_code="AA.J.31",
            link_type="workflow_approval_request",
        )
    )

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

    fake_project_task_class = type("FakeProjectTask", (), {"query": _FakeQuery()})
    monkeypatch.setattr(project_task_resource, "ProjectTask", fake_project_task_class)
    monkeypatch.setattr(project_task_resource, "apply_task_employee_filter", lambda query, company_id: query)

    with app.test_request_context(
        "/api/projects/31/tasks/270/transfer",
        method="POST",
        json={"target_project_id": 99},
    ):
        session["active_company_id"] = 9
        response, status_code = project_task_resource.ProjectTaskTransferResource().post.__wrapped__(
            project_task_resource.ProjectTaskTransferResource(),
            31,
            270,
        )

    assert status_code == 409
    assert "espelhado" in response["error"]
