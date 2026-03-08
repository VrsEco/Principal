import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.direct_execution import (
    DirectExecutionDispatcher,
    DirectExecutionRequest,
    build_direct_execution_request,
    build_handler_executor,
)
from src.intelligence.workflows.policy import WorkflowApprovalPolicyGuard, WorkflowApprovalRequest
from src.intelligence.workflows.handlers import MyWorkExecutionRequest


class _DummyRequest:
    def __init__(self, response_text: str):
        self.response_text = response_text


class _DummyHandler:
    def __init__(self, sink):
        self._sink = sink

    def execute(self, request):
        self._sink.append(request)
        return _DummyRequest(response_text="executado")


def test_direct_execution_dispatcher_executes_registered_handler():
    dispatcher = DirectExecutionDispatcher(
        {
            "project_task.create": lambda request: (
                f"{request.action_key}:{request.payload.get('nome_atividade')}:{request.active_company_id}:{request.user_id}:{request.channel}"
            )
        }
    )

    result = dispatcher.execute(
        DirectExecutionRequest(
            action_key="project_task.create",
            payload={"nome_atividade": "Implementar V3"},
            active_company_id=9,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert result.executed is True
    assert result.response_text == "project_task.create:Implementar V3:9:10:whatsapp"


def test_direct_execution_dispatcher_normalizes_action_key_and_returns_not_executed_for_unknown():
    dispatcher = DirectExecutionDispatcher(
        {
            "meeting.schedule": lambda request: "ok",
        }
    )

    known = dispatcher.execute(
        DirectExecutionRequest(
            action_key=" Meeting.Schedule ",
            payload={},
            active_company_id=None,
            user_id=10,
        )
    )
    unknown = dispatcher.execute(
        DirectExecutionRequest(
            action_key="summary.week",
            payload={},
            active_company_id=None,
            user_id=10,
        )
    )

    assert known.executed is True
    assert known.response_text == "ok"
    assert unknown.executed is False
    assert unknown.response_text is None


def test_direct_execution_dispatcher_treats_none_response_as_not_executed():
    dispatcher = DirectExecutionDispatcher(
        {
            "onboarding.start": lambda request: None,
        }
    )

    result = dispatcher.execute(
        DirectExecutionRequest(
            action_key="onboarding.start",
            payload={},
            active_company_id=1,
            user_id=10,
        )
    )

    assert result.executed is False
    assert result.response_text is None


def test_build_direct_execution_request_maps_shared_fields_and_action_override():
    direct_request = DirectExecutionRequest(
        action_key="my_work.open",
        payload={"periodo": "esta semana"},
        active_company_id=9,
        user_id=10,
        channel="telegram",
    )

    request = build_direct_execution_request(
        direct_request,
        MyWorkExecutionRequest,
        action_override="my_work.overdue",
    )

    assert isinstance(request, MyWorkExecutionRequest)
    assert request.action == "my_work.overdue"
    assert request.payload == {"periodo": "esta semana"}
    assert request.active_company_id == 9
    assert request.user_id == 10
    assert request.channel == "telegram"


def test_build_handler_executor_builds_request_and_returns_response_text():
    captured_requests = []

    def _factory():
        return _DummyHandler(captured_requests)

    executor = build_handler_executor(
        handler_factory=_factory,
        request_model=MyWorkExecutionRequest,
        action_override="my_work.completed_range",
    )

    response_text = executor(
        DirectExecutionRequest(
            action_key="my_work.open",
            payload={"periodo": "este mes"},
            active_company_id=3,
            user_id=7,
            channel="email",
        )
    )

    assert response_text == "executado"
    assert len(captured_requests) == 1
    built_request = captured_requests[0]
    assert isinstance(built_request, MyWorkExecutionRequest)
    assert built_request.action == "my_work.completed_range"
    assert built_request.payload == {"periodo": "este mes"}
    assert built_request.active_company_id == 3
    assert built_request.user_id == 7
    assert built_request.channel == "email"


def test_direct_execution_dispatcher_blocks_sensitive_action_via_policy_guard():
    created = []

    def _create_approval_request(request, context):
        created.append((request, context))
        return WorkflowApprovalRequest(approval_id=77, reused_existing=False, approval_key=context['approval_key'], action_key=context['action_key'], object_code=context['object_code'], resume_payload=context['resume_payload'])

    guard = WorkflowApprovalPolicyGuard(create_approval_request=_create_approval_request)
    dispatcher = DirectExecutionDispatcher(
        {
            "project_task.complete": lambda request: "nao deveria executar",
        },
        policy_guard=guard.evaluate,
    )

    result = dispatcher.execute(
        DirectExecutionRequest(
            action_key="project_task.complete",
            payload={"codigo_atividade": "AA.J.31.202"},
            active_company_id=9,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert result.executed is True
    assert "aprovação humana" in result.response_text.lower()
    assert "#77" in result.response_text
    assert len(created) == 1
    assert created[0][1]["action_key"] == "project_task.complete"
    assert result.metadata["workflow_approval"]["approval_request_id"] == 77
    assert result.metadata["workflow_approval"]["resume_payload"]["payload"]["codigo_atividade"] == "AA.J.31.202"


def test_workflow_approval_policy_guard_allows_sensitive_action_on_web_channel():
    guard = WorkflowApprovalPolicyGuard(
        create_approval_request=lambda request, context: WorkflowApprovalRequest(approval_id=1)
    )

    response = guard.evaluate(
        DirectExecutionRequest(
            action_key="meeting.start",
            payload={"codigo_reuniao": "R-15"},
            active_company_id=9,
            user_id=10,
            channel="web",
        )
    )

    assert response is None


def test_workflow_approval_policy_guard_requires_company_for_sensitive_action():
    guard = WorkflowApprovalPolicyGuard(
        create_approval_request=lambda request, context: WorkflowApprovalRequest(approval_id=1)
    )

    response = guard.evaluate(
        DirectExecutionRequest(
            action_key="process_instance.complete",
            payload={"codigo_instancia": "PI-9"},
            active_company_id=None,
            user_id=10,
            channel="telegram",
        )
    )

    assert "empresa ativa" in response.response_text.lower()
    assert response.metadata["workflow_approval"]["status"] == "missing_company_context"
