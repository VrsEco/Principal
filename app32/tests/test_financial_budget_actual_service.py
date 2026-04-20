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


def test_aggregate_actual_records_by_account_center_project_and_process():
    grouped = FinancialBudgetActualService.aggregate_actual_records(
        [
            {
                "chart_account_id": 10,
                "cost_center_id": 20,
                "project_id": 30,
                "process_id": 40,
                "signed_amount": "100.50",
                "source": "baixa",
            },
            {
                "chart_account_id": 10,
                "cost_center_id": 20,
                "project_id": 30,
                "process_id": 40,
                "signed_amount": "25.25",
                "source": "titulo",
            },
            {
                "chart_account_id": 11,
                "cost_center_id": 20,
                "project_id": None,
                "process_id": None,
                "signed_amount": "-10.00",
                "source": "baixa",
            },
        ]
    )

    assert grouped[(10, 20, 30, 40)]["actual_amount"] == 125.75
    assert grouped[(10, 20, 30, 40)]["record_count"] == 2
    assert grouped[(10, 20, 30, 40)]["sources"] == ["baixa", "titulo"]
    assert grouped[(11, 20, None, None)]["actual_amount"] == -10.0
