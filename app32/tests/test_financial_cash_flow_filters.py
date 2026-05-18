import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_report_service as report_module
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


def test_cash_flow_defaults_to_projection_with_financial_correction():
    filters, error = FinancialReportService._normalize_filters(
        "cash_flow",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    )

    assert error is None
    assert filters.projected_values_mode == "with_financial_correction"


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
    sidebar_template = (
        template_path.parent / "partials" / "report_filters_cash_flow_sidebar.html"
    ).read_text(encoding="utf-8")
    combined_template = template + sidebar_template

    assert "Retirar títulos financeiros em aberto do fluxo" in template
    assert "report_filters_cash_flow_sidebar.html" in template
    assert 'cash-flow-filter-form' in template
    assert 'action="/financial/reports/{{ report_definition.slug }}/view"' in template
    assert 'data-filter-action="/financial/reports/{{ report_definition.slug }}"' in template
    assert 'data-apply-filters-only="true"' not in template
    assert 'data-cash-flow-submit-mode="report"' in template
    assert 'formaction="/financial/reports/{{ report_definition.slug }}/view"' in template
    assert 'data-cash-flow-submit-mode="filters"' in sidebar_template
    assert 'formaction="/financial/reports/{{ report_definition.slug }}"' in sidebar_template
    assert 'name="ui_refresh" value="1"' in sidebar_template
    assert "{% set cash_period_start = (filters.get('period_start'" in sidebar_template
    assert "{% set title_filter_movement_nature = (filters.get('title_filter_movement_nature'" in sidebar_template
    assert 'name="enable_title_exclusions"' in template
    assert 'data-cash-flow-process' not in combined_template
    assert 'name="excluded_projected_refs"' in template
    assert '/projected-titles' in template
    assert 'form="cash-flow-filter-form" type="hidden" name="bank_account_ids" value="-1"' in sidebar_template
    assert "Processar filtros" not in sidebar_template
    assert "Aplicar Filtros" in sidebar_template
    assert "Gerar fluxo" not in sidebar_template
    assert "Buscar título financeiro" in sidebar_template
    assert 'name="projected_values_mode" value="with_financial_correction"' in sidebar_template
    assert 'name="projected_values_mode" value="without_financial_correction"' in sidebar_template
    assert 'name="chart_account_ids"' in sidebar_template
    assert 'name="cost_center_ids"' in sidebar_template
    assert 'name="project_ids"' in sidebar_template
    assert 'name="process_ids"' in sidebar_template


def test_cash_flow_filter_javascript_has_submitter_safe_fallback():
    script = (
        Path(__file__).resolve().parents[2]
        / "static"
        / "js"
        / "financial_cash_flow_filters.js"
    ).read_text(encoding="utf-8")

    assert "lastSubmitter" in script
    assert "event.submitter || lastSubmitter" in script
    assert "submitter?.name === 'ui_refresh' ? 'filters' : 'report'" in script
    assert "isSubmitLikeControl(control)" in script
    assert "includeSubmitter: true" in script


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
    assert filters.excluded_projected_refs == ["entry:10", "entry:11"]


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
    assert "projected_amount_label" in template
    assert "Retirado" in template
    assert "cashflow-accounts-layout" in template
    assert "cashflow-accounts-brand" in template
    assert "cashflow-bank-amount" in template
    assert "cashflow-amount" in template
    assert "css_base }}--positive" in template
    assert "css_base }}--negative" in template
    assert "cashflow-title-col--counterparty" in template
    assert "cashflow-title-col--projected" in template


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def isnot(self, other):
        return ("isnot", other)

    def in_(self, other):
        return ("in", list(other))

    def __ge__(self, other):
        return ("ge", other)

    def __le__(self, other):
        return ("le", other)

    def __lt__(self, other):
        return ("lt", other)

    def asc(self):
        return self


class _QueryStub:
    def __init__(self):
        self.filters = []
        self.ordering = []

    def filter(self, *args, **kwargs):
        self.filters.extend(args)
        return self

    def order_by(self, *args, **kwargs):
        self.ordering.extend(args)
        return self


