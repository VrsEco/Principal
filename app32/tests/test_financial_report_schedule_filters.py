import os
import sys
from pathlib import Path

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
    assert error == "Selecione ao menos um status para o relatório de títulos financeiros."


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
    assert error == "Selecione ao menos uma coluna para exibir no relatório de títulos financeiros."


def test_income_statement_normalize_forces_fixed_identification_and_sorting():
    filters, error = FinancialReportService._normalize_filters(
        "income_statement",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "include_settled": "true",
            "include_open": "true",
            "include_payable": "true",
            "include_receivable": "true",
            "show_code": "false",
            "show_description": "false",
            "order_by": "description",
            "order_direction": "desc",
        },
    )

    assert error is None
    assert filters is not None
    assert filters.show_code is True
    assert filters.show_description is True
    assert filters.order_by == "code"
    assert filters.order_direction == "asc"


def test_income_statement_resolve_roots_promotes_nodes_with_missing_parent():
    root_ids = FinancialReportService._resolve_income_statement_root_ids(
        {
            20: {"codigo": "5.02", "descricao": "Despesas", "parent_id": 10},
            30: {"codigo": "5.03", "descricao": "Operacionais", "parent_id": None},
        }
    )

    assert root_ids == [20, 30]


def test_income_statement_sort_roots_keeps_code_order():
    root_ids = FinancialReportService._sort_income_statement_account_ids(
        [2, 1],
        {
            1: {"codigo": "4.01", "descricao": "Receitas"},
            2: {"codigo": "5.01", "descricao": "Custos"},
        },
    )

    assert root_ids == [1, 2]


def test_income_statement_2_normalize_forces_fixed_identification_and_sorting():
    filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "include_settled": "true",
            "include_open": "true",
            "include_payable": "true",
            "include_receivable": "true",
            "show_code": "false",
            "show_description": "false",
            "order_by": "description",
            "order_direction": "desc",
        },
    )

    assert error is None
    assert filters is not None
    assert filters.show_code is True
    assert filters.show_description is True
    assert filters.order_by == "code"
    assert filters.order_direction == "asc"


def test_schedule_report_templates_use_titulos_financeiros_copy():
    page = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_schedule_page.html").read_text(encoding="utf-8")
    sidebar = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_schedule_sidebar.html").read_text(encoding="utf-8")
    assert "Abrir títulos financeiros" in page
    assert "relatório de títulos financeiros" in sidebar
