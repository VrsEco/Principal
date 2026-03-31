import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_automation_service as automation_module
from services.financial_automation_service import FinancialAutomationService


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self


def test_update_rule_accepts_same_rule_code_in_payload(monkeypatch):
    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return rule

    class _RuleModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _Query()

    rule = SimpleNamespace(
        id=1,
        company_id=9,
        rule_code="FIN-AUTO-001",
        process_id=10,
        activity_id=None,
        bank_account_id=None,
        counterparty_id=None,
        chart_account_id=None,
        cost_center_id=None,
        routine_id=None,
    )

    monkeypatch.setattr(automation_module, "FinancialAutomationRule", _RuleModel)
    monkeypatch.setattr(automation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_validate_rule_scope", lambda **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_serialize_rule", lambda current: current.__dict__)
    monkeypatch.setattr(automation_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(automation_module.db.session, "rollback", lambda: None)

    result, error = FinancialAutomationService.update_rule(
        rule_id=1,
        company_id=9,
        payload={
            "rule_code": "FIN-AUTO-001",
            "name": "Regra atualizada",
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert rule.rule_code == "FIN-AUTO-001"
    assert rule.name == "Regra atualizada"


def test_update_rule_rejects_rule_code_change(monkeypatch):
    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return rule

    class _RuleModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _Query()

    rule = SimpleNamespace(
        id=1,
        company_id=9,
        rule_code="FIN-AUTO-001",
        process_id=10,
        activity_id=None,
        bank_account_id=None,
        counterparty_id=None,
        chart_account_id=None,
        cost_center_id=None,
        routine_id=None,
    )

    monkeypatch.setattr(automation_module, "FinancialAutomationRule", _RuleModel)
    monkeypatch.setattr(automation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)

    result, error = FinancialAutomationService.update_rule(
        rule_id=1,
        company_id=9,
        payload={"rule_code": "FIN-AUTO-999"},
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "O código da regra de automação não pode ser alterado após a criação."