def test_cash_flow_projected_query_includes_titles_without_bank_account_when_accounts_selected(monkeypatch):
    query = _QueryStub()
    entry_model = type(
        "FinancialEntryStub",
        (),
        {
            "company_id": _Column(),
            "deleted_at": _Column(),
            "status": _Column(),
            "due_date": _Column(),
            "bank_account_id": _Column(),
            "id": _Column(),
            "query": query,
        },
    )
    monkeypatch.setattr(report_module, "FinancialEntry", entry_model)
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))

    filters = SimpleNamespace(
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        bank_account_id=None,
        bank_account_ids=[1, 2],
    )

    FinancialReportService._cash_flow_projected_entry_query(9, filters)

    assert ("or", (("in", [1, 2]), ("is", None))) in query.filters


def test_cash_flow_projected_query_with_empty_bank_marker_keeps_only_titles_without_bank_account(monkeypatch):
    query = _QueryStub()
    entry_model = type(
        "FinancialEntryStub",
        (),
        {
            "company_id": _Column(),
            "deleted_at": _Column(),
            "status": _Column(),
            "due_date": _Column(),
            "bank_account_id": _Column(),
            "id": _Column(),
            "query": query,
        },
    )
    monkeypatch.setattr(report_module, "FinancialEntry", entry_model)
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))

    filters = SimpleNamespace(
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        bank_account_id=None,
        bank_account_ids=[-1],
    )

    FinancialReportService._cash_flow_projected_entry_query(9, filters)

    assert ("is", None) in query.filters


def test_cash_flow_projected_query_applies_account_and_center_filters(monkeypatch):
    query = _QueryStub()
    entry_model = type(
        "FinancialEntryStub",
        (),
        {
            "company_id": _Column(),
            "deleted_at": _Column(),
            "status": _Column(),
            "due_date": _Column(),
            "bank_account_id": _Column(),
            "chart_account_id": _Column(),
            "cost_center_id": _Column(),
            "id": _Column(),
            "query": query,
        },
    )
    monkeypatch.setattr(report_module, "FinancialEntry", entry_model)
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))

    filters = SimpleNamespace(
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        bank_account_id=None,
        bank_account_ids=[],
        chart_account_id=None,
        chart_account_ids=[10, 11],
        cost_center_id=None,
        cost_center_ids=[20],
    )

    FinancialReportService._cash_flow_projected_entry_query(9, filters)

    assert ("in", [10, 11]) in query.filters
    assert ("in", [20]) in query.filters


