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


def test_build_comparison_rows_by_competence_and_executive_summary():
    planned_records = [
        {
            "company_id": 7,
            "chart_account_id": 10,
            "cost_center_id": 20,
            "project_id": 30,
            "process_id": 40,
            "competence": "2026-04-01",
            "planned_amount": "1000.00",
            "source": "orcamento",
        },
        {
            "company_id": 7,
            "chart_account_id": 10,
            "cost_center_id": 20,
            "project_id": 30,
            "process_id": 40,
            "competence": "2026-05-01",
            "planned_amount": "500.00",
            "source": "orcamento",
        },
    ]
    actual_records = [
        {
            "company_id": 7,
            "chart_account_id": 10,
            "cost_center_id": 20,
            "project_id": 30,
            "process_id": 40,
            "competence_date": "2026-04-15",
            "actual_amount": "950.00",
            "source": "baixa",
        },
        {
            "company_id": 7,
            "chart_account_id": 11,
            "cost_center_id": 20,
            "project_id": None,
            "process_id": None,
            "competence_date": "2026-04-20",
            "actual_amount": "100.00",
            "source": "titulo",
        },
    ]

    rows = FinancialBudgetActualService.build_comparison_rows(
        planned_records,
        actual_records,
        view="competence",
        company_id=7,
    )

    april_budgeted = next(row for row in rows if row["dimensions"]["chart_account_id"] == 10 and row["period_key"] == "2026-04")
    assert april_budgeted["planned_amount"] == 1000.0
    assert april_budgeted["actual_amount"] == 950.0
    assert april_budgeted["variance_amount"] == 50.0
    assert april_budgeted["consumption_rate"] == 95.0
    assert april_budgeted["status"] == "attention"

    april_unbudgeted = next(row for row in rows if row["dimensions"]["chart_account_id"] == 11)
    assert april_unbudgeted["planned_amount"] == 0.0
    assert april_unbudgeted["actual_amount"] == 100.0
    assert april_unbudgeted["status"] == "no_budget"

    summary = FinancialBudgetActualService.build_executive_summary(rows)
    assert summary["contract_version"] == "financial_budget_actual_executive_summary_v1"
    assert summary["planned_amount"] == 1500.0
    assert summary["actual_amount"] == 1050.0
    assert summary["variance_amount"] == 450.0
    assert summary["consumption_rate"] == 70.0
    assert summary["status"] == "on_track"
    assert summary["status_counts"] == {"attention": 1, "no_budget": 1, "on_track": 1}


def test_budget_actual_comparison_rejects_cross_tenant_records():
    try:
        FinancialBudgetActualService.build_comparison_rows(
            [{"company_id": 8, "chart_account_id": 1, "planned_amount": "10.00"}],
            [],
            company_id=7,
        )
    except ValueError as exc:
        assert "tenant" in str(exc)
    else:
        raise AssertionError("Comparativo deveria bloquear registros fora do company_id informado")
