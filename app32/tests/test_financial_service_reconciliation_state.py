import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_service as financial_module
from services.financial_service import FinancialService


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self

    def in_(self, other):
        return self


class _QueryStub:
    def __init__(self, all_result=None):
        self._all_result = list(all_result or [])

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._all_result)


def _install_settlement_model(monkeypatch, settlements):
    class _SettlementModel:
        company_id = _Column()
        financial_entry_id = _Column()
        deleted_at = _Column()
        settlement_status = _Column()
        reconciliation_status = _Column()
        query = _QueryStub(all_result=settlements)

    monkeypatch.setattr(financial_module, "FinancialSettlement", _SettlementModel)


def test_is_entry_reconciled_false_for_partial_reconciled_settlement(monkeypatch):
    entry = SimpleNamespace(id=55, company_id=1, original_amount=Decimal("817.33"), metadata_json={"reconciled": True})
    settlements = [
        SimpleNamespace(
            principal_amount=Decimal("392.00"),
            settlement_status="posted",
            reconciliation_status="reconciled",
            deleted_at=None,
        )
    ]
    _install_settlement_model(monkeypatch, settlements)

    assert FinancialService.is_entry_reconciled(entry) is False


def test_is_entry_reconciled_true_only_when_fully_settled_by_reconciled_settlements(monkeypatch):
    entry = SimpleNamespace(id=55, company_id=1, original_amount=Decimal("817.33"), metadata_json={})
    settlements = [
        SimpleNamespace(
            principal_amount=Decimal("392.00"),
            settlement_status="posted",
            reconciliation_status="reconciled",
            deleted_at=None,
        ),
        SimpleNamespace(
            principal_amount=Decimal("425.33"),
            settlement_status="posted",
            reconciliation_status="matched",
            deleted_at=None,
        ),
    ]
    _install_settlement_model(monkeypatch, settlements)

    assert FinancialService.is_entry_reconciled(entry) is True


def test_set_entry_reconciliation_state_removes_legacy_flag_from_entry_metadata():
    entry = SimpleNamespace(
        metadata_json={
            "reconciled": True,
            "other": "keep",
        }
    )

    FinancialService.set_entry_reconciliation_state(
        entry=entry,
        reconciled=False,
        actor_reason="Cancelamento da baixa conciliada.",
    )

    assert entry.metadata_json["other"] == "keep"
    assert entry.metadata_json["reconciliation_updated_reason"] == "Cancelamento da baixa conciliada."
    assert "reconciled" not in entry.metadata_json
