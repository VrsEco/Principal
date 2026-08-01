import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from models.process_assignment import ProcessExecutionAssignment  # noqa: E402
from services import process_assignment_service as service  # noqa: E402


def _execution(**overrides):
    payload = {
        "status": "pending",
        "execution_mode": "human_task",
        "metadata_json": {},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_assignment_model_is_tenant_safe_and_has_target_constraints():
    assert ProcessExecutionAssignment.__table__.columns["company_id"].nullable is False
    constraints = {item.name for item in ProcessExecutionAssignment.__table__.constraints}
    assert "ck_process_execution_assignment_type" in constraints
    assert "ck_process_execution_assignment_status" in constraints
    assert "ck_process_execution_assignment_target" in constraints
    assert "uq_process_execution_assignment_active" in {
        item.name for item in ProcessExecutionAssignment.__table__.indexes
    }


def test_extract_assignment_payload_removes_transport_fields():
    payload = {"status": "pending", "assigned_employee_id": "17"}

    assignment = service.extract_assignment_payload(payload)

    assert assignment == {"assignee_type": "employee", "employee_id": "17"}
    assert payload == {"status": "pending"}


def test_human_execution_is_actionable():
    assert service.is_execution_actionable(_execution()) is True


def test_automatic_execution_only_becomes_actionable_with_human_gate():
    assert service.is_execution_actionable(_execution(execution_mode="automatic")) is False
    assert service.is_execution_actionable(
        _execution(execution_mode="automatic", metadata_json={"requires_human_gate": True})
    ) is True


def test_terminal_execution_is_not_actionable_even_for_human_mode():
    assert service.is_execution_actionable(_execution(status="completed")) is False
