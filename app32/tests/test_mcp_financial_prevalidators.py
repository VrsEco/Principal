"""Pré-validação das financeiras que exigem aprovação: o erro de negócio aparece antes de gastar a aprovação."""

from types import SimpleNamespace

import pytest

from services import financial_prevalidation_rules as rules
from src.core import mcp_prevalidation as pre
from src.core.mcp_gate_policy import requires_persisted_approval
from src.core.mcp_write_cohorts import finance_cohort_names


# ---- guarda: nenhuma financeira com aprovação fica sem pré-validador -------------------------------------
def test_every_published_financial_tool_that_needs_approval_has_a_prevalidator():
    from src.intelligence.tool_catalog import catalog

    published = {"create_financial_entry", "create_financial_settlement"}
    # O faturamento comercial (generate_commercial_*) não está nas coortes financeiras (decisão da 2F).
    candidates = [n for n in (*finance_cohort_names(), *published) if not n.startswith("generate_commercial_")]
    needing = [n for n in candidates if requires_persisted_approval(n, catalog.get_tool_capability(n))]
    assert needing, "o catálogo deve apontar ferramentas financeiras com aprovação"
    missing = sorted(set(needing) - set(pre.PREVALIDATORS))
    assert not missing, f"financeiras com aprovação sem pré-validador: {missing}"


def test_every_registered_prevalidator_resolves_to_a_callable():
    for tool_name, spec in pre.PREVALIDATORS.items():
        assert callable(pre._resolve(spec)), tool_name


# ---- regras da ferramenta de baixa (as mesmas antes e depois da aprovação) --------------------------------
@pytest.mark.parametrize(
    "company_id,payload,expected",
    [
        (True, {}, "company_id válido"),
        (0, {}, "company_id válido"),
        (10, {"company_id": 11}, "diverge do tenant"),
        (10, {"company_id": "x"}, "company_id do payload é inválido"),
        (10, {}, "financial_entry_id é obrigatório"),
        (10, {"financial_entry_id": 5}, "bank_account_id é obrigatório"),
        (10, {"financial_entry_id": 5, "bank_account_id": 16, "settlement_status": "draft"}, "settlement_status=posted"),
    ],
)
def test_settlement_request_rules_refuse_with_the_tool_messages(company_id, payload, expected):
    normalized, error = rules.settlement_request_rules(company_id, payload)
    assert normalized is None and expected in error


def test_settlement_request_rules_bind_the_tenant_and_accept_a_valid_request():
    normalized, error = rules.settlement_request_rules(
        10, {"financial_entry_id": 5, "bank_account_id": 16, "principal_amount": 1}
    )
    assert error is None and normalized["company_id"] == 10


# ---- existência e formato ----------------------------------------------------------------------------------
def test_run_until_is_checked_as_a_date():
    assert rules.run_until_valid(None) is None and rules.run_until_valid("2026-10-31") is None
    assert "YYYY-MM-DD" in rules.run_until_valid("31/10/2026")


@pytest.mark.parametrize(
    "func,message",
    [
        (rules.import_batch_exists, "Lote de importação"),
        (rules.import_row_exists, "Linha do extrato"),
        (rules.entry_exists, "Lançamento financeiro"),
        (rules.bordero_exists, "Borderô"),
        (rules.schedule_exists, "Agendamento"),
    ],
)
def test_existence_checks_report_the_missing_record_per_tenant(monkeypatch, func, message):
    monkeypatch.setattr(rules, "_exists", lambda model, company_id, record_id: record_id == 7 and company_id == 10)
    assert func(10, 7) is None
    assert message in func(10, 8)
    assert message in func(11, 7), "outro tenant não enxerga o registro"


def test_exists_helper_rejects_non_numeric_ids_without_querying():
    assert rules._exists(SimpleNamespace(), 10, "abc") is False


# ---- pré-validadores delegam às regras ---------------------------------------------------------------------
def test_prevalidators_combine_the_row_and_the_entry(monkeypatch):
    monkeypatch.setattr(rules, "import_row_exists", lambda c, r: None if r == 1 else "Linha do extrato não encontrada nesta empresa.")
    monkeypatch.setattr(rules, "entry_exists", lambda c, e: None if e == 2 else "Lançamento financeiro não encontrado nesta empresa.")
    ok = {"company_id": 10, "row_id": 1, "financial_entry_id": 2}
    assert pre.reconciliation_match(ok) is None
    assert pre.reconciliation_match({**ok, "row_id": 9}).startswith("Linha do extrato")
    assert pre.reconciliation_match({**ok, "financial_entry_id": 9}).startswith("Lançamento financeiro")
    assert pre.reconciliation_new_entry({"company_id": 10, "row_id": 9}).startswith("Linha do extrato")


def test_due_schedules_checks_the_date_before_the_schedule(monkeypatch):
    monkeypatch.setattr(rules, "schedule_exists", lambda c, s: "Agendamento não encontrado nesta empresa.")
    assert "YYYY-MM-DD" in pre.due_schedules({"company_id": 10, "run_until": "ontem"})
    assert pre.due_schedules({"company_id": 10}) is None, "sem schedule_id, nada a conferir além da data"
    assert pre.due_schedules({"company_id": 10, "schedule_id": 3}).startswith("Agendamento")


def test_bordero_settlement_binds_the_tenant_then_checks_the_bordero(monkeypatch):
    monkeypatch.setattr(rules, "bordero_exists", lambda c, b: "Borderô não encontrado nesta empresa.")
    assert pre.bordero_settlement({"company_id": 10, "bordero_id": 3, "payload": {"company_id": 11}}).startswith(
        "company_id do payload diverge"
    )
    assert pre.bordero_settlement({"company_id": 10, "bordero_id": 3, "payload": {}}).startswith("Borderô")


def test_settlement_prevalidator_runs_the_request_rules_then_the_read_only_checks(monkeypatch):
    seen = []
    monkeypatch.setattr(rules, "settlement_read_only", lambda normalized: seen.append(normalized) or "Baixa principal excede o valor principal do lançamento.")
    assert pre.settlement({"company_id": 10, "payload": {}}).startswith("financial_entry_id")
    assert seen == []
    error = pre.settlement({"company_id": 10, "payload": {"financial_entry_id": 5, "bank_account_id": 16}})
    assert error.startswith("Baixa principal excede") and seen[0]["company_id"] == 10


def test_allocation_prevalidator_uses_the_service_validation_without_writing(monkeypatch):
    from services import financial_service as fs

    calls = []
    monkeypatch.setattr(
        fs.FinancialService,
        "validate_allocation_batch",
        staticmethod(lambda **k: calls.append(k) or (None, None, None, "Rateio percentual inválido. Soma atual: 60.")),
    )
    assert pre.replace_allocations({"company_id": 10, "payload": {"financial_entry_id": 5}}) == "Rateio percentual inválido. Soma atual: 60."
    assert calls[0]["payload"]["company_id"] == 10
    assert pre.replace_allocations({"company_id": 10, "payload": {"company_id": 11}}).startswith("company_id do payload diverge")
