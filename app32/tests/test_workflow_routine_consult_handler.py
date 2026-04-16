import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.intents.schemas import (
    CompanyScopeForm,
    FilterScopeForm,
    OperationalIntentForm,
    ResolutionScopeForm,
    SourceScopeForm,
)
from src.intelligence.workflows.handlers import (
    MyWorkExecutionResult,
    RoutineConsultExecutionHandler,
    RoutineConsultExecutionRequest,
)


def test_routine_consult_handler_routes_period_queries_to_due_range():
    captured = {}

    def fake_build_operational_form(action, payload, active_company_id, channel):
        return (
            OperationalIntentForm(
                intent_kind="query",
                intent_code="query.routine.consult",
                entity_type="project_task",
                company_scope=CompanyScopeForm(company_ids=[9]),
                filter_scope=FilterScopeForm(
                    status="open",
                    entity_hint="project_task",
                    period_label="hoje",
                    date_mode="today",
                ),
                resolution_scope=ResolutionScopeForm(status="ready"),
                source_scope=SourceScopeForm(origin_channel=channel, detected_action_key=action),
            ),
            None,
        )

    def fake_execute_my_work(request):
        captured["request"] = request
        return MyWorkExecutionResult(response_text="ok:due_range")

    handler = RoutineConsultExecutionHandler(
        build_operational_form=fake_build_operational_form,
        execute_my_work=fake_execute_my_work,
    )

    result = handler.execute(
        RoutineConsultExecutionRequest(
            action="routine.consult",
            payload={"empresa": "Versus"},
            active_company_id=1,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert captured["request"].action == "my_work.due_range"
    assert captured["request"].payload["_selected_company_id"] == 9
    assert captured["request"].payload["periodo"] == "hoje"
    assert result.response_text == "ok:due_range"


def test_routine_consult_handler_routes_overdue_queries_without_period():
    captured = {}

    def fake_build_operational_form(action, payload, active_company_id, channel):
        return (
            OperationalIntentForm(
                intent_kind="query",
                intent_code="query.routine.consult",
                entity_type="mixed",
                filter_scope=FilterScopeForm(status="overdue", entity_hint="mixed"),
                resolution_scope=ResolutionScopeForm(status="ready"),
                source_scope=SourceScopeForm(origin_channel=channel, detected_action_key=action),
            ),
            None,
        )

    def fake_execute_my_work(request):
        captured["action"] = request.action
        return MyWorkExecutionResult(response_text="ok:overdue")

    handler = RoutineConsultExecutionHandler(
        build_operational_form=fake_build_operational_form,
        execute_my_work=fake_execute_my_work,
    )

    result = handler.execute(
        RoutineConsultExecutionRequest(
            action="routine.consult",
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["action"] == "my_work.overdue"
    assert result.response_text == "ok:overdue"