def test_cash_flow_title_preview_includes_schedule_without_generated_entry(monkeypatch):
    schedule = SimpleNamespace(
        id=77,
        schedule_code="AG-000077",
        name="Receita futura",
        description="Receita futura",
        memo=None,
        entry_type="receivable",
        movement_nature="credit",
        status="active",
        competence_date=date(2026, 6, 1),
        start_date=date(2026, 6, 1),
        first_due_date=date(2026, 6, 18),
        next_due_date=date(2026, 6, 18),
        template_amount=Decimal("890.00"),
        bank_account_id=None,
        counterparty_id=1,
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={},
    )

    monkeypatch.setattr(report_module.FinancialReportService, "_cash_flow_projected_entry_query", lambda *args, **kwargs: _QueryStubWithItems([]))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_cash_flow_projected_schedule_query",
        lambda *args, **kwargs: _QueryStubWithItems([schedule]),
    )
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_schedule_projected_balance_snapshot",
        lambda schedule: {
            "principal_amount": Decimal(str(schedule.template_amount)),
            "principal_open": Decimal(str(schedule.template_amount)),
            "principal_corrected_open": Decimal(str(schedule.template_amount)),
        },
    )
    monkeypatch.setattr(report_module.FinancialReportService, "_entry_settlement_totals", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_name_map",
        lambda model, company_id: {1: "Cliente Teste"},
    )
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))
    monkeypatch.setattr(
        report_module,
        "FinancialEntry",
        type(
            "FinancialEntryStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "financial_schedule_id": _Column(),
                "external_reference": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )

    payload, error = FinancialReportService.build_cash_flow_title_preview(
        company_id=9,
        filters={
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "enable_title_exclusions": "true",
            "excluded_projected_refs": ["schedule:77"],
        },
        selection_filters={},
        allowed_company_ids=[9],
    )

    assert error is None
    assert payload["summary"]["count"] == 1
    assert payload["summary"]["selected_count"] == 1
    assert payload["titles"][0]["projection_ref"] == "schedule:77"
    assert payload["titles"][0]["selected"] is True
    assert payload["titles"][0]["due_date"] == "2026-06-18"


def test_cash_flow_build_includes_schedule_titles_when_entries_do_not_exist(monkeypatch):
    receivable_schedule = SimpleNamespace(
        id=44,
        schedule_code="AG-000029",
        name="Teste a receber",
        description="Teste a receber",
        memo=None,
        entry_type="receivable",
        movement_nature="credit",
        status="active",
        competence_date=date(2026, 4, 20),
        start_date=date(2026, 4, 20),
        first_due_date=date(2026, 5, 2),
        next_due_date=date(2026, 5, 2),
        template_amount=Decimal("1250.00"),
        bank_account_id=None,
        counterparty_id=1,
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={},
    )
    payable_schedule = SimpleNamespace(
        id=45,
        schedule_code="AG-000030",
        name="Contas a Pagar 01",
        description="Contas a Pagar 01",
        memo=None,
        entry_type="payable",
        movement_nature="debit",
        status="active",
        competence_date=date(2026, 4, 20),
        start_date=date(2026, 4, 20),
        first_due_date=date(2026, 5, 2),
        next_due_date=date(2026, 5, 2),
        template_amount=Decimal("1050.00"),
        bank_account_id=None,
        counterparty_id=2,
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={},
    )

    monkeypatch.setattr(report_module.FinancialReportService, "_settlement_query", lambda company_id, filters: _QueryStubWithItems([]))
    monkeypatch.setattr(report_module.FinancialReportService, "_cash_flow_projected_entry_query", lambda company_id, filters: _QueryStubWithItems([]))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_cash_flow_projected_schedule_query",
        lambda company_id, filters: _QueryStubWithItems([receivable_schedule, payable_schedule]),
    )
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_schedule_projected_balance_snapshot",
        lambda schedule: {
            "principal_amount": Decimal(str(schedule.template_amount)),
            "principal_open": Decimal(str(schedule.template_amount)),
            "principal_corrected_open": Decimal(str(schedule.template_amount)),
        },
    )
    monkeypatch.setattr(report_module.FinancialReportService, "_entry_settlement_totals", lambda company_id, entry_ids=None: {})
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_name_map",
        lambda model, company_id: {1: "Cliente Teste", 2: "Fornecedor Teste"},
    )
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_overdraft_limit", lambda *args, **kwargs: Decimal("0"))
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_current_balance", lambda **kwargs: Decimal("0"))

    monkeypatch.setattr(
        report_module,
        "FinancialEntry",
        type(
            "FinancialEntryStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "status": _Column(),
                "due_date": _Column(),
                "financial_schedule_id": _Column(),
                "external_reference": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialSettlement",
        type(
            "FinancialSettlementStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "settlement_status": _Column(),
                "settlement_date": _Column(),
                "bank_account_id": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialBankAccount",
        type(
            "FinancialBankAccountStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "is_active": _Column(),
                "code": _Column(),
                "name": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )

    filters = SimpleNamespace(
        report_type="cash_flow",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        bank_account_id=None,
        bank_account_ids=[],
        include_reconciled_only=False,
        include_overdraft=False,
        frequency="daily",
        include_projected=True,
        projected_values_mode="with_financial_correction",
        enable_title_exclusions=False,
        excluded_entry_ids=[],
        excluded_projected_refs=[],
        process_ids=[],
        project_ids=[],
        include_receivable=True,
        include_payable=True,
        include_budget_vs_actual=False,
    )

    result = FinancialReportService._build_cash_flow(9, filters)

    assert result["selected_receivables_totals"]["count"] == 1
    assert result["selected_payables_totals"]["count"] == 1
    assert result["selected_receivables"][0]["id"] == 44
    assert result["selected_payables"][0]["id"] == 45
    assert result["selected_receivables"][0]["counterparty"] == "Cliente Teste"
    assert result["selected_payables"][0]["counterparty"] == "Fornecedor Teste"
    assert result["rows"][1]["entrada"] == "R$ 1.250,00"
    assert result["rows"][1]["saida"] == "R$ 1.050,00"


def test_cash_flow_build_excludes_schedule_without_generated_entry_when_selected(monkeypatch):
    schedule = SimpleNamespace(
        id=88,
        schedule_code="AG-000088",
        name="Despesa futura",
        description="Despesa futura",
        memo=None,
        entry_type="payable",
        movement_nature="debit",
        status="active",
        competence_date=date(2026, 6, 1),
        start_date=date(2026, 6, 1),
        first_due_date=date(2026, 6, 30),
        next_due_date=date(2026, 6, 30),
        template_amount=Decimal("540.00"),
        bank_account_id=None,
        counterparty_id=2,
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={},
    )

    monkeypatch.setattr(report_module.FinancialReportService, "_settlement_query", lambda company_id, filters: _QueryStubWithItems([]))
    monkeypatch.setattr(report_module.FinancialReportService, "_cash_flow_projected_entry_query", lambda company_id, filters: _QueryStubWithItems([]))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_cash_flow_projected_schedule_query",
        lambda company_id, filters: _QueryStubWithItems([schedule]),
    )
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_schedule_projected_balance_snapshot",
        lambda schedule: {
            "principal_amount": Decimal(str(schedule.template_amount)),
            "principal_open": Decimal(str(schedule.template_amount)),
            "principal_corrected_open": Decimal(str(schedule.template_amount)),
        },
    )
    monkeypatch.setattr(report_module.FinancialReportService, "_entry_settlement_totals", lambda company_id, entry_ids=None: {})
    monkeypatch.setattr(report_module, "or_", lambda *args: ("or", args))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_name_map",
        lambda model, company_id: {2: "Fornecedor Teste"},
    )
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_overdraft_limit", lambda *args, **kwargs: Decimal("0"))
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_current_balance", lambda **kwargs: Decimal("0"))
    monkeypatch.setattr(
        report_module,
        "FinancialEntry",
        type(
            "FinancialEntryStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "status": _Column(),
                "due_date": _Column(),
                "financial_schedule_id": _Column(),
                "external_reference": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialSettlement",
        type(
            "FinancialSettlementStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "settlement_status": _Column(),
                "settlement_date": _Column(),
                "bank_account_id": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialBankAccount",
        type(
            "FinancialBankAccountStub",
            (),
            {
                "company_id": _Column(),
                "deleted_at": _Column(),
                "is_active": _Column(),
                "code": _Column(),
                "name": _Column(),
                "id": _Column(),
                "query": _QueryStubWithItems([]),
            },
        ),
    )

    filters = SimpleNamespace(
        report_type="cash_flow",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        bank_account_id=None,
        bank_account_ids=[],
        include_reconciled_only=False,
        include_overdraft=False,
        frequency="daily",
        include_projected=True,
        projected_values_mode="with_financial_correction",
        enable_title_exclusions=True,
        excluded_entry_ids=[],
        excluded_projected_refs=["schedule:88"],
        process_ids=[],
        project_ids=[],
        include_receivable=True,
        include_payable=True,
        include_budget_vs_actual=False,
    )

    result = FinancialReportService._build_cash_flow(9, filters)

    assert result["selected_payables"][0]["projection_ref"] == "schedule:88"
    assert result["selected_payables"][0]["is_excluded"] is True
    assert result["rows"][29]["saida"] == "R$ 0,00"
    assert result["totals"]["excluded_projected_amount"] == 540.0
    assert result["excluded_titles"][0]["projection_ref"] == "schedule:88"


class _QueryStubWithItems(_QueryStub):
    def __init__(self, items):
        super().__init__()
        self._items = list(items)

    def all(self):
        return list(self._items)
