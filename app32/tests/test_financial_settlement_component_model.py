import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.financial import FinancialSettlementComponent, SETTLEMENT_COMPONENT_TYPE_VALUES


def test_financial_settlement_component_to_dict_serializes_contract():
    created_at = datetime(2026, 4, 20, 9, 15, 30)
    component = FinancialSettlementComponent(
        id=15,
        company_id=7,
        financial_settlement_id=901,
        financial_schedule_id=34,
        component_type="monetary_correction",
        amount=Decimal("50.25"),
        competence_date=date(2026, 4, 20),
        due_date=date(2026, 4, 20),
        source="user",
        origin_adjustment_id=81,
        metadata_json={"origin": "manual_override"},
        created_at=created_at,
    )

    assert component.to_dict() == {
        "id": 15,
        "company_id": 7,
        "financial_settlement_id": 901,
        "financial_schedule_id": 34,
        "component_type": "monetary_correction",
        "amount": 50.25,
        "competence_date": "2026-04-20",
        "due_date": "2026-04-20",
        "source": "user",
        "origin_adjustment_id": 81,
        "metadata_json": {"origin": "manual_override"},
        "created_at": created_at.isoformat(),
    }


def test_financial_settlement_component_type_contract_is_complete():
    assert SETTLEMENT_COMPONENT_TYPE_VALUES == (
        "principal",
        "monetary_correction",
        "interest",
        "fine",
        "discount",
        "manual_adjustment",
    )
