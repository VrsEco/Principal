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

    defaults = {
        "resolve_company_ids_for_payload": fake_resolve_company_ids_for_payload,
        "resolve_period_from_payload": fake_resolve_period_from_payload,
        "load_project_tasks_report": fake_load_project_tasks_report,
        "load_process_instances_report": fake_load_process_instances_report,
        "load_meetings_report": fake_load_meetings_report,
        "format_my_work_report": fake_format_my_work_report,
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
