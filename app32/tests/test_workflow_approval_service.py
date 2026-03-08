import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workflow_approval_service import WorkflowApprovalService
from src.intelligence.workflows.direct_execution import DirectExecutionResult


def _build_action(**overrides):
    payload = {
        "resume_payload": {
            "action_key": "meeting.start",
            "payload": {"codigo_reuniao": "R-55"},
            "active_company_id": 9,
            "user_id": 3,
            "channel": "whatsapp",
        }
    }
    data = {
        "id": 99,
        "company_id": 9,
        "status": "pending",
        "payload": payload,
        "user_feedback": None,
        "resolved_at": None,
        "executed_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_workflow_approval_service_executes_resume_payload_when_approved():
    captured = {}
    now = datetime(2026, 3, 8, 11, 30, 0)

    def _resume_executor(resume_payload):
        captured["resume_payload"] = dict(resume_payload)
        return DirectExecutionResult(
            executed=True,
            response_text="Reunião iniciada com sucesso.",
            metadata={"workflow_approval": {"status": "resumed_execution"}},
        )

    service = WorkflowApprovalService(
        resume_executor=_resume_executor,
        now_factory=lambda: now,
    )
    action = _build_action()

    outcome = service.approve(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is True
    assert outcome.action_status == "executed"
    assert action.status == "executed"
    assert action.executed_at == now
    assert action.resolved_at == now
    assert captured["resume_payload"]["approved_action_id"] == 99
    assert outcome.resume_result["metadata"]["workflow_approval"]["status"] == "resumed_execution"
    assert action.payload["approval_status"] == "approved"


def test_workflow_approval_service_blocks_company_mismatch():
    service = WorkflowApprovalService(resume_executor=lambda payload: DirectExecutionResult(executed=True))
    action = _build_action(company_id=12)

    outcome = service.approve(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is False
    assert outcome.http_status == 403
    assert action.status == "pending"


def test_workflow_approval_service_keeps_action_approved_when_resume_does_not_execute():
    service = WorkflowApprovalService(
        resume_executor=lambda payload: DirectExecutionResult(
            executed=False,
            response_text="A retomada não executou.",
        ),
        now_factory=lambda: datetime(2026, 3, 8, 12, 0, 0),
    )
    action = _build_action()

    outcome = service.approve(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is True
    assert outcome.action_status == "approved"
    assert action.status == "approved"
    assert action.payload["resume_result"]["executed"] is False
