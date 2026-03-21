from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    MyWorkExecutionHandler,
    MyWorkExecutionRequest,
)


def _build_handler(**overrides):
    captured = {}

    def fake_resolve_company_ids_for_payload(payload, active_company_id, user_id):
        captured["resolved"] = {
            "payload": dict(payload or {}),
            "active_company_id": active_company_id,
            "user_id": user_id,
        }
        return [9], "empresa AA - Versus"

    def fake_resolve_employee_ids_for_report(user_id, company_ids):
        captured["employee_scope"] = {"user_id": user_id, "company_ids": list(company_ids)}
        return None

    def fake_resolve_employee_scope_for_payload(payload, user_id, company_ids, default_employee_ids):
        captured["employee_scope_payload"] = {
            "payload": dict(payload or {}),
            "user_id": user_id,
            "company_ids": list(company_ids),
            "default_employee_ids": None if default_employee_ids is None else list(default_employee_ids),
        }
        collaborator = payload.get("colaborador")
        if collaborator:
            return [91], collaborator, None
        return default_employee_ids, None, None

    def fake_resolve_period_from_payload(payload):
        captured["period_payload"] = dict(payload or {})
        return date(2026, 3, 5), date(2026, 3, 19)

    def fake_load_project_tasks_report(**kwargs):
        captured.setdefault("tasks_calls", []).append(dict(kwargs))
        return [{"activity_code": "AA.J.17.31", "title": "Configurar dashboards"}]

    def fake_load_process_instances_report(**kwargs):
        captured.setdefault("process_calls", []).append(dict(kwargs))
        return [{"instance_code": "AA.P95.001", "title": "Aprovacao Financeira"}]

    def fake_load_meetings_report(**kwargs):
        captured.setdefault("meeting_calls", []).append(dict(kwargs))
        return [{"meeting_code": "AA.R.12", "meeting_name": "Reuniao Operacional"}]

    def fake_format_my_work_report(**kwargs):
        captured["formatted"] = dict(kwargs)
        return f"report:{kwargs['action']}:{kwargs['company_label']}"

    def fake_build_operational_form(action, payload, active_company_id, channel):
        captured["intent_form_request"] = {
            "action": action,
            "payload": dict(payload or {}),
            "active_company_id": active_company_id,
            "channel": channel,
        }
        return None, None

    defaults = {
        "resolve_company_ids_for_payload": fake_resolve_company_ids_for_payload,
        "resolve_employee_ids_for_report": fake_resolve_employee_ids_for_report,
        "resolve_employee_scope_for_payload": fake_resolve_employee_scope_for_payload,
        "resolve_period_from_payload": fake_resolve_period_from_payload,
        "load_project_tasks_report": fake_load_project_tasks_report,
        "load_process_instances_report": fake_load_process_instances_report,
        "load_meetings_report": fake_load_meetings_report,
        "format_my_work_report": fake_format_my_work_report,
        "build_operational_form": fake_build_operational_form,
    }
    defaults.update(overrides)
    return MyWorkExecutionHandler(**defaults), captured


def test_my_work_handler_returns_scope_error():
    handler, _ = _build_handler(
        resolve_company_ids_for_payload=lambda payload, active_company_id, user_id: (
            [],
            "Nao encontrei empresa para consulta.",
        )
    )

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei empresa para consulta."


