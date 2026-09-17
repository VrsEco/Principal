from types import SimpleNamespace

from services.internal_audit_financial_analyzer import (
    InternalAuditFinancialAnalyzer,
    RULE_COUNTERPARTY_CLASSIFICATION,
    RULE_DUPLICATE_REFERENCE,
    RULE_EMPLOYEE_CLASSIFICATION,
)


def row(settlement_id, *, counterparty_id, chart_account_id, bank_account_id=7, reference=None):
    settlement = SimpleNamespace(id=settlement_id, bank_account_id=bank_account_id, external_reference=reference)
    entry = SimpleNamespace(id=100 + settlement_id, counterparty_id=counterparty_id, chart_account_id=chart_account_id)
    return settlement, entry


def test_financial_crossings_detects_requested_rules_without_persisting():
    counterparties = {
        1: SimpleNamespace(id=1, name="Fornecedor A", metadata_json={}),
        2: SimpleNamespace(id=2, name="Colaborador B", metadata_json={"employee_id": 44}),
    }
    accounts = {
        10: SimpleNamespace(id=10, name="Despesas de viagem"),
        11: SimpleNamespace(id=11, name="Material de escritório"),
        12: SimpleNamespace(id=12, name="Salários"),
    }
    candidates = InternalAuditFinancialAnalyzer.detect(
        [
            row(1, counterparty_id=1, chart_account_id=10),
            row(2, counterparty_id=1, chart_account_id=11),
            row(3, counterparty_id=2, chart_account_id=11),
            row(4, counterparty_id=1, chart_account_id=10, reference="PIX-123"),
            row(5, counterparty_id=1, chart_account_id=11, reference="pix-123"),
        ],
        counterparties=counterparties,
        accounts=accounts,
    )
    rules = {candidate.rule_id for candidate in candidates}
    assert RULE_COUNTERPARTY_CLASSIFICATION in rules
    assert RULE_EMPLOYEE_CLASSIFICATION in rules
    assert RULE_DUPLICATE_REFERENCE in rules
    assert all(candidate.metadata for candidate in candidates)


def test_employee_allowed_classes_do_not_raise_candidate():
    candidates = InternalAuditFinancialAnalyzer.detect(
        [row(1, counterparty_id=2, chart_account_id=12)],
        counterparties={2: SimpleNamespace(id=2, name="Colaborador", metadata_json={"employee_id": 7})},
        accounts={12: SimpleNamespace(id=12, name="Folha de pagamento")},
    )
    assert RULE_EMPLOYEE_CLASSIFICATION not in {candidate.rule_id for candidate in candidates}
