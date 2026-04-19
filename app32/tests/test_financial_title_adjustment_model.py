from datetime import date, datetime
from decimal import Decimal

from models.financial import (
    FinancialSettlementComponent,
    FinancialTitleAdjustment,
    TITLE_ADJUSTMENT_STATUS_VALUES,
    TITLE_ADJUSTMENT_TYPE_VALUES,
)


def test_financial_title_adjustment_to_dict_serializes_contract():
    adjustment = FinancialTitleAdjustment(
        id=27,
        company_id=7,
        financial_schedule_id=34,
        adjustment_type="monetary_correction",
        status="partial",
        calculation_date=date(2026, 4, 20),
        competence_date=date(2026, 4, 20),
        due_date_reference=date(2026, 4, 10),
        base_amount=Decimal("1000.00"),
        generated_amount=Decimal("50.25"),
        settled_amount=Decimal("20.25"),
        open_amount=Decimal("30.00"),
        rule_snapshot_json={"index": "IPCA"},
        metadata_json={"source": "system"},
        created_at=datetime(2026, 4, 20, 10, 0, 0),
        updated_at=datetime(2026, 4, 20, 11, 30, 0),
    )

    assert adjustment.to_dict() == {
        "id": 27,
        "company_id": 7,
        "financial_schedule_id": 34,
        "adjustment_type": "monetary_correction",
        "status": "partial",
        "calculation_date": "2026-04-20",
        "competence_date": "2026-04-20",
        "due_date_reference": "2026-04-10",
        "base_amount": 1000.0,
        "generated_amount": 50.25,
        "settled_amount": 20.25,
        "open_amount": 30.0,
        "rule_snapshot_json": {"index": "IPCA"},
        "metadata_json": {"source": "system"},
        "created_at": "2026-04-20T10:00:00",
        "updated_at": "2026-04-20T11:30:00",
        "deleted_at": None,
    }


def test_financial_title_adjustment_contract_constants_are_complete():
    assert TITLE_ADJUSTMENT_TYPE_VALUES == (
        "monetary_correction",
        "interest",
        "fine",
        "discount",
        "writeoff",
    )
    assert TITLE_ADJUSTMENT_STATUS_VALUES == ("open", "partial", "settled", "cancelled")


def test_financial_settlement_component_origin_adjustment_fk_targets_title_adjustments():
    column = FinancialSettlementComponent.__table__.c.origin_adjustment_id
    foreign_keys = {fk.target_fullname for fk in column.foreign_keys}

    assert foreign_keys == {"financial_title_adjustments.id"}
