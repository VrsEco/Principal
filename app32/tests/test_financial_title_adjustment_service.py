import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_title_adjustment_service as adjustment_module
from services.financial_title_adjustment_service import FinancialTitleAdjustmentService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def in_(self, other):
        return ("in", other)


class _QueryStub:
    def __init__(self, first_result=None):
        self._first_result = first_result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result


class _Schedule:
    id = 34
    company_id = 7
    schedule_code = "TIT-034"
    status = "active"
    movement_nature = "debit"
    template_amount = Decimal("1000.00")
    first_due_date = date(2026, 4, 10)
    next_due_date = date(2026, 4, 10)
    start_date = date(2026, 4, 1)
    metadata_json = {"correction_index_id": 9, "discount_amount_override": "30.00"}
    chart_account_id = None
    cost_center_id = None
    budget_document_id = None
    activity_id = None
    process_instance_id = None
    routine_id = None


def test_simulate_for_schedule_splits_interest_fine_and_discount(monkeypatch):
    correction_rule = type("CorrectionRule", (), {
        "id": 9,
        "code": "MORA",
        "name": "Mora padrão",
        "metadata_json": {
            "interest_rate": "1",
            "interest_period": "daily",
            "penalty_rate": "5",
            "penalty_limit_rate": "2",
        },
    })()

    monkeypatch.setattr(
        adjustment_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {"principal_open": 800.0},
    )
    monkeypatch.setattr(
        adjustment_module,
        "FinancialCorrectionIndex",
        type("CorrectionIndexModel", (), {
            "id": _Column(),
            "company_id": _Column(),
            "deleted_at": _Column(),
            "is_active": _Column(),
            "query": _QueryStub(first_result=correction_rule),
        }),
    )
    monkeypatch.setattr(
        adjustment_module,
        "FinancialDiscountRule",
        type("DiscountRuleModel", (), {
            "id": _Column(),
            "company_id": _Column(),
            "deleted_at": _Column(),
            "is_active": _Column(),
            "query": _QueryStub(first_result=None),
        }),
    )

    result = FinancialTitleAdjustmentService.simulate_for_schedule(
        schedule=_Schedule(),
        reference_date=date(2026, 4, 15),
    )

    assert result["base_amount"] == 800.0
    assert result["totals"]["interest"] == 40.0
    assert result["totals"]["fine"] == 16.0
    assert result["totals"]["discount"] == 30.0
    assert result["totals"]["positive_adjustments"] == 56.0
    assert result["totals"]["net_adjustments"] == 26.0
    assert [item["adjustment_type"] for item in result["adjustments"]] == ["interest", "fine", "discount"]
    assert result["adjustments"][0]["competence_date"] == "2026-04-15"
    assert result["adjustments"][0]["due_date_reference"] == "2026-04-10"


def test_simulate_title_adjustments_rejects_cross_company_scope():
    result, error = FinancialTitleAdjustmentService.simulate_title_adjustments(
        company_id=7,
        schedule_id=34,
        allowed_company_ids=[8],
        reference_date=date(2026, 4, 15),
    )

    assert result is None
    assert error == "A operação financeira está fora do escopo da empresa autorizada."


def test_materialize_title_adjustments_persists_generated_adjustments(monkeypatch):
    captured = {"added": []}

    class _FakeScheduleModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=_Schedule())

    class _FakeAdjustment:
        company_id = _Column()
        financial_schedule_id = _Column()
        adjustment_type = _Column()
        calculation_date = _Column()
        deleted_at = _Column()
        status = _Column()
        query = _QueryStub(first_result=None)

        def __init__(self, **kwargs):
            self.id = 901
            self.__dict__.update(kwargs)
            captured.setdefault("adjustment_kwargs", []).append(kwargs)

        def to_dict(self):
            return {
                "id": self.id,
                "adjustment_type": self.adjustment_type,
                "generated_amount": float(self.generated_amount),
            }

    monkeypatch.setattr(adjustment_module, "FinancialSchedule", _FakeScheduleModel)
    monkeypatch.setattr(adjustment_module, "FinancialTitleAdjustment", _FakeAdjustment)
    monkeypatch.setattr(
        adjustment_module.FinancialTitleAdjustmentService,
        "simulate_for_schedule",
        lambda **kwargs: {
            "financial_schedule_id": 34,
            "company_id": 7,
            "base_amount": 800.0,
            "adjustments": [
                {
                    "adjustment_type": "interest",
                    "status": "open",
                    "calculation_date": "2026-04-15",
                    "competence_date": "2026-04-15",
                    "due_date_reference": "2026-04-10",
                    "base_amount": 800.0,
                    "generated_amount": 40.0,
                    "settled_amount": 0.0,
                    "open_amount": 40.0,
                    "rule_snapshot_json": {"rule_id": 9},
                    "metadata_json": {"source": "simulate_for_schedule"},
                }
            ],
            "totals": {"interest": 40.0},
        },
    )
    monkeypatch.setattr(
        adjustment_module.FinancialTitleAdjustmentAllocationService,
        "build_default_allocations",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(adjustment_module.db.session, "add", lambda obj: captured["added"].append(obj))
    monkeypatch.setattr(adjustment_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(adjustment_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(adjustment_module.db.session, "rollback", lambda: captured.setdefault("rolled_back", True))

    result, error = FinancialTitleAdjustmentService.materialize_title_adjustments(
        company_id=7,
        schedule_id=34,
        allowed_company_ids=[7],
        reference_date=date(2026, 4, 15),
    )

    assert error is None
    assert result["count"] == 1
    assert captured["adjustment_kwargs"][0]["company_id"] == 7
    assert captured["adjustment_kwargs"][0]["financial_schedule_id"] == 34
    assert captured["adjustment_kwargs"][0]["adjustment_type"] == "interest"
    assert captured["adjustment_kwargs"][0]["open_amount"] == Decimal("40.00")
    assert captured["committed"] is True
