from datetime import datetime
from decimal import Decimal

from models.financial import FinancialTitleAdjustmentAllocation


def test_financial_title_adjustment_allocation_to_dict_serializes_contract():
    allocation = FinancialTitleAdjustmentAllocation(
        id=9,
        company_id=7,
        financial_title_adjustment_id=27,
        chart_account_id=501,
        cost_center_id=19,
        budget_document_id=11,
        activity_id=31,
        process_instance_id=77,
        routine_id=88,
        percentage=Decimal("100.0000"),
        amount=Decimal("50.25"),
        metadata_json={"inheritance_mode": "principal_defaults"},
        created_at=datetime(2026, 4, 20, 11, 0, 0),
    )

    assert allocation.to_dict() == {
        "id": 9,
        "company_id": 7,
        "financial_title_adjustment_id": 27,
        "chart_account_id": 501,
        "cost_center_id": 19,
        "budget_document_id": 11,
        "activity_id": 31,
        "process_instance_id": 77,
        "routine_id": 88,
        "percentage": 100.0,
        "amount": 50.25,
        "metadata_json": {"inheritance_mode": "principal_defaults"},
        "created_at": "2026-04-20T11:00:00",
    }
