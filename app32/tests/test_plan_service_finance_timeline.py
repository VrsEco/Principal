from __future__ import annotations

from types import SimpleNamespace

import services.plan_service as service_module
from services.plan_service import PlanService


def _build_sections():
    model = {
        "products": [
            {
                "name": "Produto A",
                "sale_price": 100.0,
                "market_share_goal_monthly_units": 10,
                "variable_costs_value": 20.0,
                "variable_expenses_value": 10.0,
                "ramp_up_entries": [
                    {"month_period": "2026.01", "percentage": 50},
                    {"month_period": "2026.02", "percentage": 100},
                ],
            }
        ],
        "segments": [],
    }
    execution = {
        "areas": {
            "operacional": {
                "items": [
                    {
                        "description": "Equipe operacional",
                        "classification": "contratação",
                        "payment_plan": {
                            "mode": "monthly_contract",
                            "start_date": "2026.01",
                            "monthly_amount": 100.0,
                        },
                    }
                ]
            }
        }
    }
    finance = {
        "analysis_params": {
            "period_months": "60",
            "start_date": "2026.01",
            "opportunity_cost_annual": 12.0,
        },
        "working_capital": {
            "cash_items": [],
            "receivables_items": [],
            "inventory_items": [],
        },
        "sources_v2": [
            {
                "name": "Capital próprio",
                "amount": 1000.0,
                "type": "propria",
                "date": "2026.01",
            }
        ],
        "profit_distribution": [
            {
                "description": "Distribuição sócios",
                "percentage": 10.0,
                "type": "socio",
                "start_date": "2026.01",
            }
        ],
    }
    return {"model": model, "execution": execution, "finance": finance}


def test_get_consolidated_finance_keeps_operation_after_last_ramp_month(monkeypatch):
    sections = _build_sections()

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )

    consolidated = PlanService.get_consolidated_finance(12, 31)

    assert len(consolidated["timeline"]) == 60
    assert consolidated["timeline"][0]["revenue"] == 500.0
    assert consolidated["timeline"][1]["revenue"] == 1000.0
    assert consolidated["timeline"][2]["revenue"] == 1000.0
    assert consolidated["timeline"][-1]["revenue"] == 1000.0
    assert consolidated["timeline"][2]["investor_net_flow"] > 0
    assert consolidated["timeline"][-1]["investor_net_flow"] > 0


def test_get_implantation_report_context_uses_full_finance_timeline(monkeypatch):
    sections = _build_sections()

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )
    monkeypatch.setattr(
        service_module,
        "PlanParticipant",
        SimpleNamespace(query=SimpleNamespace(filter_by=lambda **kwargs: SimpleNamespace(all=lambda: []))),
    )

    context = PlanService.get_implantation_report_context(12, 31)

    assert len(context["timeline_focus"]) == 60
    assert context["timeline_focus"][-1]["period"] == "2030-12"
    assert len(context["flow_timeline"]) == 27
    assert context["flow_timeline"][0]["is_aggregated_year"] is False
    assert context["flow_timeline"][11]["is_aggregated_year"] is False
    assert context["flow_timeline"][12]["is_aggregated_year"] is False
    assert context["flow_timeline"][-1]["period_label"] == "2030"
    assert context["flow_timeline"][-1]["is_aggregated_year"] is True
    assert len(context["ramp_up_timeline"]) == 2
    assert context["working_capital_settings"]["receivables_days"] == 30
    assert context["finance_executive_summary"] == ""


def test_aggregate_flow_timeline_for_report_keeps_monthly_until_end_of_next_year_and_then_annual():
    timeline = []
    for year in range(2026, 2031):
        for month in range(1, 13):
            if year == 2030 and month > 9:
                break
            period = f"{year:04d}-{month:02d}"
            timeline.append({
                "period": period,
                "revenue": 100.0,
                "business_net_flow": 10.0,
                "cumulative_business": float(len(timeline) + 1),
            })

    aggregated = PlanService._aggregate_flow_timeline_for_report(timeline, "2026.01")

    assert len(aggregated) == 27
    assert aggregated[0]["period"] == "2026-01"
    assert aggregated[11]["period"] == "2026-12"
    assert aggregated[12]["period"] == "2027-01"
    assert aggregated[23]["period"] == "2027-12"
    assert aggregated[0]["is_aggregated_year"] is False
    assert aggregated[24]["period_label"] == "2028"
    assert aggregated[24]["revenue"] == 1200.0
    assert aggregated[25]["period_label"] == "2029"
    assert aggregated[26]["period_label"] == "jan-set/2030"
    assert aggregated[26]["revenue"] == 900.0
    assert aggregated[26]["cumulative_business"] == float(len(timeline))


