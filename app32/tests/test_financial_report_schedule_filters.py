import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_report_service import FinancialReportService


def test_schedule_report_normalize_accepts_default_operational_filters():
    filters, error = FinancialReportService._normalize_filters(
        "schedule_report",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "include_settled": "true",
            "include_partial": "true",
            "include_open": "true",
            "include_bordero": "true",
            "include_payable": "true",
            "include_receivable": "true",
            "show_title_number": "true",
        },
    )

    assert error is None
    assert filters is not None
    assert filters.report_type == "schedule_report"
    assert filters.competence_start.isoformat() == "2026-04-01"
    assert filters.competence_end.isoformat() == "2026-04-30"


def test_schedule_report_normalize_rejects_without_status():
    filters, error = FinancialReportService._normalize_filters(
        "schedule_report",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "include_settled": "false",
            "include_partial": "false",
            "include_open": "false",
            "include_bordero": "false",
            "include_payable": "true",
            "include_receivable": "true",
            "show_title_number": "true",
        },
    )

    assert filters is None
    assert error == "Selecione ao menos um status para o relatório de agendamentos."


def test_schedule_report_normalize_rejects_without_display_columns():
    filters, error = FinancialReportService._normalize_filters(
        "schedule_report",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "include_settled": "true",
            "include_partial": "true",
            "include_open": "true",
            "include_bordero": "true",
            "include_payable": "true",
            "include_receivable": "true",
            "show_title_number": "false",
            "show_installment": "false",
            "show_history": "false",
            "show_counterparty": "false",
            "show_title_amount": "false",
            "show_balance_amount": "false",
            "show_competence_date": "false",
            "show_due_date": "false",
            "show_settlement_date": "false",
        },
    )

    assert filters is None
    assert error == "Selecione ao menos uma coluna para exibir no relatório de agendamentos."
