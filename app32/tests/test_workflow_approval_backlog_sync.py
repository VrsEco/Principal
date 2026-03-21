import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.workflow_approval_service as workflow_approval_service
from services.workflow_approval_service import WorkflowApprovalService
from src.intelligence.workflows.direct_execution import DirectExecutionResult


def _build_action():
    return SimpleNamespace(
        id=55,
        company_id=9,
        status="pending",
        payload={
            "resume_payload": {
                "action_key": "meeting.start",
                "payload": {"codigo_reuniao": "R-55"},
                "active_company_id": 9,
                "user_id": 3,
                "channel": "whatsapp",
            }
        },
        user_feedback=None,
        resolved_at=None,
        executed_at=None,
        created_at=datetime(2026, 3, 8, 10, 0, 0),
    )


def test_workflow_approval_service_syncs_backlog_after_approve(monkeypatch):
    synced = {}

    monkeypatch.setattr(
        workflow_approval_service,
        "sync_backlog_task_for_action",
        lambda action: synced.setdefault("action_status", action.status),
    )

    service = WorkflowApprovalService(
        resume_executor=lambda payload: DirectExecutionResult(
            executed=False,
            response_text="Aprovado sem execução automática.",
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
    assert synced["action_status"] == "approved"
