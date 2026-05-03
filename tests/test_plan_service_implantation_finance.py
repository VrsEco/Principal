from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app32"))

from services.plan_service import PlanService


def _build_section(content):
    return SimpleNamespace(content=content)


def test_get_consolidated_finance_expands_indefinite_monthly_contract_to_flow(monkeypatch):
    model_content = {"products": []}
    execution_content = {
        "areas": {
            "operacional": {
                "items": [
                    {
                        "description": "Gestor Comercial",
                        "classification": "contratação",
                        "payments": [],
                        "payment_plan": {
                            "mode": "monthly_contract",
                            "start_date": "2026-02",
                            "end_date": None,
                            "monthly_amount": 1000,
                        },
                    }
                ]
            }
        }
    }
    finance_content = {
        "analysis_params": {
            "period_months": 3,
            "start_date": "2026.01",
            "opportunity_cost_annual": 12.0,
        }
    }

    sections = {
        "model": _build_section(model_content),
        "execution": _build_section(execution_content),
        "finance": _build_section(finance_content),
    }

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(lambda *_args, **_kwargs: SimpleNamespace(mode="implantation")))
    monkeypatch.setattr(PlanService, "get_implantation_data", staticmethod(lambda _plan_id, _company_id, section_key: sections.get(section_key)))

    consolidated = PlanService.get_consolidated_finance(12, 9)

    assert [row["period"] for row in consolidated["timeline"]] == ["2026-01", "2026-02", "2026-03"]
    assert [row["fixed_costs"] for row in consolidated["timeline"]] == [0, 1000, 1000]


def test_normalize_period_supports_brazilian_full_date():
    assert PlanService._normalize_period("01/07/2026") == "2026-07"
    assert PlanService._normalize_period("2026-07-01") == "2026-07"


def test_get_consolidated_finance_limits_defined_monthly_contract_to_end_date(monkeypatch):
    execution_content = {
        "areas": {
            "comercial": {
                "items": [
                    {
                        "description": "SDR Terceirizado",
                        "classification": "contratação",
                        "payments": [],
                        "payment_plan": {
                            "mode": "monthly_contract",
                            "start_date": "2026-02",
                            "end_date": "2026-03",
                            "monthly_amount": 500,
                        },
                    }
                ]
            }
        }
    }
    finance_content = {
        "analysis_params": {
            "period_months": 4,
            "start_date": "2026.01",
        }
    }

    sections = {
        "model": _build_section({"products": []}),
        "execution": _build_section(execution_content),
        "finance": _build_section(finance_content),
    }

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(lambda *_args, **_kwargs: SimpleNamespace(mode="implantation")))
    monkeypatch.setattr(PlanService, "get_implantation_data", staticmethod(lambda _plan_id, _company_id, section_key: sections.get(section_key)))

    consolidated = PlanService.get_consolidated_finance(12, 9)

    assert [row["fixed_expenses"] for row in consolidated["timeline"]] == [0, 500, 500, 0]


def test_get_consolidated_finance_monthly_contract_accepts_brazilian_date_format(monkeypatch):
    execution_content = {
        "areas": {
            "operacional": {
                "items": [
                    {
                        "description": "Suporte",
                        "classification": "contratação",
                        "payments": [],
                        "payment_plan": {
                            "mode": "monthly_contract",
                            "start_date": "01/07/2026",
                            "end_date": "01/08/2026",
                            "monthly_amount": 700,
                        },
                    }
                ]
            }
        }
    }
    finance_content = {
        "analysis_params": {
            "period_months": 3,
            "start_date": "2026.07",
        }
    }

    sections = {
        "model": _build_section({"products": []}),
        "execution": _build_section(execution_content),
        "finance": _build_section(finance_content),
    }

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(lambda *_args, **_kwargs: SimpleNamespace(mode="implantation")))
    monkeypatch.setattr(PlanService, "get_implantation_data", staticmethod(lambda _plan_id, _company_id, section_key: sections.get(section_key)))

    consolidated = PlanService.get_consolidated_finance(12, 9)

    assert [row["period"] for row in consolidated["timeline"]] == ["2026-07", "2026-08", "2026-09"]
    assert [row["fixed_costs"] for row in consolidated["timeline"]] == [700, 700, 0]


def test_get_consolidated_finance_keeps_investment_with_explicit_payments(monkeypatch):
    execution_content = {
        "areas": {
            "admin": {
                "items": [
                    {
                        "description": "Servidor",
                        "item_type": "ti",
                        "classification": "aquisição",
                        "payments": [
                            {"date": "2026-01-10", "amount": 1200},
                            {"date": "2026-02-10", "amount": 800},
                        ],
                    }
                ]
            }
        }
    }
    finance_content = {
        "analysis_params": {
            "period_months": 2,
            "start_date": "2026.01",
        }
    }

    sections = {
        "model": _build_section({"products": []}),
        "execution": _build_section(execution_content),
        "finance": _build_section(finance_content),
    }

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(lambda *_args, **_kwargs: SimpleNamespace(mode="implantation")))
    monkeypatch.setattr(PlanService, "get_implantation_data", staticmethod(lambda _plan_id, _company_id, section_key: sections.get(section_key)))

    consolidated = PlanService.get_consolidated_finance(12, 9)

    assert consolidated["summary"]["total_fixed_assets"] == 2000
    assert [row["investment"] for row in consolidated["timeline"]] == [1200, 800]
    assert consolidated["investments"]["fixed_asset_rows"] == [
        {"description": "Servidor", "item_type": "ti", "date": "2026-01", "amount": 1200.0},
        {"description": "Servidor", "item_type": "ti", "date": "2026-02", "amount": 800.0},
    ]
