import os
import sys
from types import SimpleNamespace


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import process_assignment_service as assignment_service


def _instance(**overrides):
    data = {
        'company_id': 10,
        'owner_employee_id': 7,
        'responsible_id': 8,
        'executor_id': 9,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_employee_can_execute_activity_for_direct_runtime_roles(monkeypatch):
    monkeypatch.setattr(assignment_service, 'employee_assignment_execution_ids', lambda *_: [])

    assert assignment_service.employee_can_execute_activity(10, 7, _instance(), 501) is True
    assert assignment_service.employee_can_execute_activity(10, 8, _instance(), 501) is True
    assert assignment_service.employee_can_execute_activity(10, 9, _instance(), 501) is True


def test_employee_can_execute_only_assigned_activity_in_same_tenant(monkeypatch):
    monkeypatch.setattr(assignment_service, 'employee_assignment_execution_ids', lambda *_: [501])

    assert assignment_service.employee_can_execute_activity(10, 15, _instance(), 501) is True
    assert assignment_service.employee_can_execute_activity(10, 15, _instance(), 999) is False
    assert assignment_service.employee_can_execute_activity(11, 15, _instance(), 501) is False


def test_runtime_pop_exposes_linked_forms_and_checklists():
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'process_instance_runtime.js')
    )
    with open(script_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'Formulários e checklists vinculados' in content
    assert 'data-pop-artifact-id' in content
    assert 'openArtifactExecution' in content
