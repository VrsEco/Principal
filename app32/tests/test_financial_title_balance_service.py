import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_title_balance_service import FinancialTitleBalanceService


class _Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_calculate_from_records_exposes_principal_adjustments_and_total_open():
    schedule = _Obj(
        id=34,
        company_id=7,
        schedule_code="TIT-034",
        status="open",
        movement_nature="debit",
        template_amount=Decimal("1000.00"),
    )
    entry = _Obj(id=81, original_amount=Decimal("1000.00"))
    settlement = _Obj(id=501, settlement_status="posted", deleted_at=None, principal_amount=Decimal("200.00"))
    components = [
        _Obj(financial_settlement_id=501, component_type="principal", amount=Decimal("200.00")),
        _Obj(financial_settlement_id=501, component_type="interest", amount=Decimal("50.00"), origin_adjustment_id=900),
    ]
    adjustments = [
        _Obj(
            id=900,
            adjustment_type="interest",
            status="open",
            generated_amount=Decimal("80.00"),
            settled_amount=Decimal("0.00"),
            open_amount=Decimal("30.00"),
            deleted_at=None,
        )
    ]

    result = FinancialTitleBalanceService.calculate_from_records(
        schedule=schedule,
        entries=[entry],
        settlements=[settlement],
        components=components,
        adjustments=adjustments,
        reference_date=date(2026, 4, 20),
    )

    assert result["principal_amount"] == 1000.0
    assert result["principal_settled"] == 200.0
    assert result["principal_open"] == 800.0
    assert result["adjustments_generated"] == 80.0
    assert result["adjustments_settled"] == 50.0
    assert result["adjustments_open"] == 30.0
    assert result["total_open"] == 830.0
    assert result["signed_total_open"] == -830.0
    assert result["settlement_state"] == "partial"
    assert result["operational_state"] == "partial"
    assert result["operational_state_label"] == "Parcial"
    assert result["include_in_accounting_reports"] is True
    assert result["include_in_projected_reports"] is False
    assert result["editable_open"]["principal"] == 800.0
    assert result["editable_open"]["financial_correction"] == 30.0
    assert result["editable_open"]["total_open"] == 830.0
    assert result["editable_rules"]["principal_max"] == 800.0


def test_calculate_from_records_uses_legacy_settlement_fields_when_components_absent():
    schedule = _Obj(
        id=35,
        company_id=7,
        schedule_code="TIT-035",
        status="open",
        movement_nature="credit",
        template_amount=Decimal("500.00"),
    )
    settlement = _Obj(
        id=601,
        settlement_status="posted",
        deleted_at=None,
        principal_amount=Decimal("125.00"),
        interest_amount=Decimal("10.00"),
        penalty_amount=Decimal("5.00"),
        fee_amount=Decimal("0.00"),
        other_adjustments_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
    )

    result = FinancialTitleBalanceService.calculate_from_records(
        schedule=schedule,
        entries=[],
        settlements=[settlement],
        components=[],
        adjustments=[],
        reference_date=date(2026, 4, 20),
    )

    assert result["principal_amount"] == 500.0
    assert result["principal_settled"] == 125.0
    assert result["principal_open"] == 375.0
    assert result["adjustments_open"] == 0.0
    assert result["total_open"] == 375.0
    assert result["signed_total_open"] == 375.0


def test_get_title_balance_rejects_company_out_of_scope():
    result, error = FinancialTitleBalanceService.get_title_balance(
        company_id=7,
        schedule_id=34,
        allowed_company_ids=[8],
    )

    assert result is None
    assert error == "A operação financeira está fora do escopo da empresa autorizada."


def test_calculate_from_records_marks_discount_only_settlement_as_partial():
    schedule = _Obj(
        id=36,
        company_id=7,
        schedule_code="TIT-036",
        status="open",
        movement_nature="debit",
        template_amount=Decimal("1000.00"),
    )
    settlement = _Obj(
        id=602,
        settlement_status="posted",
        deleted_at=None,
        principal_amount=Decimal("0.00"),
        discount_amount=Decimal("100.00"),
    )
    components = [
        _Obj(financial_settlement_id=602, component_type="discount", amount=Decimal("100.00")),
    ]

    result = FinancialTitleBalanceService.calculate_from_records(
        schedule=schedule,
        entries=[],
        settlements=[settlement],
        components=components,
        adjustments=[],
        reference_date=date(2026, 4, 20),
    )

    assert result["principal_open"] == 1000.0
    assert result["discounts_applied"] == 100.0
    assert result["total_open"] == 1000.0
    assert result["settlement_state"] == "partial"
    assert result["operational_state"] == "partial"
    assert result["has_open_balance"] is True
