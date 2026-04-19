import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_title_calculation_service as title_calc_module
from services.financial_title_calculation_service import FinancialTitleCalculationService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, *, first_result=None, all_results=None):
        self._first_result = first_result
        self._all_results = list(all_results or [])
        self.received_limit = None

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.received_limit = value
        return self

    def first(self):
        return self._first_result

    def all(self):
        return self._all_results


def test_list_title_calculation_logs_is_tenant_safe_and_returns_logs(monkeypatch):
    schedule = type(
        "Schedule",
        (),
        {
            "id": 77,
            "company_id": 7,
            "schedule_code": "TIT-077",
            "to_dict": lambda self: {
                "id": self.id,
                "company_id": self.company_id,
                "schedule_code": self.schedule_code,
            },
        },
    )()
    log = type(
        "Log",
        (),
        {
            "id": 501,
            "financial_schedule_id": 77,
            "calculation_date": date(2026, 4, 19),
            "to_dict": lambda self: {
                "id": self.id,
                "financial_schedule_id": self.financial_schedule_id,
                "calculation_date": self.calculation_date.isoformat(),
            },
        },
    )()

    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=schedule)

    log_query = _QueryStub(all_results=[log])

    class _FakeLog:
        id = _Column()
        company_id = _Column()
        financial_schedule_id = _Column()
        calculation_date = _Column()
        query = log_query

    monkeypatch.setattr(title_calc_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(title_calc_module, "FinancialTitleCalculationLog", _FakeLog)
    monkeypatch.setattr(
        title_calc_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids: None,
    )

    result, error = FinancialTitleCalculationService.list_title_calculation_logs(
        company_id=7,
        schedule_id=77,
        allowed_company_ids=[7],
        limit=800,
    )

    assert error is None
    assert result["schedule"]["schedule_code"] == "TIT-077"
    assert result["logs"] == [
        {
            "id": 501,
            "financial_schedule_id": 77,
            "calculation_date": "2026-04-19",
        }
    ]
    assert result["count"] == 1
    assert result["limit"] == 500
    assert log_query.received_limit == 500


def test_list_title_calculation_logs_rejects_company_out_of_scope(monkeypatch):
    monkeypatch.setattr(
        title_calc_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids: "A operação financeira está fora do escopo da empresa autorizada.",
    )

    result, error = FinancialTitleCalculationService.list_title_calculation_logs(
        company_id=8,
        schedule_id=77,
        allowed_company_ids=[7],
    )

    assert result is None
    assert error == "A operação financeira está fora do escopo da empresa autorizada."


def test_list_title_calculation_logs_requires_existing_title(monkeypatch):
    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=None)

    monkeypatch.setattr(title_calc_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(
        title_calc_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids: None,
    )

    result, error = FinancialTitleCalculationService.list_title_calculation_logs(
        company_id=7,
        schedule_id=999,
        allowed_company_ids=[7],
    )

    assert result is None
    assert error == "Título financeiro não encontrado no escopo da empresa."
