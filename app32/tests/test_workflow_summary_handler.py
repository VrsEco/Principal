from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    SummaryExecutionRequest,
    SummaryWorkflowExecutionHandler,
)


class DummyCompany:
    def __init__(self, company_id: int, name: str, client_code: str = ""):
        self.id = company_id
        self.name = name
        self.client_code = client_code


class DummyEmployee:
    def __init__(self, employee_id: int, name: str, email: str = ""):
        self.id = employee_id
        self.name = name
        self.email = email


def _build_handler(**overrides):
    def format_label(names, *, all_selected=False):
        if all_selected:
            return "Todos os colaboradores"
        return ", ".join(names)

    defaults = {
        "user_can_access_company": lambda user_id, company_id: True,
        "load_company_by_id": lambda company_id: DummyCompany(company_id, "Versus", "AA"),
        "resolve_period_from_payload": lambda payload: (date(2026, 3, 1), date(2026, 3, 31)),
        "load_employee_rows": lambda company_id, employee_ids: [
            DummyEmployee(employee_id, f"Colaborador {employee_id}", f"c{employee_id}@empresa.com")
            for employee_id in employee_ids
        ],
        "format_summary_collaborator_selection_label": format_label,
        "load_project_tasks_report": lambda **kwargs: [{"activity_code": f"task-{kwargs['mode']}"}],
        "load_process_instances_report": lambda **kwargs: [{"instance_code": f"proc-{kwargs['mode']}"}],
        "load_meetings_report": lambda **kwargs: [{"meeting_code": f"meet-{kwargs['mode']}"}],
        "merge_report_items": lambda items, unique_key: items,
        "format_my_work_report": lambda **kwargs: (
            f"{kwargs['action']}|{kwargs['company_label']}|{kwargs['payload'].get('colaborador', '-')}"
        ),
    }
    defaults.update(overrides)
    return SummaryWorkflowExecutionHandler(**defaults)


def test_summary_execution_handler_returns_open_report():
    handler = _build_handler()

    result = handler.execute(
        SummaryExecutionRequest(
            payload={
                "_summary_company_id": 9,
                "_summary_employee_ids": [3],
                "_summary_status": "open",
            },
            active_company_id=9,
            user_id=10,
            channel="whatsapp",
        )
    )

    assert result.report_text == "my_work.due_range|empresa AA - Versus|Colaborador 3"


def test_summary_execution_handler_combines_open_and_completed_reports():
    handler = _build_handler()

    result = handler.execute(
        SummaryExecutionRequest(
            payload={
                "_summary_company_id": 9,
                "_summary_employee_ids": [3],
                "_summary_status": "all",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert "STATUS: ABERTAS" in result.report_text
    assert "my_work.due_range|empresa AA - Versus|Colaborador 3" in result.report_text
    assert "STATUS: CONCLUIDAS" in result.report_text
    assert "my_work.completed_range|empresa AA - Versus|Colaborador 3" in result.report_text


def test_summary_execution_handler_blocks_employee_outside_company_scope():
    handler = _build_handler(load_employee_rows=lambda company_id, employee_ids: [])

    result = handler.execute(
        SummaryExecutionRequest(
            payload={
                "_summary_company_id": 9,
                "_summary_employee_ids": [999],
                "_summary_status": "open",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.report_text == "Colaborador selecionado nao pertence a empresa escolhida."
