import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_budget_actual_service import FinancialBudgetActualService


def test_budget_actual_workspace_model_contract():
    model = FinancialBudgetActualService.build_workspace_model()

    assert model["contract_version"] == "financial_budget_actual_workspace_v1"
    assert model["title"] == "Orçado x Realizado"
    assert [item["key"] for item in model["dimensions"]] == ["chart_account_id", "cost_center_id", "project_id", "process_id"]
    assert [item["key"] for item in model["measures"]] == ["planned_amount", "actual_amount", "variance_amount", "consumption_rate"]
    assert model["ux"]["primary_filter"] == "period"