def test_my_work_handler_requires_period_for_range_queries():
    handler, _ = _build_handler(
        resolve_period_from_payload=lambda payload: (None, None),
    )

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.due_range",
            payload={"periodo": "qualquer"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "periodo: 01/03/2026 a 07/03/2026" in result.response_text


def test_my_work_handler_formats_success_for_open_query():
    handler, captured = _build_handler()

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={"empresa": "Versus"},
            active_company_id=9,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert captured["resolved"]["active_company_id"] == 9
    assert captured["tasks_calls"][0]["mode"] == "my_work.open"
    assert captured["formatted"]["action"] == "my_work.open"
    assert captured["formatted"]["channel"] == "whatsapp"
    assert result.response_text == "report:my_work.open:empresa AA - Versus"


def test_my_work_handler_formats_success_for_completed_range():
    handler, captured = _build_handler()

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.completed_range",
            payload={"periodo": "05/03/2026 a 19/03/2026"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["period_payload"]["periodo"] == "05/03/2026 a 19/03/2026"
    assert captured["tasks_calls"][0]["start_date"] == date(2026, 3, 5)
    assert captured["tasks_calls"][0]["end_date"] == date(2026, 3, 19)
    assert result.response_text == "report:my_work.completed_range:empresa AA - Versus"



def test_my_work_handler_restricts_collaborator_to_own_employee_ids():
    handler, captured = _build_handler(
        resolve_employee_ids_for_report=lambda user_id, company_ids: [77],
    )

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={"empresa": "Versus"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["tasks_calls"][0]["employee_ids"] == [77]
    assert captured["process_calls"][0]["employee_ids"] == [77]
    assert result.response_text == "report:my_work.open:empresa AA - Versus"


def test_my_work_handler_filters_by_payload_collaborator_and_skips_non_requested_entities():
    handler, captured = _build_handler()

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.overdue",
            payload={
                "empresa": "Versus",
                "colaborador": "Caroline Marques",
                "entidade": "process_instance",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["employee_scope_payload"]["payload"]["colaborador"] == "Caroline Marques"
    assert captured["process_calls"][0]["employee_ids"] == [91]
    assert "tasks_calls" not in captured
    assert "meeting_calls" not in captured
    assert result.response_text == "report:my_work.overdue:empresa AA - Versus"


def test_my_work_handler_returns_collaborator_resolution_error():
    handler, _ = _build_handler(
        resolve_employee_scope_for_payload=lambda payload, user_id, company_ids, default_employee_ids: (
            None,
            None,
            "Nao encontrei colaborador para 'Joaquim Guga'.",
        )
    )

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={"empresa": "Versus", "colaborador": "Joaquim Guga"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei colaborador para 'Joaquim Guga'."


def test_my_work_handler_requires_period_when_due_range_is_selected_for_today_queue():
    handler, captured = _build_handler()

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.due_range",
            payload={"periodo": "hoje", "empresa": "Versus"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["period_payload"]["periodo"] == "hoje"
    assert captured["tasks_calls"][0]["start_date"] == date(2026, 3, 5)
    assert captured["tasks_calls"][0]["end_date"] == date(2026, 3, 19)
    assert result.response_text == "report:my_work.due_range:empresa AA - Versus"


def test_my_work_handler_uses_canonical_intent_form_payload_when_available():
    from src.intelligence.intents.schemas import (
        CompanyScopeForm,
        FilterScopeForm,
        OperationalIntentForm,
        ResolutionScopeForm,
        SourceScopeForm,
        SubjectScopeForm,
    )

    def fake_build_operational_form(action, payload, active_company_id, channel):
        return (
            OperationalIntentForm(
                intent_kind="query",
                intent_code="query.my_work.open",
                entity_type="project_task",
                company_scope=CompanyScopeForm(company_ids=[9]),
                subject_scope=SubjectScopeForm(responsible_names=["Caroline Marques"]),
                filter_scope=FilterScopeForm(status="open", entity_hint="project_task"),
                resolution_scope=ResolutionScopeForm(status="ready"),
                source_scope=SourceScopeForm(origin_channel=channel, detected_action_key=action),
            ),
            None,
        )

    handler, captured = _build_handler(build_operational_form=fake_build_operational_form)

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={"empresa": "Ignorar este termo"},
            active_company_id=1,
            user_id=10,
        )
    )

    assert captured["resolved"]["payload"]["_selected_company_id"] == 9
    assert captured["resolved"]["payload"]["colaborador"] == "Caroline Marques"
    assert captured["resolved"]["payload"]["entidade"] == "project_task"
    assert "meeting_calls" not in captured
    assert result.response_text == "report:my_work.open:empresa AA - Versus"


def test_my_work_handler_returns_form_missing_fields_error():
    handler, _ = _build_handler(
        build_operational_form=lambda action, payload, active_company_id, channel: (None, "Formulario invalido")
    )

    result = handler.execute(
        MyWorkExecutionRequest(
            action="my_work.open",
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Formulario invalido"
