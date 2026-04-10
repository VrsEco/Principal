from __future__ import annotations

import src.intelligence.tools as tools_module
import src.intelligence.tools_domains.analytics_ops as analytics_ops
from services.analytics_read_model_service import AnalyticsReadModelService


def test_analytics_ops_plan_read_model_delegates_to_service(monkeypatch):
    monkeypatch.setattr(
        AnalyticsReadModelService,
        "get_plan_diagnostics_read_model",
        staticmethod(lambda company_id, plan_id: {"company_id": company_id, "plan_id": plan_id, "summary": {"ok": True}}),
    )

    result = analytics_ops.get_plan_diagnostics_read_model(company_id=31, plan_id=9)

    assert result["company_id"] == 31
    assert result["plan_id"] == 9


def test_tools_analytics_wrappers_delegate_to_domain(monkeypatch):
    calls = []

    monkeypatch.setattr(
        tools_module.analytics_ops_domain,
        "get_plan_diagnostics_read_model",
        lambda company_id, plan_id: calls.append(("plan", company_id, plan_id)) or {"ok": "plan"},
    )
    monkeypatch.setattr(
        tools_module.analytics_ops_domain,
        "get_team_workload_read_model",
        lambda company_id, department=None, employee_id=None: calls.append(("workload", company_id, department, employee_id)) or {"ok": "workload"},
    )
    monkeypatch.setattr(
        tools_module.analytics_ops_domain,
        "get_projects_execution_risk_read_model",
        lambda company_id, project_id=None, employee_id=None, status=None, limit=50: calls.append(("projects", company_id, project_id, employee_id, status, limit)) or {"ok": "projects"},
    )

    assert tools_module.get_plan_diagnostics_read_model.func(31, 7) == {"ok": "plan"}
    assert tools_module.get_team_workload_read_model.func(31, "Financeiro", 4) == {"ok": "workload"}
    assert tools_module.get_projects_execution_risk_read_model.func(31, 9, 4, "in_progress", 25) == {"ok": "projects"}
    assert calls == [
        ("plan", 31, 7),
        ("workload", 31, "Financeiro", 4),
        ("projects", 31, 9, 4, "in_progress", 25),
    ]
