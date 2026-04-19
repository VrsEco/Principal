from datetime import date
from decimal import Decimal

import pytest

from schemas.financial import FinancialSettlementInput


def test_financial_settlement_input_defaults_gross_amount_from_aggregated_composition():
    data = FinancialSettlementInput(
        company_id=7,
        financial_entry_id=99,
        settlement_code="LIQ-000001",
        settlement_type="manual",
        settlement_date=date(2026, 4, 20),
        principal_amount=Decimal("200.00"),
        interest_amount=Decimal("25.00"),
        discount_amount=Decimal("5.00"),
    )

    assert data.net_amount == Decimal("220.00")
    assert data.gross_amount == Decimal("220.00")


def test_financial_settlement_input_validates_gross_amount_against_component_sum():
    with pytest.raises(ValueError, match="gross_amount inconsistente com a soma dos componentes"):
        FinancialSettlementInput(
            company_id=7,
            financial_entry_id=99,
            settlement_code="LIQ-000002",
            settlement_type="manual",
            settlement_date=date(2026, 4, 20),
            principal_amount=Decimal("200.00"),
            gross_amount=Decimal("250.00"),
            settlement_components=[
                {"component_type": "principal", "amount": Decimal("200.00")},
                {"component_type": "interest", "amount": Decimal("30.00")},
            ],
        )


def test_financial_settlement_input_accepts_discount_as_negative_component_for_gross_total():
    data = FinancialSettlementInput(
        company_id=7,
        financial_entry_id=99,
        settlement_code="LIQ-000003",
        settlement_type="manual",
        settlement_date=date(2026, 4, 20),
        principal_amount=Decimal("200.00"),
        discount_amount=Decimal("10.00"),
        gross_amount=Decimal("190.00"),
        settlement_components=[
            {"component_type": "principal", "amount": Decimal("200.00")},
            {"component_type": "discount", "amount": Decimal("10.00")},
        ],
    )

    assert data.gross_amount == Decimal("190.00")
    assert len(data.settlement_components) == 2
