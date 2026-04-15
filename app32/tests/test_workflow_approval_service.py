import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workflow_approval_service import WorkflowApprovalService, build_workflow_approval_board, build_workflow_approval_metrics, is_workflow_approval_expired, serialize_workflow_approval_action
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


def test_workflow_approval_service_tool_runtime_approval_returns_resume_hint():
    service = WorkflowApprovalService(
        resume_executor=lambda payload: DirectExecutionResult(executed=False),
        now_factory=lambda: datetime(2026, 3, 8, 12, 15, 0),
    )
    action = _build_action(
        payload={
            "created_via": "tool_runtime_guard",
            "request_payload": {"tool_name": "register_system_user"},
            "resume_payload": {
                "tool_name": "register_system_user",
                "company_id": 9,
            },
        }
    )

    outcome = service.approve(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is True
    assert action.status == "approved"
    assert "register_system_user" in outcome.message
    assert "repetir a mesma solicitação" in outcome.message



def test_workflow_approval_service_rejects_and_marks_action_without_resuming():
    called = {"resume": False}

    def _resume_executor(payload):
        called["resume"] = True
        return DirectExecutionResult(executed=True)

    service = WorkflowApprovalService(
        resume_executor=_resume_executor,
        now_factory=lambda: datetime(2026, 3, 8, 12, 30, 0),
    )
    action = _build_action()

    outcome = service.reject(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
        feedback="Executar somente após validar com o cliente.",
    )

    assert outcome.success is True
    assert action.status == "rejected"
    assert called["resume"] is False
    assert action.payload["approval_status"] == "rejected"
    assert action.payload["rejection_feedback"] == "Executar somente após validar com o cliente."
    assert outcome.audit_metadata["workflow_approval"]["event"] == "rejected"


def test_workflow_approval_service_blocks_expired_approval_until_revalidated():
    now = datetime(2026, 3, 8, 14, 0, 0)
    service = WorkflowApprovalService(
        resume_executor=lambda payload: DirectExecutionResult(executed=True),
        now_factory=lambda: now,
    )
    action = _build_action()
    action.created_at = datetime(2026, 3, 7, 10, 0, 0)

    outcome = service.approve(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is False
    assert outcome.http_status == 409
    assert action.status == 'pending'
    assert action.payload['approval_status'] == 'expired'
    assert outcome.audit_metadata['workflow_approval']['event'] == 'expired'


def test_workflow_approval_service_revalidates_pending_approval():
    now = datetime(2026, 3, 8, 14, 0, 0)
    service = WorkflowApprovalService(
        resume_executor=lambda payload: DirectExecutionResult(executed=True),
        now_factory=lambda: now,
        approval_ttl_hours=12,
    )
    action = _build_action()
    action.created_at = datetime(2026, 3, 7, 10, 0, 0)
    action.payload['approval_status'] = 'expired'
    action.payload['expired_at'] = '2026-03-08T14:00:00'

    outcome = service.revalidate(
        action=action,
        approver_user_id=7,
        approver_name="Fabiano Ferreira",
        active_company_id=9,
    )

    assert outcome.success is True
    assert action.status == 'pending'
    assert action.payload['approval_status'] == 'pending'
    assert action.payload['revalidated_by_user_id'] == 7
    assert action.payload['approval_expires_at'] == '2026-03-09T02:00:00'
    assert 'expired_at' not in action.payload
    assert outcome.audit_metadata['workflow_approval']['event'] == 'revalidated'


def test_serialize_workflow_approval_action_marks_expired_pending_action():
    action = _build_action()
    action.created_at = datetime(2026, 3, 7, 10, 0, 0)

    serialized = serialize_workflow_approval_action(action, now=datetime(2026, 3, 8, 14, 0, 0))

    assert serialized['approval']['expired'] is True
    assert serialized['approval']['approval_status'] == 'expired'
    assert serialized['approval']['expires_at'] == '2026-03-08T10:00:00'
    assert is_workflow_approval_expired(action, now=datetime(2026, 3, 8, 14, 0, 0)) is True


def test_build_workflow_approval_metrics_groups_by_status_channel_and_approver():
    pending = _build_action()
    pending.created_at = datetime(2026, 3, 8, 10, 0, 0)
    pending.user_id = 3
    pending.payload = {
        'action_key': 'meeting.start',
        'channel': 'whatsapp',
        'approval_status': 'pending',
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'whatsapp'},
    }

    executed = _build_action(status='executed')
    executed.created_at = datetime(2026, 3, 8, 9, 0, 0)
    executed.user_id = 3
    executed.payload = {
        'action_key': 'project_task.complete',
        'channel': 'telegram',
        'approval_status': 'approved',
        'approved_by_user_id': 7,
        'resume_payload': {'action_key': 'project_task.complete', 'channel': 'telegram'},
        'resume_result': {'executed': True},
    }

    expired = _build_action(action_id=101)
    expired.created_at = datetime(2026, 3, 7, 8, 0, 0)
    expired.user_id = 3
    expired.payload = {
        'action_key': 'meeting.start',
        'channel': 'email',
        'approval_status': 'expired',
        'approval_expires_at': '2026-03-08T08:00:00',
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'email'},
    }

    metrics = build_workflow_approval_metrics([pending, executed, expired], now=datetime(2026, 3, 8, 12, 0, 0))

    assert metrics['total'] == 3
    assert metrics['by_status']['pending'] == 1
    assert metrics['by_status']['approved'] == 1
    assert metrics['by_status']['expired'] == 1
    assert metrics['by_action_key']['meeting.start'] == 2
    assert metrics['by_channel']['telegram'] == 1
    assert metrics['by_channel']['email'] == 1
    assert metrics['by_requester_user_id']['3'] == 3
    assert metrics['by_approver_user_id']['7'] == 1
    assert metrics['by_approver_user_id']['unassigned'] == 2
    assert metrics['expired_pending'] == 1


