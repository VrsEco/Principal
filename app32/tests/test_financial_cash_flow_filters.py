import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_dashboard_analytics import FinancialDashboardAnalytics
from services.financial_report_service import FinancialReportService


def test_cash_flow_includes_open_titles_by_default():
    filters, error = FinancialReportService._normalize_filters(
        "cash_flow",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )

    assert error is None
    assert filters.include_projected is True


def test_cash_flow_allows_filter_to_remove_open_titles():
    filters, error = FinancialReportService._normalize_filters(
        "cash_flow",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "include_projected": "false",
        },
    )

    assert error is None
    assert filters.include_projected is False


def test_cash_flow_bank_account_empty_marker_is_preserved_only_when_alone():
    assert FinancialReportService._selected_ids(
        None,
        [-1],
        preserve_empty_marker=True,
    ) == [-1]
    assert FinancialReportService._selected_ids(
        None,
        [-1, 7, 8],
        preserve_empty_marker=True,
    ) == [7, 8]
    assert FinancialReportService._selected_ids(None, [-1]) == []


def test_overdraft_limit_empty_bank_selection_short_circuits_without_query():
    assert FinancialDashboardAnalytics.calculate_overdraft_limit(9, bank_account_ids=[]) == Decimal("0")


def test_cash_flow_filter_template_uses_exclusion_language():
    template_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "financial"
        / "report_filters.html"
    )
    template = template_path.read_text(encoding="utf-8")

    assert "Retirar títulos financeiros do fluxo" in template
    assert 'name="enable_title_exclusions"' in template
    assert 'data-cash-flow-process' in template
    assert 'name="excluded_entry_ids"' in template
    assert '/projected-titles' in template
    assert 'name="bank_account_ids" value="-1"' in template
    assert "Processar filtros" in template


def test_cash_flow_filters_accept_manual_title_exclusions():
    filters, error = FinancialReportService._normalize_filters(
        "cash_flow",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "enable_title_exclusions": "true",
            "excluded_entry_ids": ["10", "11"],
        },
    )

    assert error is None
    assert filters.enable_title_exclusions is True
    assert filters.excluded_entry_ids == [10, 11]


def test_bank_account_catalog_template_exposes_overdraft_limit_field():
    template_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "financial"
        / "catalog_detail.html"
    )
    template = template_path.read_text(encoding="utf-8")

    assert "Limite da conta (conta garantida / cheque especial)" in template
    assert "overdraft_limit: normalizeValue('overdraft_limit'" in template


def test_cash_flow_period_buckets_weekly_cover_full_selected_window():
    buckets = FinancialReportService._cash_flow_period_buckets(
        date(2023, 12, 1),
        date(2023, 12, 31),
        "weekly",
    )

    assert [
        (bucket["label"], bucket["start"].isoformat(), bucket["end"].isoformat())
        for bucket in buckets
    ] == [
        ("Semana 1", "2023-12-01", "2023-12-07"),
        ("Semana 2", "2023-12-08", "2023-12-14"),
        ("Semana 3", "2023-12-15", "2023-12-21"),
        ("Semana 4", "2023-12-22", "2023-12-28"),
        ("Semana 5", "2023-12-29", "2023-12-31"),
    ]


def test_cash_flow_view_template_uses_dedicated_partial_and_styles():
    template_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "financial"
        / "report_view.html"
    )
    template = template_path.read_text(encoding="utf-8")

    assert "report.report_type == 'cash_flow'" in template
    assert "report_view_cash_flow.html" in template
    assert "financial_cash_flow_report.css" in template


def test_cash_flow_report_partial_contains_expected_sections():
    partial_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "modules"
        / "financial"
        / "partials"
        / "report_view_cash_flow.html"
    )
    template = partial_path.read_text(encoding="utf-8")

    assert "Contas Correntes" in template
    assert "Fluxo de Caixa" in template
    assert "Contas a Receber Selecionadas" in template
    assert "Contas a Pagar Selecionadas" in template
    assert "Retirado" in template
