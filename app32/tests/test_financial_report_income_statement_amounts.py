from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_report_service as report_module
from services.financial_report_service import FinancialReportService


class _Column:
    def __eq__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __le__(self, other):
        return True

    def is_(self, other):
        return True

    def in_(self, other):
        return True

    def notin_(self, other):
        return True

    def asc(self):
        return self


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


class _FakeModel:
    company_id = _Column()
    deleted_at = _Column()
    status = _Column()
    chart_account_id = _Column()
    cost_center_id = _Column()
    entry_type = _Column()
    competence_date = _Column()
    external_reference = _Column()
    financial_schedule_id = _Column()
    financial_entry_id = _Column()
    settlement_status = _Column()
    id = _Column()
    code = _Column()
    name = _Column()

    def __init__(self, rows):
        self.query = _Query(rows)


def _install_income_statement_fakes(
    monkeypatch,
    *,
    schedules,
    entries,
    settlements,
    accounts=None,
):
    accounts = accounts or [
        SimpleNamespace(id=10, parent_id=None, code="4", name="Receitas", accepts_posting=False),
        SimpleNamespace(id=11, parent_id=10, code="4.01.001", name="Receita teste", accepts_posting=True),
        SimpleNamespace(id=12, parent_id=10, code="4.02.001", name="Correção financeira", accepts_posting=True),
        SimpleNamespace(id=13, parent_id=10, code="4.03.001", name="Descontos concedidos", accepts_posting=True),
    ]
    monkeypatch.setattr(report_module, "FinancialChartAccount", _FakeModel(accounts))
    monkeypatch.setattr(report_module, "FinancialSchedule", _FakeModel(schedules))
    monkeypatch.setattr(report_module, "FinancialEntry", _FakeModel(entries))
    monkeypatch.setattr(report_module, "FinancialSettlement", _FakeModel(settlements))
    monkeypatch.setattr(FinancialReportService, "_name_map", staticmethod(lambda model, company_id: {}))


def _income_statement_filters():
    filters, error = FinancialReportService._normalize_filters(
        "income_statement",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_receivable": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    return filters


def test_income_statement_uses_financial_title_dates_and_settlement_date(monkeypatch):
    schedule = SimpleNamespace(
        id=34,
        company_id=7,
        status="active",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 17),
        start_date=date(2026, 4, 17),
        first_due_date=date(2026, 5, 17),
        next_due_date=date(2026, 5, 17),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={"discount_amount_override": "10"},
    )
    entry = SimpleNamespace(
        id=120,
        external_reference="financial_schedule:34",
        financial_schedule_id=34,
        original_amount=Decimal("100"),
        status="posted",
        movement_nature="credit",
        entry_type="receivable",
        competence_date=date(2026, 5, 17),
        due_date=date(2026, 5, 17),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    settlement = SimpleNamespace(
        financial_entry_id=120,
        settlement_date=date(2026, 4, 19),
        principal_amount=Decimal("30"),
        net_amount=Decimal("30"),
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[entry], settlements=[settlement])

    payload = FinancialReportService._build_income_statement(7, _income_statement_filters())

    assert payload["totals"]["competence"] == 100.0
    assert payload["totals"]["due"] == 0.0
    assert payload["totals"]["liquidation"] == 30.0


def test_income_statement_liquidation_splits_principal_correction_and_discount(monkeypatch):
    schedule = SimpleNamespace(
        id=45,
        company_id=7,
        status="active",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 10),
        start_date=date(2026, 4, 10),
        first_due_date=date(2026, 4, 20),
        next_due_date=date(2026, 4, 20),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    entry = SimpleNamespace(
        id=145,
        company_id=7,
        external_reference="financial_schedule:45",
        financial_schedule_id=45,
        original_amount=Decimal("100"),
        status="settled",
        movement_nature="credit",
        entry_type="receivable",
        competence_date=date(2026, 4, 10),
        due_date=date(2026, 4, 20),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    settlement = SimpleNamespace(
        financial_entry_id=145,
        settlement_date=date(2026, 4, 21),
        principal_amount=Decimal("100"),
        net_amount=Decimal("115"),
        metadata_json={
            "settlement_allocation_breakdown": {
                "principal": {"items": [{"chart_account_id": 11, "settled_allocated_amount": 100}]},
                "financial_correction": {"items": [{"chart_account_id": 12, "settled_allocated_amount": 20}]},
                "discount": {"items": [{"chart_account_id": 13, "settled_allocated_amount": 5}]},
            }
        },
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[entry], settlements=[settlement])

    payload = FinancialReportService._build_income_statement(7, _income_statement_filters())
    rows_by_code = {row["codigo"]: row for row in payload["rows"]}

    assert payload["totals"]["competence"] == 115.0
    assert payload["totals"]["due"] == 115.0
    assert payload["totals"]["liquidation"] == 115.0
    assert rows_by_code["4.01.001"]["competencia"] == "R$ 100,00"
    assert rows_by_code["4.01.001"]["vencimento"] == "R$ 100,00"
    assert rows_by_code["4.02.001"]["competencia"] == "R$ 20,00"
    assert rows_by_code["4.02.001"]["vencimento"] == "R$ 20,00"
    assert rows_by_code["4.03.001"]["competencia"] == "R$ -5,00"
    assert rows_by_code["4.03.001"]["vencimento"] == "R$ -5,00"
    assert rows_by_code["4.01.001"]["liquidacao"] == "R$ 100,00"
    assert rows_by_code["4.02.001"]["liquidacao"] == "R$ 20,00"
    assert rows_by_code["4.03.001"]["liquidacao"] == "R$ -5,00"


def test_income_statement_ignores_cancelled_financial_titles(monkeypatch):
    schedule = SimpleNamespace(
        id=35,
        company_id=7,
        status="cancelled",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 17),
        start_date=date(2026, 4, 17),
        first_due_date=date(2026, 4, 25),
        next_due_date=date(2026, 4, 25),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[], settlements=[])

    payload = FinancialReportService._build_income_statement(7, _income_statement_filters())

    assert payload["totals"]["competence"] == 0.0
    assert payload["totals"]["due"] == 0.0
    assert payload["totals"]["liquidation"] == 0.0


def test_income_statement_01_hides_summary_cards_general_info_and_status_columns(monkeypatch):
    schedule = SimpleNamespace(
        id=36,
        company_id=7,
        status="active",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 10),
        start_date=date(2026, 4, 10),
        first_due_date=date(2026, 4, 20),
        next_due_date=date(2026, 4, 20),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[], settlements=[])

    payload = FinancialReportService._build_income_statement(7, _income_statement_filters())

    assert payload["summary_cards"] == []
    assert payload["general_info"] == []
    assert payload["show_status_columns"] is False


