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
            "show_correction_amount": "false",
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


def test_schedule_report_normalize_accepts_correction_sort_field():
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
            "show_correction_amount": "true",
            "order_by": "correction_amount",
        },
    )

    assert error is None
    assert filters.order_by == "correction_amount"


def test_schedule_report_templates_expose_correction_and_corrected_balance_copy():
    page = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_schedule_page.html").read_text(encoding="utf-8")
    sidebar = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_schedule_sidebar.html").read_text(encoding="utf-8")
    filters_page = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\report_filters.html").read_text(encoding="utf-8")
    assert "Saldo Principal Corrigido" in sidebar
    assert "Valor da Correção" in sidebar
    assert "Saldo Principal Corrigido" in filters_page
    assert "field-correction-amount" in Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")


def test_schedule_form_separates_discount_configuration_from_realized_discount_summary():
    schedules_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")
    schedules_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")
    assert "Desconto Configurado" in schedules_template
    assert "Descontos Realizados / Baixados" in schedules_template
    assert "field-discount-configured" in schedules_template
    assert "discounts_applied" in schedules_js
    assert "Correções realizadas / baixadas" in schedules_js


def test_calculation_memory_ui_hides_deleted_events_and_uses_refined_copy():
    schedules_js = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")
    assert "eventType !== 'settlement_deleted'" in schedules_js
    assert "Correções e descontos ainda em aberto" in schedules_js
    assert "Desconto baixado" in schedules_js


def test_schedule_template_loads_canonical_financial_schedules_asset():
    schedules_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")
    assert "js/financial_schedules.js" in schedules_template
    assert "financial_schedules_20260420m.js" not in schedules_template
