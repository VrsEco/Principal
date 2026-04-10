from __future__ import annotations

import pytest

from services.analytics_read_model_service import AnalyticsReadModelService
from services.plan_service import PlanService


def test_plan_read_model_uses_plan_service(monkeypatch):
    monkeypatch.setattr(
        PlanService,
        "get_plan_dashboard_data",
        staticmethod(
            lambda plan_id, company_id: {
                "plan": {"id": plan_id, "title": "Plano X"},
                "stats": {"progress_pct": 60, "completed_sections": 3},
                "sections": [
                    {"key": "participants", "status": "completed"},
                    {"key": "finance", "status": "pending"},
                    {"key": "projects", "status": "in_progress"},
                ],
            }
        ),
    )

    result = AnalyticsReadModelService.get_plan_diagnostics_read_model(company_id=31, plan_id=8)

    assert result["company_id"] == 31
    assert result["plan_id"] == 8
    assert result["insights"]["pending_sections"] == 1
    assert result["insights"]["in_progress_sections"] == 1


def test_plan_read_model_blocks_company_outside_accessible_scope(monkeypatch):
    called = False

    def fake_dashboard(plan_id, company_id):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(PlanService, "get_plan_dashboard_data", staticmethod(fake_dashboard))

    with pytest.raises(PermissionError, match="escopo analítico"):
        AnalyticsReadModelService.get_plan_diagnostics_read_model(
            company_id=99,
            plan_id=8,
            accessible_company_ids=[31],
        )

    assert called is False


def test_workload_read_model_blocks_company_outside_accessible_scope():
    with pytest.raises(PermissionError, match="escopo analítico"):
        AnalyticsReadModelService.get_team_workload_read_model(
            company_id=99,
            accessible_company_ids=[31],
        )


def test_projects_execution_risk_read_model_blocks_company_outside_accessible_scope():
    with pytest.raises(PermissionError, match="escopo analítico"):
        AnalyticsReadModelService.get_projects_execution_risk_read_model(
            company_id=99,
            accessible_company_ids=[31],
        )