def test_income_statement_02_keeps_summary_cards_general_info_and_status_columns(monkeypatch):
    schedule = SimpleNamespace(
        id=37,
        company_id=7,
        status="active",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 10),
        start_date=date(2026, 4, 10),
        first_due_date=date(2026, 4, 20),
        next_due_date=date(2026, 4, 20),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[], settlements=[])
    filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_receivable": "true",
            "include_payable": "true",
        },
    )
    assert error is None

    payload = FinancialReportService._build_income_statement_2(7, filters)

    assert len(payload["summary_cards"]) == 4
    assert len(payload["general_info"]) >= 1
    assert payload["show_status_columns"] is True


def test_income_statement_02_compiles_due_and_settlement_independently_from_competence(monkeypatch):
    entry = SimpleNamespace(
        id=220,
        company_id=7,
        external_reference="",
        financial_schedule_id=None,
        original_amount=Decimal("150"),
        status="posted",
        movement_nature="credit",
        entry_type="receivable",
        competence_date=date(2026, 3, 31),
        due_date=date(2026, 4, 12),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    settlement = SimpleNamespace(
        financial_entry_id=220,
        settlement_date=date(2026, 4, 18),
        principal_amount=Decimal("150"),
        net_amount=Decimal("150"),
    )
    _install_income_statement_fakes(monkeypatch, schedules=[], entries=[entry], settlements=[settlement])
    filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "due_start": "2026-04-01",
            "due_end": "2026-04-30",
            "settlement_start": "2026-04-01",
            "settlement_end": "2026-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_receivable": "true",
            "include_payable": "true",
        },
    )
    assert error is None

    payload = FinancialReportService._build_income_statement_2(7, filters)

    assert payload["totals"]["competence"] == 0.0
    assert payload["totals"]["due"] == 150.0
    assert payload["totals"]["liquidation"] == 150.0


