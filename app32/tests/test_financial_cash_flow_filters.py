import os
import sys
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

    assert "Retirar títulos financeiros em aberto" in template
    assert 'name="bank_account_ids" value="-1"' in template
    assert "Desmarque contas para retirar seus títulos financeiros" in template


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
