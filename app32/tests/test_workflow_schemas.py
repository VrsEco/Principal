from datetime import date
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.schemas import (
    MeetingReferenceInput,
    MeetingScheduleInput,
    ProjectTaskCreateInput,
    SummaryExecutionInput,
)


def test_summary_execution_input_builds_from_legacy_payload():
    execution_input, error = SummaryExecutionInput.build_from_legacy_payload(
        {
            "_summary_company_id": "9",
            "_summary_employee_ids": ["3", 4, "x", 3],
            "_summary_status": "completed",
            "_summary_all_collaborators": True,
            "periodo": "este mes",
        },
        resolve_period_from_payload=lambda payload: (date(2026, 3, 1), date(2026, 3, 31)),
    )

    assert error is None
    assert execution_input is not None
    assert execution_input.selected_company_id == 9
    assert execution_input.employee_ids == [3, 4]
    assert execution_input.status == "completed"
    assert execution_input.all_collaborators is True
    assert execution_input.start_date == date(2026, 3, 1)
    assert execution_input.end_date == date(2026, 3, 31)


def test_project_task_create_input_maps_aliases():
    execution_input, error = ProjectTaskCreateInput.build_from_legacy_payload(
        {
            "project_code": "AA.J.17",
            "titulo": "Configurar dashboards",
            "who": "Fabiano",
            "description": "Criar painéis",
            "priority": "high",
            "notes": "Urgente",
        }
    )

    assert error is None
    assert execution_input is not None
    assert execution_input.project_code == "AA.J.17"
    assert execution_input.task_name == "Configurar dashboards"
    assert execution_input.responsible_name == "Fabiano"
    assert execution_input.description == "Criar painéis"
    assert execution_input.priority == "high"
    assert execution_input.notes == "Urgente"


def test_meeting_schedule_input_splits_lists_and_deduplicates():
    execution_input, error = MeetingScheduleInput.build_from_legacy_payload(
        {
            "titulo": "Reuniao Operacional",
            "data_hora": "20/03/2026 14:30",
            "participantes": "Fabiano, Marcel\nFabiano; Ana",
            "agenda": "Comercial;Financeiro\nComercial",
            "dados": "Sala 2",
        }
    )

    assert error is None
    assert execution_input is not None
    assert execution_input.title == "Reuniao Operacional"
    assert execution_input.datetime_raw == "20/03/2026 14:30"
    assert execution_input.guests == ["Fabiano", "Marcel", "Ana"]
    assert execution_input.agenda_items == ["Comercial", "Financeiro"]
    assert execution_input.notes == "Sala 2"


def test_meeting_reference_input_reads_alias_and_extracts_id():
    execution_input, error = MeetingReferenceInput.build_from_legacy_payload(
        {"codigo_reuniao": "ID 55"}
    )

    assert error is None
    assert execution_input is not None
    assert execution_input.meeting_id == 55


def test_canonical_models_forbid_unknown_fields():
    with pytest.raises(ValidationError):
        ProjectTaskCreateInput(
            project_code="AA.J.17",
            task_name="Configurar dashboards",
            unknown="x",
        )

    with pytest.raises(ValidationError):
        MeetingScheduleInput(
            title="Reuniao Operacional",
            invalid_field="x",
        )

    with pytest.raises(ValidationError):
        SummaryExecutionInput(
            selected_company_id=9,
            employee_ids=[3],
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            extra_field="x",
        )