def test_income_statement_reports_keep_totals_consistent_between_dre01_and_dre02(monkeypatch):
    schedule = SimpleNamespace(
        id=44,
        company_id=7,
        status="active",
        entry_type="receivable",
        movement_nature="credit",
        competence_date=date(2026, 4, 5),
        start_date=date(2026, 4, 5),
        first_due_date=date(2026, 4, 12),
        next_due_date=date(2026, 4, 12),
        template_amount=Decimal("100"),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    entry = SimpleNamespace(
        id=144,
        company_id=7,
        external_reference="financial_schedule:44",
        financial_schedule_id=44,
        original_amount=Decimal("100"),
        status="posted",
        movement_nature="credit",
        entry_type="receivable",
        competence_date=date(2026, 4, 5),
        due_date=date(2026, 4, 12),
        chart_account_id=11,
        cost_center_id=None,
        metadata_json={},
    )
    settlement = SimpleNamespace(
        financial_entry_id=144,
        settlement_date=date(2026, 4, 18),
        principal_amount=Decimal("100"),
        net_amount=Decimal("100"),
    )
    _install_income_statement_fakes(monkeypatch, schedules=[schedule], entries=[entry], settlements=[settlement])

    dre01 = FinancialReportService._build_income_statement(7, _income_statement_filters())
    dre02_filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "due_start": "2026-04-01",
            "due_end": "2026-04-30",
            "settlement_start": "2026-04-01",
            "settlement_end": "2026-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_receivable": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    dre02 = FinancialReportService._build_income_statement_2(7, dre02_filters)

    assert dre01["totals"]["competence"] == dre02["totals"]["competence"] == 100.0
    assert dre01["totals"]["due"] == dre02["totals"]["due"] == 100.0
    assert dre01["totals"]["liquidation"] == dre02["totals"]["liquidation"] == 100.0


def test_income_statement_payable_schedule_keeps_principal_and_correction_separate(monkeypatch):
    accounts = [
        SimpleNamespace(id=15, parent_id=None, code="5", name="Despesas", accepts_posting=False),
        SimpleNamespace(id=16, parent_id=15, code="5.2", name="Despesas operacionais", accepts_posting=False),
        SimpleNamespace(id=17, parent_id=16, code="5.2.01", name="Despesas administrativas", accepts_posting=False),
        SimpleNamespace(id=19, parent_id=17, code="5.2.01.001", name="Aluguel", accepts_posting=True),
        SimpleNamespace(id=21, parent_id=17, code="5.2.01.003", name="Multas e Juros por Atrazo no Pagamento", accepts_posting=True),
    ]
    schedule = SimpleNamespace(
        id=42,
        company_id=9,
        status="active",
        entry_type="payable",
        movement_nature="debit",
        competence_date=date(2020, 1, 31),
        start_date=date(2020, 1, 31),
        first_due_date=date(2020, 2, 28),
        next_due_date=date(2020, 2, 28),
        template_amount=Decimal("7500"),
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={},
    )
    entry = SimpleNamespace(
        id=21,
        company_id=9,
        external_reference="financial_schedule:42",
        financial_schedule_id=42,
        original_amount=Decimal("13134.75"),
        status="partially_settled",
        movement_nature="debit",
        entry_type="payable",
        competence_date=date(2020, 1, 31),
        due_date=date(2020, 2, 28),
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={"schedule_template_amount": 7500.0},
    )
    settlement = SimpleNamespace(
        financial_entry_id=21,
        settlement_date=date(2020, 4, 21),
        principal_amount=Decimal("2000"),
        net_amount=Decimal("2100"),
        metadata_json={
            "settlement_allocation_breakdown": {
                "principal": {
                    "items": [
                        {
                            "chart_account_id": 19,
                            "cost_center_id": 2,
                            "settled_allocated_amount": 2000.0,
                        }
                    ]
                },
                "financial_correction": {
                    "items": [
                        {
                            "chart_account_id": 21,
                            "cost_center_id": 2,
                            "settled_allocated_amount": 100.0,
                            "competence_date": "2020-04-21",
                            "due_date": "2020-04-21",
                        }
                    ]
                },
            }
        },
    )
    _install_income_statement_fakes(
        monkeypatch,
        schedules=[schedule],
        entries=[entry],
        settlements=[settlement],
        accounts=accounts,
    )

    january_filters, error = FinancialReportService._normalize_filters(
        "income_statement",
        {
            "period_start": "2020-01-01",
            "period_end": "2020-01-31",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    january_payload = FinancialReportService._build_income_statement(9, january_filters)
    january_rows = {row["codigo"]: row for row in january_payload["rows"]}
    assert january_rows["5.2.01.001"]["competencia"] == "R$ -7.500,00"
    assert january_rows["5.2.01.001"]["vencimento"] == "R$ 0,00"
    assert january_rows["5.2.01.001"]["liquidacao"] == "R$ 0,00"

    february_filters, error = FinancialReportService._normalize_filters(
        "income_statement",
        {
            "period_start": "2020-02-01",
            "period_end": "2020-02-29",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    february_payload = FinancialReportService._build_income_statement(9, february_filters)
    february_rows = {row["codigo"]: row for row in february_payload["rows"]}
    assert february_rows["5.2.01.001"]["competencia"] == "R$ 0,00"
    assert february_rows["5.2.01.001"]["vencimento"] == "R$ -7.500,00"
    assert february_rows["5.2.01.001"]["liquidacao"] == "R$ 0,00"

    april_filters, error = FinancialReportService._normalize_filters(
        "income_statement",
        {
            "period_start": "2020-04-01",
            "period_end": "2020-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    april_payload = FinancialReportService._build_income_statement(9, april_filters)
    april_rows = {row["codigo"]: row for row in april_payload["rows"]}
    assert april_rows["5.2.01.001"]["competencia"] == "R$ 0,00"
    assert april_rows["5.2.01.001"]["vencimento"] == "R$ 0,00"
    assert april_rows["5.2.01.001"]["liquidacao"] == "R$ -2.000,00"
    assert april_rows["5.2.01.003"]["competencia"] == "R$ -100,00"
    assert april_rows["5.2.01.003"]["vencimento"] == "R$ -100,00"
    assert april_rows["5.2.01.003"]["liquidacao"] == "R$ -100,00"


def test_income_statement_02_correction_uses_settlement_window_for_competence_and_due(monkeypatch):
    accounts = [
        SimpleNamespace(id=15, parent_id=None, code="5", name="Despesas", accepts_posting=False),
        SimpleNamespace(id=16, parent_id=15, code="5.2", name="Despesas operacionais", accepts_posting=False),
        SimpleNamespace(id=17, parent_id=16, code="5.2.01", name="Despesas administrativas", accepts_posting=False),
        SimpleNamespace(id=19, parent_id=17, code="5.2.01.001", name="Aluguel", accepts_posting=True),
        SimpleNamespace(id=21, parent_id=17, code="5.2.01.003", name="Multas e Juros por Atrazo no Pagamento", accepts_posting=True),
    ]
    entry = SimpleNamespace(
        id=21,
        company_id=9,
        external_reference="financial_schedule:42",
        financial_schedule_id=42,
        original_amount=Decimal("13134.75"),
        status="partially_settled",
        movement_nature="debit",
        entry_type="payable",
        competence_date=date(2020, 1, 31),
        due_date=date(2020, 2, 28),
        chart_account_id=19,
        cost_center_id=2,
        metadata_json={"schedule_template_amount": 7500.0},
    )
    settlement = SimpleNamespace(
        financial_entry_id=21,
        settlement_date=date(2020, 4, 21),
        principal_amount=Decimal("2000"),
        net_amount=Decimal("2100"),
        metadata_json={
            "settlement_allocation_breakdown": {
                "principal": {
                    "items": [
                        {
                            "chart_account_id": 19,
                            "cost_center_id": 2,
                            "settled_allocated_amount": 2000.0,
                        }
                    ]
                },
                "financial_correction": {
                    "items": [
                        {
                            "chart_account_id": 21,
                            "cost_center_id": 2,
                            "settled_allocated_amount": 100.0,
                            "competence_date": "2020-04-21",
                            "due_date": "2020-04-21",
                        }
                    ]
                },
            }
        },
    )
    _install_income_statement_fakes(
        monkeypatch,
        schedules=[],
        entries=[entry],
        settlements=[settlement],
        accounts=accounts,
    )

    split_filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "competence_start": "2020-01-01",
            "competence_end": "2020-01-31",
            "due_start": "2020-02-01",
            "due_end": "2020-02-29",
            "settlement_start": "2020-04-01",
            "settlement_end": "2020-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    split_payload = FinancialReportService._build_income_statement_2(9, split_filters)
    split_rows = {row["codigo"]: row for row in split_payload["rows"]}
    assert split_rows["5.2.01.001"]["competencia"] == "R$ -7.500,00"
    assert split_rows["5.2.01.001"]["vencimento"] == "R$ -7.500,00"
    assert split_rows["5.2.01.001"]["liquidacao"] == "R$ -2.000,00"
    assert split_rows["5.2.01.003"]["competencia"] == "R$ 0,00"
    assert split_rows["5.2.01.003"]["vencimento"] == "R$ 0,00"
    assert split_rows["5.2.01.003"]["liquidacao"] == "R$ -100,00"

    april_filters, error = FinancialReportService._normalize_filters(
        "income_statement_2",
        {
            "competence_start": "2020-04-01",
            "competence_end": "2020-04-30",
            "due_start": "2020-04-01",
            "due_end": "2020-04-30",
            "settlement_start": "2020-04-01",
            "settlement_end": "2020-04-30",
            "include_open": "true",
            "include_partial": "true",
            "include_settled": "true",
            "include_payable": "true",
        },
    )
    assert error is None
    april_payload = FinancialReportService._build_income_statement_2(9, april_filters)
    april_rows = {row["codigo"]: row for row in april_payload["rows"]}
    assert april_rows["5.2.01.001"]["competencia"] == "R$ 0,00"
    assert april_rows["5.2.01.001"]["vencimento"] == "R$ 0,00"
    assert april_rows["5.2.01.001"]["liquidacao"] == "R$ -2.000,00"
    assert april_rows["5.2.01.003"]["competencia"] == "R$ -100,00"
    assert april_rows["5.2.01.003"]["vencimento"] == "R$ -100,00"
    assert april_rows["5.2.01.003"]["liquidacao"] == "R$ -100,00"