def test_build_workflow_approval_board_exposes_filters_and_channel_experience():
    pending = _build_action()
    pending.created_at = datetime(2026, 3, 8, 10, 0, 0)
    pending.payload = {
        'action_key': 'meeting.start',
        'channel': 'instagram',
        'approval_status': 'pending',
        'object_code': 'R-77',
        'resume_payload': {'action_key': 'meeting.start', 'channel': 'instagram'},
    }
    pending.description = 'Início de reunião sensível via Instagram.'

    executed = _build_action(action_id=102, status='executed')
    executed.created_at = datetime(2026, 3, 8, 9, 0, 0)
    executed.payload = {
        'action_key': 'project_task.complete',
        'channel': 'web',
        'approval_status': 'approved',
        'object_code': 'AA.J.31.203',
        'approved_by_user_id': 7,
        'resume_payload': {'action_key': 'project_task.complete', 'channel': 'web'},
        'resume_result': {'executed': True},
    }
    executed.description = 'Conclusão sensível feita via painel web.'

    board = build_workflow_approval_board([pending, executed], now=datetime(2026, 3, 8, 12, 0, 0))

    assert board['board_meta']['total_cards'] == 2
    assert 'instagram' in board['board_meta']['channels']
    assert 'chat' in board['board_meta']['channel_families']
    assert any(item['id'] == 'all' and item['value'] == 2 for item in board['quick_filters']['status'])
    assert any(item['id'] == 'instagram' and item['value'] == 1 for item in board['quick_filters']['channel'])
    assert any(item['id'] == 'chat' and item['value'] == 1 for item in board['quick_filters']['channel_family'])

    instagram_card = board['approval_cards'][0]
    assert instagram_card['channel_family'] == 'chat'
    assert instagram_card['experience']['layout_hint'] == 'compact'
    assert 'cards compactos' in instagram_card['experience']['capability_summary']
    assert instagram_card['search_blob'].startswith('meeting.start instagram chat')

    web_card = board['approval_cards'][1]
    assert web_card['channel_family'] == 'web'
    assert web_card['experience']['layout_hint'] == 'rich'
    assert 'cards ricos' in web_card['experience']['capability_summary']
