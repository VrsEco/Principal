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


def _install_income_statement_fakes(monkeypatch, *, schedules, entries, settlements):
    accounts = [
        SimpleNamespace(id=10, parent_id=None, code="4", name="Receitas", accepts_posting=False),
        SimpleNamespace(id=11, parent_id=10, code="4.01.001", name="Receita teste", accepts_posting=True),
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

    assert payload["totals"]["competence"] == 90.0
    assert payload["totals"]["due"] == 0.0
    assert payload["totals"]["liquidation"] == 30.0


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
