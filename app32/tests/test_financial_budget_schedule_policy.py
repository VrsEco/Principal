import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_budget_schedule_policy as policy_module
from services.financial_budget_schedule_policy import FinancialBudgetSchedulePolicy


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self


class _QueryStub:
    def __init__(self, result=None, all_result=None):
        self._result = result
        self._all_result = list(all_result or [])

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return list(self._all_result)


def test_validate_document_schedule_amount_blocks_when_requested_value_exceeds_document_balance(monkeypatch):
    document = type("Document", (), {"id": 30, "company_id": 9, "document_amount": Decimal("5000.00")})()
    schedules = [
        type("Schedule", (), {"id": 26, "template_amount": Decimal("2500.00")})(),
    ]

    class _FakeDocument:
        query = _QueryStub(document)
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

    class _FakeSchedule:
        query = _QueryStub(all_result=schedules)
        company_id = _Column()
        budget_document_id = _Column()
        deleted_at = _Column()

    monkeypatch.setattr(policy_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(policy_module, "FinancialBudgetDocument", _FakeDocument)
    monkeypatch.setattr(policy_module, "FinancialSchedule", _FakeSchedule)

    error = FinancialBudgetSchedulePolicy.validate_document_schedule_amount(
        company_id=9,
        budget_document_id=30,
        requested_amount=Decimal("3000.00"),
        allowed_company_ids=[9],
    )

    assert error == FinancialBudgetSchedulePolicy.CAPACITY_EXCEEDED_MESSAGE


def test_validate_document_schedule_amount_excludes_current_schedule_on_update(monkeypatch):
    document = type("Document", (), {"id": 30, "company_id": 9, "document_amount": Decimal("5000.00")})()
    schedules = [
        type("Schedule", (), {"id": 26, "template_amount": Decimal("3000.00")})(),
        type("Schedule", (), {"id": 27, "template_amount": Decimal("1500.00")})(),
    ]

    class _FakeDocument:
        query = _QueryStub(document)
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

    class _FakeSchedule:
        query = _QueryStub(all_result=schedules)
        company_id = _Column()
        budget_document_id = _Column()
        deleted_at = _Column()

    monkeypatch.setattr(policy_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(policy_module, "FinancialBudgetDocument", _FakeDocument)
    monkeypatch.setattr(policy_module, "FinancialSchedule", _FakeSchedule)

    error = FinancialBudgetSchedulePolicy.validate_document_schedule_amount(
        company_id=9,
        budget_document_id=30,
        requested_amount=Decimal("3500.00"),
        allowed_company_ids=[9],
        exclude_schedule_id=26,
    )

    assert error is None
