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
