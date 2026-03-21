from types import SimpleNamespace
import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.resources.process import ProcessInstanceResource
import api.resources.process as process_module
import models.employee as employee_module


class _FakeEmployeeQuery:
    def __init__(self, employee):
        self._employee = employee

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._employee


def _build_instance():
    return SimpleNamespace(
        id=95,
        company_id=9,
        owner_employee_id=None,
        responsible_id=None,
        executor_id=22,
        collaborators_json=[],
    )


def test_process_instance_put_allows_assigned_collaborator_to_complete(monkeypatch):
    app = Flask(__name__)
    instance = _build_instance()
    captured = {}

    monkeypatch.setattr(process_module, "current_user", SimpleNamespace(id=7))
    monkeypatch.setattr(process_module, "has_company_full_access", lambda company_id: False)
    monkeypatch.setattr(
        process_module,
        "has_permission",
        lambda company_id, resource, action: action == "view",
    )
    monkeypatch.setattr(
        process_module,
        "ProcessInstance",
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda instance_id: instance)),
    )
    monkeypatch.setattr(
        employee_module,
        "Employee",
        SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(id=22, company_id=9))),
    )

    def _fake_load(data, instance=None, partial=True):
        captured["payload"] = data
        return instance

    monkeypatch.setattr(process_module.process_instance_schema, "load", _fake_load)
    monkeypatch.setattr(
        process_module.process_instance_schema,
        "dump",
        lambda value: {"id": value.id, "status": captured["payload"]["status"]},
    )
    monkeypatch.setattr(process_module.db.session, "commit", lambda: captured.setdefault("committed", True))

    with app.test_request_context(
        "/api/process-instances/95?company_id=9",
        method="PUT",
        json={"status": "completed", "actual_end_date": "2026-03-19", "completed_at": "2026-03-19T12:00:00"},
    ):
        response, status_code = ProcessInstanceResource.put.__wrapped__(ProcessInstanceResource(), 95)

    assert status_code == 200
    assert captured["payload"]["status"] == "completed"
    assert captured["committed"] is True
    assert response["status"] == "completed"


def test_process_instance_put_blocks_assigned_collaborator_from_editing_structural_fields(monkeypatch):
    app = Flask(__name__)
    instance = _build_instance()

    monkeypatch.setattr(process_module, "current_user", SimpleNamespace(id=7))
    monkeypatch.setattr(process_module, "has_company_full_access", lambda company_id: False)
    monkeypatch.setattr(
        process_module,
        "has_permission",
        lambda company_id, resource, action: action == "view",
    )
    monkeypatch.setattr(
        process_module,
        "ProcessInstance",
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda instance_id: instance)),
    )
    monkeypatch.setattr(
        employee_module,
        "Employee",
        SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(id=22, company_id=9))),
    )

    with app.test_request_context(
        "/api/process-instances/95?company_id=9",
        method="PUT",
        json={"title": "Mudanca indevida"},
    ):
        response, status_code = ProcessInstanceResource.put.__wrapped__(ProcessInstanceResource(), 95)

    assert status_code == 403
    assert "blocked_fields" in response["details"]
    assert response["details"]["blocked_fields"] == ["title"]
