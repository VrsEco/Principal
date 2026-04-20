import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_budget_actual_service import FinancialBudgetActualService


def test_budget_actual_rollout_contract_governance():
    contract = FinancialBudgetActualService.build_rollout_contract()

    assert contract["contract_version"] == "financial_budget_actual_rollout_v1"
    assert contract["workspace_contract"] == "financial_budget_actual_workspace_v1"
    assert contract["canonical_name"] == "Orçado x Realizado"
    assert contract["tenant_guardrails"] == {
        "requires_company_id": True,
        "cross_tenant_records": "blocked",
        "route_business_logic": "forbidden",
    }
    assert contract["views"] == ["period", "competence", "executive"]
    assert contract["required_dimensions"] == ["chart_account_id", "cost_center_id", "project_id", "process_id"]
    assert contract["required_measures"] == ["planned_amount", "actual_amount", "variance_amount", "consumption_rate"]


def test_budget_actual_rollout_uses_financial_v2_canonical_language():
    contract = FinancialBudgetActualService.build_rollout_contract()
    labels = {source["label"] for source in contract["data_sources"]}

    assert "Títulos Financeiros" in labels
    assert "Baixas" in labels
    assert "Agendamentos" not in labels
    assert "Lançamentos" not in labels
    assert "validar linguagem canônica: Títulos Financeiros e Baixas" in contract["qa_checklist"]


def test_budget_actual_rollout_status_taxonomy_matches_comparison_rows():
    rows = FinancialBudgetActualService.build_comparison_rows(
        [{"company_id": 7, "chart_account_id": 1, "planned_amount": "100.00"}],
        [{"company_id": 7, "chart_account_id": 1, "actual_amount": "110.00"}],
        dimensions=["chart_account_id"],
        company_id=7,
    )
    contract = FinancialBudgetActualService.build_rollout_contract()

    assert rows[0]["status"] == "overrun"
    assert rows[0]["status"] in contract["statuses"]
    assert contract["statuses"]["no_budget"] == "Realizado sem orçamento"