def test_get_consolidated_finance_defaults_start_date_to_first_equity_execution_or_revenue(monkeypatch):
    sections = _build_sections()
    sections["finance"]["analysis_params"]["start_date"] = ""
    sections["finance"]["sources_v2"] = [
        {
            "name": "Capital próprio",
            "amount": 1000.0,
            "type": "propria",
            "date": "2025.12",
        },
        {
            "name": "Financiamento bancário",
            "amount": 5000.0,
            "type": "financiamento",
            "date": "2025.11",
        },
    ]
    sections["execution"]["areas"]["operacional"]["items"][0]["payment_plan"]["start_date"] = "2026.02"
    sections["model"]["products"][0]["ramp_up_entries"] = [
        {"month_period": "2026.03", "percentage": 100},
    ]

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )

    consolidated = PlanService.get_consolidated_finance(12, 31)

    assert consolidated["params"]["start_date"] == "2025-12"
    assert consolidated["timeline"][0]["period"] == "2025-12"



def test_get_consolidated_finance_business_flow_includes_equity_sources(monkeypatch):
    sections = _build_sections()
    sections["finance"]["analysis_params"]["start_date"] = "2026.01"
    sections["finance"]["sources_v2"] = [
        {
            "name": "Capital próprio",
            "amount": 1000.0,
            "type": "propria",
            "date": "2026.01",
        }
    ]
    sections["finance"]["profit_distribution"] = []
    sections["execution"]["areas"] = {
        "operacional": {"items": []},
        "comercial": {"items": []},
        "admin": {"items": []},
    }
    sections["model"]["products"] = []

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )

    consolidated = PlanService.get_consolidated_finance(12, 31)

    assert consolidated["timeline"][0]["investment_flow"] == 1000.0
    assert consolidated["timeline"][0]["business_net_flow"] == 1000.0
    assert consolidated["timeline"][0]["cumulative_business"] == 1000.0


def test_get_consolidated_finance_applies_taxes_before_operating_result(monkeypatch):
    sections = _build_sections()
    sections["finance"]["profit_distribution"] = []
    sections["finance"]["taxes"] = [
        {"description": "CSLL", "percentage": 9.0, "base": "operating_result"},
        {"description": "IRPJ", "percentage": 15.0, "base": "operating_result"},
    ]

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )

    consolidated = PlanService.get_consolidated_finance(12, 31)
    first_month = consolidated["timeline"][0]

    assert first_month["operating_result_before_taxes"] == 250.0
    assert first_month["taxes_total"] == 60.0
    assert first_month["operating_result"] == 190.0
    assert consolidated["summary"]["total_taxes"] > 0


def test_get_consolidated_finance_calculates_additional_ir_base(monkeypatch):
    sections = _build_sections()
    sections["finance"]["profit_distribution"] = []
    sections["finance"]["taxes"] = [
        {"description": "Adicional IRPJ", "percentage": 10.0, "base": "operating_result_additional_ir"},
    ]
    sections["model"]["products"] = [
        {
            "name": "Produto Premium",
            "sale_price": 50000.0,
            "market_share_goal_monthly_units": 1,
            "variable_costs_value": 0.0,
            "variable_expenses_value": 0.0,
            "ramp_up_entries": [{"month_period": "2026.01", "percentage": 100}],
        }
    ]
    sections["execution"]["areas"] = {"operacional": {"items": []}}

    monkeypatch.setattr(
        PlanService,
        "get_plan",
        staticmethod(lambda plan_id, company_id: SimpleNamespace(id=plan_id, mode="implantation")),
    )
    monkeypatch.setattr(
        PlanService,
        "get_implantation_data",
        staticmethod(lambda plan_id, company_id, section_key: SimpleNamespace(content=sections.get(section_key, {}))),
    )

    consolidated = PlanService.get_consolidated_finance(12, 31)
    first_month = consolidated["timeline"][0]

    assert first_month["operating_result_before_taxes"] == 50000.0
    assert first_month["tax_base_values"]["operating_result_additional_ir"] == 30000.0
    assert first_month["taxes_total"] == 3000.0
    assert first_month["operating_result"] == 47000.0
