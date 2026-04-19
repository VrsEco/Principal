import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_settlement_composition_service as composition_module
from services.financial_settlement_composition_service import FinancialSettlementCompositionService


class _Schedule:
    id = 34
    company_id = 7
    schedule_code = "TIT-034"
    movement_nature = "debit"
    template_amount = Decimal("1000.00")
    competence_date = date(2026, 4, 1)
    first_due_date = date(2026, 4, 10)
    next_due_date = date(2026, 4, 10)
    start_date = date(2026, 4, 1)


class _Adjustment:
    def __init__(self, *, id, adjustment_type, open_amount, generated_amount=None, settled_amount=0):
        self.id = id
        self.company_id = 7
        self.adjustment_type = adjustment_type
        self.open_amount = Decimal(str(open_amount))
        self.generated_amount = Decimal(str(generated_amount if generated_amount is not None else open_amount))
        self.settled_amount = Decimal(str(settled_amount))
        self.status = "open"
        self.deleted_at = None
        self.calculation_date = date(2026, 4, 20)


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _QueryStub:
    def __init__(self, first_result=None):
        self._first_result = first_result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result


def test_simulate_settlement_suggests_adjustment_first_then_principal(monkeypatch):
    schedule = _Schedule()
    adjustments = [_Adjustment(id=91, adjustment_type="interest", open_amount="30.00")]
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_fetch_schedule", lambda **kwargs: schedule)
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_list_open_adjustments", lambda **kwargs: adjustments)
    monkeypatch.setattr(
        composition_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {"principal_open": 800.0, "adjustments_open": 30.0, "total_open": 830.0},
    )

    result, error = FinancialSettlementCompositionService.simulate_settlement(
        company_id=7,
        schedule_id=34,
        payload={"settlement_date": "2026-04-20", "gross_amount": 300},
        allowed_company_ids=[7],
    )

    assert error is None
    assert result["valid"] is True
    assert result["composition"]["interest"] == 30.0
    assert result["composition"]["principal"] == 270.0
    assert result["composition"]["gross_amount"] == 300.0
    assert result["after"] == {"principal_open": 530.0, "adjustments_open": 0.0, "total_open": 530.0}
    components = result["settlement_payload"]["settlement_components"]
    assert components[0]["component_type"] == "principal"
    assert components[1]["component_type"] == "interest"
    assert components[1]["origin_adjustment_id"] == 91
    assert result["settlement_payload"]["principal_amount"] == 270.0
    assert result["settlement_payload"]["interest_amount"] == 30.0


def test_simulate_settlement_rejects_components_above_available_balance(monkeypatch):
    schedule = _Schedule()
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_fetch_schedule", lambda **kwargs: schedule)
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_list_open_adjustments", lambda **kwargs: [])
    monkeypatch.setattr(
        composition_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {"principal_open": 100.0, "adjustments_open": 0.0, "total_open": 100.0},
    )

    result, error = FinancialSettlementCompositionService.simulate_settlement(
        company_id=7,
        schedule_id=34,
        payload={"settlement_date": "2026-04-20", "composition": {"principal": 150}},
        allowed_company_ids=[7],
    )

    assert error is None
    assert result["valid"] is False
    assert "Valor de principal da baixa não pode superar o principal em aberto do título." in result["errors"]


def test_simulate_settlement_accepts_free_financial_correction(monkeypatch):
    schedule = _Schedule()
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_fetch_schedule", lambda **kwargs: schedule)
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_list_open_adjustments", lambda **kwargs: [])
    monkeypatch.setattr(
        composition_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {"principal_open": 1000.0, "adjustments_open": 0.0, "total_open": 1000.0},
    )

    result, error = FinancialSettlementCompositionService.simulate_settlement(
        company_id=7,
        schedule_id=34,
        payload={
            "settlement_date": "2026-04-20",
            "composition": {"principal": 200, "financial_correction": 50, "discount": 10},
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert result["valid"] is True
    assert result["composition"]["financial_correction"] == 50.0
    assert result["composition"]["gross_amount"] == 240.0
    assert result["settlement_payload"]["principal_amount"] == 200.0
    assert result["settlement_payload"]["other_adjustments_amount"] == 50.0
    assert result["settlement_payload"]["discount_amount"] == 10.0
    components = result["settlement_payload"]["settlement_components"]
    assert [item["component_type"] for item in components] == ["principal", "manual_adjustment", "discount"]
    assert components[1]["metadata_json"]["free_value_adjustment"] is True


def test_create_assisted_settlement_forwards_component_payload_and_updates_adjustments(monkeypatch):
    captured = {}
    schedule = _Schedule()
    adjustment = _Adjustment(id=91, adjustment_type="interest", open_amount="30.00", generated_amount="50.00", settled_amount="20.00")
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_fetch_schedule", lambda **kwargs: schedule)
    monkeypatch.setattr(composition_module.FinancialSettlementCompositionService, "_list_open_adjustments", lambda **kwargs: [adjustment])
    monkeypatch.setattr(
        composition_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {"principal_open": 800.0, "adjustments_open": 30.0, "total_open": 830.0},
    )

    class _FakeScheduleService:
        @staticmethod
        def create_settlement_from_schedule(**kwargs):
            captured["settlement_payload"] = kwargs["payload"]
            return {"settlement": {"id": 501}, "entry": {"id": 99}, "created_entry": True}, None

    class _FakeAdjustmentModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=adjustment)

    monkeypatch.setitem(sys.modules, "services.financial_schedule_service", type("Module", (), {"FinancialScheduleService": _FakeScheduleService}))
    monkeypatch.setattr(composition_module, "FinancialTitleAdjustment", _FakeAdjustmentModel)
    monkeypatch.setattr(composition_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(composition_module.db.session, "rollback", lambda: captured.setdefault("rolled_back", True))

    result, error = FinancialSettlementCompositionService.create_assisted_settlement(
        company_id=7,
        schedule_id=34,
        payload={"settlement_date": "2026-04-20", "gross_amount": 300, "settlement_type": "manual"},
        allowed_company_ids=[7],
    )

    assert error is None
    assert result["settlement"]["id"] == 501
    assert captured["settlement_payload"]["principal_amount"] == 270.0
    assert captured["settlement_payload"]["interest_amount"] == 30.0
    assert captured["settlement_payload"]["settlement_components"][1]["origin_adjustment_id"] == 91
    assert adjustment.settled_amount == Decimal("50.00")
    assert adjustment.open_amount == Decimal("0.00")
    assert adjustment.status == "settled"
    assert captured["committed"] is True
