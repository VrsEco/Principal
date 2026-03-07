import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.presenters import (
    build_my_work_report,
    describe_my_work_period,
    resolve_my_work_collaborator_label,
)


def test_describe_my_work_period_handles_relative_windows():
    text = describe_my_work_period(
        action="my_work.due_range",
        start_date=date(2026, 3, 5),
        end_date=date(2026, 3, 19),
        today=date(2026, 3, 5),
        format_date_br=lambda value: value.strftime("%d/%m/%Y"),
    )

    assert text == "vencendo nos proximos 15 dias (05/03/2026 a 19/03/2026)"


def test_resolve_my_work_collaborator_label_falls_back_to_detected_names():
    label = resolve_my_work_collaborator_label(
        payload={},
        tasks=[{"responsible": "Fabiano"}],
        processes=[{"owner": "Marcel"}],
        fallback_name="Gestor",
    )

    assert label == "dos colaboradores Fabiano e Marcel"


def test_build_my_work_report_sanitizes_telegram_and_formats_structure():
    report = build_my_work_report(
        action="my_work.due_range",
        company_label="empresa AA - Versus <Core>",
        tasks=[
            {
                "company_id": 1,
                "company_code": "AA",
                "company_name": "Versus <Core>",
                "project_code": "AA.J.31",
                "project_name": "Workflow & Discovery",
                "activity_code": "AA.J.31.193",
                "title": "Telemetria <Menu>",
                "responsible": "Fabiano & Time",
                "due_date": "2026-03-10",
                "completion_date": "-",
            }
        ],
        processes=[],
        meetings=[],
        start_date=date(2026, 3, 5),
        end_date=date(2026, 3, 19),
        channel="telegram",
        payload={"colaborador": "Fabiano & Time"},
        manager_name="Fabiano",
        reference_date=date(2026, 3, 5),
        format_date_br=lambda value: value.strftime("%d/%m/%Y") if hasattr(value, "strftime") else str(value),
    )

    assert "&lt;Core&gt;" in report
    assert "Fabiano &amp; Time" in report
    assert "AA.J.31.193 - Telemetria &lt;Menu&gt;" in report
    assert "Sem instancias no periodo." in report
