import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.resources import project_task as project_task_resource


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    return app


def test_put_allows_operational_task_edit_without_explicit_projects_edit(monkeypatch):
    app = _build_app()
    task = SimpleNamespace(
        id=17,
        project_id=74,
        what="Atividade original",
        employee_id=None,
        due_date=None,
        estimated_hours=0,
        score_weight=1,
        how=None,
        notes=None,
        logs=[],
        completion_date=None,
        status="planned",
        stage="inbox",
        project=None,
        update_progress=lambda: None,
    )
    project = SimpleNamespace(update_progress=lambda: None)

    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first_or_404(self):
            return task

        def first(self):
            return task

    captured = {}

    def _fake_load(data, instance=None, partial=False):
        captured["payload"] = dict(data)
        instance.what = data.get("what", instance.what)
        instance.employee_id = data.get("employee_id", instance.employee_id)
        instance.due_date = data.get("due_date", instance.due_date)
        instance.notes = data.get("notes", instance.notes)
        return instance

    monkeypatch.setattr(project_task_resource, "ProjectTask", type("FakeProjectTask", (), {"query": _FakeQuery()}))
    monkeypatch.setattr(project_task_resource, "Project", type("FakeProject", (), {"query": SimpleNamespace(get=lambda _id: project)}))
    monkeypatch.setattr(project_task_resource, "apply_task_employee_filter", lambda query, company_id: query)
    monkeypatch.setattr(project_task_resource, "_get_project_company_id", lambda project_id: 9)
    monkeypatch.setattr(project_task_resource, "_user_can_update_task", lambda company_id, project_id, task_id: True)
    monkeypatch.setattr(project_task_resource, "can_manage_project_tasks", lambda company_id: company_id == 9)
    monkeypatch.setattr(project_task_resource, "project_task_schema", SimpleNamespace(load=_fake_load))
    monkeypatch.setattr(
        project_task_resource,
        "_serialize_task",
        lambda current_task, **_kwargs: {
            "id": current_task.id,
            "employee_id": current_task.employee_id,
            "due_date": current_task.due_date,
            "notes": current_task.notes,
        },
    )
    monkeypatch.setattr(project_task_resource.db.session, "commit", lambda: None)
    monkeypatch.setattr(project_task_resource.db.session, "rollback", lambda: None)

    with app.test_request_context(
        "/api/projects/74/tasks/17",
        method="PUT",
        json={
            "what": "Nova atividade",
            "employee_id": 33,
            "due_date": "2026-05-30",
            "notes": "Observações atualizadas",
            "logs": [],
        },
    ):
        session["active_company_id"] = 9
        response, status_code = project_task_resource.ProjectTaskResource().put.__wrapped__(
            project_task_resource.ProjectTaskResource(),
            74,
            17,
        )

    assert status_code == 200
    assert captured["payload"]["employee_id"] == 33
    assert captured["payload"]["due_date"] == "2026-05-30"
    assert captured["payload"]["notes"] == "Observações atualizadas"
    assert response["employee_id"] == 33
    assert response["notes"] == "Observações atualizadas"
