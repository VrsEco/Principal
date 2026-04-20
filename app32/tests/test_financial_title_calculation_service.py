import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_title_calculation_service as calc_module
from services.financial_title_calculation_service import FinancialTitleCalculationService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, first_result=None, all_result=None):
        self._first_result = first_result
        self._all_result = list(all_result or [])

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return list(self._all_result)


def test_list_title_calculation_logs_exposes_memory_timeline(monkeypatch):
    title = type("Schedule", (), {"id": 77, "company_id": 7, "schedule_code": "TIT-077", "to_dict": lambda self: {"id": 77, "company_id": 7, "schedule_code": "TIT-077"}})()
    log = type(
        "Log",
        (),
        {
            "to_dict": lambda self: {
                "id": 1,
                "financial_schedule_id": 77,
                "calculation_date": date(2026, 4, 20).isoformat(),
                "snapshot_json": {
                    "contract_version": "financial_title_memory_v2",
                    "before": {"principal_open": 100.0, "total_open": 120.0},
                    "current": {"principal_settled": 50.0, "gross_amount": 55.0},
                    "after": {"principal_open": 50.0, "total_open": 65.0},
                },
                "metadata_json": {
                    "ledger_version": "financial_title_memory_v2",
                    "actor": {"user_id": 19, "user_name": "Fabiano Diretor", "agent": "app32"},
                    "evidence": {"settlement_code": "LIQ-000123", "attachments_count": 1},
                    "component_summary": {"count": 2, "gross_amount": 55.0},
                    "tenant_scope": {"company_id": 7, "financial_schedule_id": 77, "scope_consistent": True},
                },
            }
        },
    )()

    monkeypatch.setattr(
        calc_module,
        "FinancialSchedule",
        type(
            "ScheduleModel",
            (),
            {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "query": _QueryStub(first_result=title)},
        ),
    )
    monkeypatch.setattr(
        calc_module,
        "FinancialTitleCalculationLog",
        type(
            "LogModel",
            (),
            {"company_id": _Column(), "financial_schedule_id": _Column(), "calculation_date": _Column(), "id": _Column(), "query": _QueryStub(all_result=[log])},
        ),
    )
    monkeypatch.setattr(calc_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)

    result, error = FinancialTitleCalculationService.list_title_calculation_logs(
        company_id=7,
        schedule_id=77,
        allowed_company_ids=[7],
        limit=10,
    )

    assert error is None
    assert result["count"] == 1
    assert result["logs"][0]["memory_contract_version"] == "financial_title_memory_v2"
    assert result["logs"][0]["memory_timeline"]["before"]["principal_open"] == 100.0
    assert result["logs"][0]["memory_timeline"]["current"]["gross_amount"] == 55.0
    assert result["logs"][0]["memory_timeline"]["after"]["total_open"] == 65.0
    assert result["logs"][0]["actor"]["user_name"] == "Fabiano Diretor"
    assert result["logs"][0]["evidence"]["settlement_code"] == "LIQ-000123"
    assert result["logs"][0]["component_summary"]["count"] == 2
    assert result["logs"][0]["tenant_scope"]["company_id"] == 7
    assert result["logs"][0]["tenant_scope"]["scope_consistent"] is True


def test_list_title_calculation_logs_blocks_cross_tenant_scope(monkeypatch):
    monkeypatch.setattr(calc_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: "Acesso negado ao escopo da empresa.")

    result, error = FinancialTitleCalculationService.list_title_calculation_logs(
        company_id=7,
        schedule_id=77,
        allowed_company_ids=[9],
        limit=10,
    )

    assert result is None
    assert error == "Acesso negado ao escopo da empresa."
