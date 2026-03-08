import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers.collaborator_handler import (
    CollaboratorOccupancyExecutionHandler,
)
from src.intelligence.workflows.schemas.collaborator import CollaboratorOccupancyRequest


class _Employee:
    def __init__(self, employee_id=7, name="Fabiano", weekly_hours=40):
        self.id = employee_id
        self.name = name
        self.weekly_hours = weekly_hours


def _build_handler(**overrides):
    captured = {}

    def fake_resolve_single_company_for_operation(payload, active_company_id, user_id):
        captured["company"] = {
            "payload": dict(payload or {}),
            "active_company_id": active_company_id,
            "user_id": user_id,
        }
        return 9, None

    def fake_resolve_period_from_payload(payload):
        captured["period_payload"] = dict(payload or {})
        return date(2026, 3, 3), date(2026, 3, 7)

    def fake_resolve_employee_for_company(company_id, collaborator_term):
        captured["employee_term"] = (company_id, collaborator_term)
        return _Employee(), None

    def fake_calculate_available_hours(employee, start_date, end_date):
        captured["available_input"] = (employee.id, start_date, end_date)
        return 40.0

    def fake_load_process_hours_taken(employee, start_date, end_date):
        return 12.5

    def fake_load_project_hours_taken(employee, start_date, end_date):
        return 8.0

    def fake_load_project_hours_committed(employee, start_date, end_date):
        return 16.0

    def fake_format_report(**kwargs):
        captured["format"] = dict(kwargs)
        return f"report:{kwargs['collaborator_name']}:{kwargs['available_hours']}"

    defaults = {
        "resolve_single_company_for_operation": fake_resolve_single_company_for_operation,
        "resolve_period_from_payload": fake_resolve_period_from_payload,
        "resolve_employee_for_company": fake_resolve_employee_for_company,
        "calculate_available_hours": fake_calculate_available_hours,
        "load_process_hours_taken": fake_load_process_hours_taken,
        "load_project_hours_taken": fake_load_project_hours_taken,
        "load_project_hours_committed": fake_load_project_hours_committed,
        "format_report": fake_format_report,
    }
    defaults.update(overrides)
    return CollaboratorOccupancyExecutionHandler(**defaults), captured


def test_collaborator_occupancy_requires_collaborator():
    handler, _ = _build_handler()

    result = handler.execute(
        CollaboratorOccupancyRequest(payload={}, active_company_id=9, user_id=10)
    )

    assert "colaborador: NOME_DO_COLABORADOR" in result.response_text


def test_collaborator_occupancy_requires_period():
    handler, _ = _build_handler(resolve_period_from_payload=lambda payload: (None, None))

    result = handler.execute(
        CollaboratorOccupancyRequest(
            payload={"colaborador": "Fabiano"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "periodo: 01/03/2026 a 07/03/2026" in result.response_text


def test_collaborator_occupancy_handles_employee_resolution_error():
    handler, _ = _build_handler(
        resolve_employee_for_company=lambda company_id, collaborator_term: (None, "Nao encontrei colaborador."),
    )

    result = handler.execute(
        CollaboratorOccupancyRequest(
            payload={"colaborador": "Fulano", "periodo": "03/03/2026 a 07/03/2026"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei colaborador."


def test_collaborator_occupancy_formats_success():
    handler, captured = _build_handler()

    result = handler.execute(
        CollaboratorOccupancyRequest(
            payload={
                "empresa": "AA - Versus",
                "colaborador": "Fabiano",
                "periodo": "03/03/2026 a 07/03/2026",
                "_selected_company_label": "AA - Versus",
            },
            active_company_id=9,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert captured["employee_term"] == (9, "Fabiano")
    assert captured["format"]["company_label"] == "AA - Versus"
    assert captured["format"]["project_hours_committed"] == 16.0
    assert captured["format"]["channel"] == "whatsapp"
    assert result.response_text == "report:Fabiano:40.0"
