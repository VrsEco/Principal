import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.project_task_due_date_change_service as due_date_change_service


class _EmployeeQuery:
    def __init__(self, employee):
        self.employee = employee

    def filter_by(self, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self.employee


def _configure_actor(monkeypatch, *, employee, can_edit=False):
    monkeypatch.setattr(
        due_date_change_service,
        "current_user",
        SimpleNamespace(id=employee.user_id, name=employee.name, username=employee.name, is_authenticated=True),
    )
    monkeypatch.setattr(
        due_date_change_service,
        "Employee",
        SimpleNamespace(
            query=_EmployeeQuery(employee),
            id=SimpleNamespace(asc=lambda: None),
        ),
    )
    monkeypatch.setattr(
        due_date_change_service,
        "has_permission",
        lambda *_args: can_edit,
    )


def test_task_responsible_can_apply_own_due_date_change(monkeypatch):
    employee = SimpleNamespace(id=42, user_id=7, name="Aline Souza")
    _configure_actor(monkeypatch, employee=employee)

    allowed = due_date_change_service.ProjectTaskDueDateChangeService.user_can_apply_due_date_change(
        SimpleNamespace(employee_id=42), SimpleNamespace(owner="Outra pessoa"), 9
    )

    assert allowed is True


def test_privileged_user_can_apply_due_date_change_for_any_task(monkeypatch):
    employee = SimpleNamespace(id=42, user_id=7, name="Aline Souza")
    _configure_actor(monkeypatch, employee=employee, can_edit=True)

    allowed = due_date_change_service.ProjectTaskDueDateChangeService.user_can_apply_due_date_change(
        SimpleNamespace(employee_id=99), SimpleNamespace(owner="Outra pessoa"), 9
    )

    assert allowed is True


def test_unrelated_user_must_use_request_flow(monkeypatch):
    employee = SimpleNamespace(id=42, user_id=7, name="Aline Souza")
    _configure_actor(monkeypatch, employee=employee)

    allowed = due_date_change_service.ProjectTaskDueDateChangeService.user_can_apply_due_date_change(
        SimpleNamespace(employee_id=99), SimpleNamespace(owner="Outra pessoa"), 9
    )

    assert allowed is False


def test_create_or_apply_returns_approved_result_for_authorized_actor(monkeypatch):
    service = due_date_change_service.ProjectTaskDueDateChangeService
    task = SimpleNamespace(id=21, employee_id=42)
    project = SimpleNamespace(id=5, owner="Aline Souza")
    request_obj = SimpleNamespace(id=81)
    calls = []

    monkeypatch.setattr(service, "get_task_or_error", lambda **_kwargs: (task, project, None))
    monkeypatch.setattr(service, "create_request", lambda **_kwargs: (request_obj, None))
    monkeypatch.setattr(service, "user_can_apply_due_date_change", lambda *_args: True)
    monkeypatch.setattr(
        service,
        "decide_request",
        lambda **kwargs: (calls.append(kwargs) or request_obj, None),
    )

    result, returned_task, applied_directly, error = service.create_or_apply_request(
        company_id=9,
        project_id=5,
        task_id=21,
        requested_due_date="2026-10-10",
        reason="Dependência externa",
    )

    assert (result, returned_task, applied_directly, error) == (request_obj, task, True, None)
    assert calls == [{
        "company_id": 9,
        "project_id": 5,
        "task_id": 21,
        "request_id": 81,
        "action": "approve",
        "approved_due_date": "2026-10-10",
    }]
