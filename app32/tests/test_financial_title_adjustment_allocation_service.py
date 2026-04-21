from decimal import Decimal

import pytest

import services.financial_title_adjustment_allocation_service as allocation_module
from models.financial import FinancialSchedule, FinancialTitleAdjustment
from services.financial_title_adjustment_allocation_service import FinancialTitleAdjustmentAllocationService


def test_build_default_allocations_inherits_principal_dimensions_from_schedule():
    adjustment = FinancialTitleAdjustment(
        id=27,
        company_id=7,
        generated_amount=Decimal("50.25"),
    )
    schedule = FinancialSchedule(
        id=34,
        company_id=7,
        chart_account_id=501,
        cost_center_id=19,
        budget_document_id=11,
        activity_id=31,
        process_instance_id=77,
        routine_id=88,
    )

    allocations = FinancialTitleAdjustmentAllocationService.build_default_allocations(
        adjustment=adjustment,
        schedule=schedule,
    )

    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.company_id == 7
    assert allocation.financial_title_adjustment_id == 27
    assert allocation.chart_account_id == 501
    assert allocation.cost_center_id == 19
    assert allocation.budget_document_id == 11
    assert allocation.activity_id == 31
    assert allocation.process_instance_id == 77
    assert allocation.routine_id == 88
    assert allocation.percentage == Decimal("100.0000")
    assert allocation.amount == Decimal("50.25")
    assert allocation.metadata_json["inheritance_source"] == "financial_schedule"
    assert allocation.metadata_json["inherited_from_schedule_id"] == 34


def test_build_default_allocations_returns_empty_without_principal_dimensions():
    adjustment = FinancialTitleAdjustment(id=27, company_id=7, generated_amount=Decimal("50.25"))
    schedule = FinancialSchedule(id=34, company_id=7)

    allocations = FinancialTitleAdjustmentAllocationService.build_default_allocations(
        adjustment=adjustment,
        schedule=schedule,
    )

    assert allocations == []


def test_build_default_allocations_blocks_cross_company_inheritance():
    adjustment = FinancialTitleAdjustment(id=27, company_id=7, generated_amount=Decimal("50.25"))
    schedule = FinancialSchedule(id=34, company_id=8, chart_account_id=501)

    with pytest.raises(ValueError, match="mesmo escopo de empresa"):
        FinancialTitleAdjustmentAllocationService.build_default_allocations(
            adjustment=adjustment,
            schedule=schedule,
        )


def test_build_default_allocations_prefers_adjustment_rule_chart_account(monkeypatch):
    class _Column:
        def __eq__(self, other):
            return True

        def is_(self, other):
            return True

    class _QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return type("CorrectionIndex", (), {"metadata_json": {"chart_account_id": 909}})()

    monkeypatch.setattr(
        allocation_module,
        "FinancialCorrectionIndex",
        type(
            "FinancialCorrectionIndexStub",
            (),
            {
                "company_id": _Column(),
                "id": _Column(),
                "deleted_at": _Column(),
                "is_active": _Column(),
                "query": _QueryStub(),
            },
        ),
    )

    adjustment = FinancialTitleAdjustment(
        id=27,
        company_id=7,
        generated_amount=Decimal("50.25"),
        adjustment_type="interest",
        rule_snapshot_json={"rule_id": 12},
    )
    schedule = FinancialSchedule(
        id=34,
        company_id=7,
        chart_account_id=501,
        cost_center_id=19,
        metadata_json={"correction_index_id": 12},
    )

    allocations = FinancialTitleAdjustmentAllocationService.build_default_allocations(
        adjustment=adjustment,
        schedule=schedule,
    )

    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.chart_account_id == 909
    assert allocation.metadata_json["chart_account_source"] == "adjustment_rule"
