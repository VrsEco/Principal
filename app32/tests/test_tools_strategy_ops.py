from __future__ import annotations

from types import SimpleNamespace

import src.intelligence.tools as tools_module
import src.intelligence.tools_domains.strategy_ops as strategy_ops
from services.plan_service import PlanService


def test_strategy_ops_list_plans_uses_active_company(monkeypatch):
    captured = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_list(company_id, mode):
        captured["company_id"] = company_id
        captured["mode"] = mode
        return [SimpleNamespace(id=1, title="Plano A", mode="growth", progress=80)]

    monkeypatch.setattr(PlanService, "list_plans", staticmethod(fake_list))

    result = strategy_ops.list_plans(mode="growth")

    assert captured == {"company_id": 31, "mode": "growth"}
    assert "ID: 1" in result
    assert "Plano A" in result


def test_strategy_ops_list_plans_honors_explicit_company(monkeypatch):
    captured = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_list(company_id, mode):
        captured["company_id"] = company_id
        captured["mode"] = mode
        return [SimpleNamespace(id=2, title="Plano B", mode="implantation", progress=30)]

    monkeypatch.setattr(PlanService, "list_plans", staticmethod(fake_list))

    result = strategy_ops.list_plans(company_id=10, mode="implantation")

    assert captured == {"company_id": 10, "mode": "implantation"}
    assert "Plano B" in result


def test_strategy_ops_update_plan_section_validates_plan_in_active_company(monkeypatch):
    calls = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_get_plan(plan_id, company_id):
        calls["get_plan"] = (plan_id, company_id)
        return SimpleNamespace(id=plan_id, mode="implantation")

    def fake_update(plan_id, section_key, status):
        calls["update"] = (plan_id, section_key, status)

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(fake_get_plan))
    monkeypatch.setattr(PlanService, "update_section_status", staticmethod(fake_update))

    result = strategy_ops.update_plan_section(7, "finance", "completed")

    assert calls == {
        "get_plan": (7, 31),
        "update": (7, "finance", "completed"),
    }
    assert "Sucesso" in result


def test_strategy_ops_update_plan_section_honors_explicit_company(monkeypatch):
    calls = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_get_plan(plan_id, company_id):
        calls["get_plan"] = (plan_id, company_id)
        return SimpleNamespace(id=plan_id, mode="implantation")

    def fake_update(plan_id, section_key, status):
        calls["update"] = (plan_id, section_key, status)

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(fake_get_plan))
    monkeypatch.setattr(PlanService, "update_section_status", staticmethod(fake_update))

    result = strategy_ops.update_plan_section(14, "participants", "in_progress", company_id=10)

    assert calls == {
        "get_plan": (14, 10),
        "update": (14, "participants", "in_progress"),
    }
    assert "Sucesso" in result


def test_strategy_ops_update_plan_section_rejects_invalid_section_key(monkeypatch):
    calls = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_get_plan(plan_id, company_id):
        calls["get_plan"] = (plan_id, company_id)
        return SimpleNamespace(id=plan_id, mode="implantation")

    def fake_update(plan_id, section_key, status):
        calls["update"] = (plan_id, section_key, status)

    monkeypatch.setattr(PlanService, "get_plan", staticmethod(fake_get_plan))
    monkeypatch.setattr(PlanService, "update_section_status", staticmethod(fake_update))

    result = strategy_ops.update_plan_section(14, "overview", "completed", company_id=10)

    assert calls == {"get_plan": (14, 10)}
    assert "section_key 'overview' inválida" in result
    assert "participants, alignment, model, execution, finance" in result


def test_strategy_ops_update_plan_section_blocks_missing_plan(monkeypatch):
    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)
    monkeypatch.setattr(PlanService, "get_plan", staticmethod(lambda plan_id, company_id: None))

    result = strategy_ops.update_plan_section(999, "finance", "completed")

    assert result == "Plano 999 não encontrado."


def test_strategy_ops_update_plan_section_rejects_invalid_status(monkeypatch):
    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    result = strategy_ops.update_plan_section(999, "finance", "done")

    assert "Erro ao atualizar seção" in result
    assert "String should match pattern" in result


def test_strategy_ops_get_plan_diagnostics_honors_explicit_company(monkeypatch):
    captured = {}

    monkeypatch.setattr(strategy_ops, "get_active_company_id", lambda: 31)

    def fake_dashboard(plan_id, company_id):
        captured["call"] = (plan_id, company_id)
        return {
            "plan": {"title": "Plano B", "mode": "growth"},
            "stats": {"progress_pct": 55},
            "sections": [{"title": "Participantes", "status": "in_progress"}],
        }

    monkeypatch.setattr(PlanService, "get_plan_dashboard_data", staticmethod(fake_dashboard))

    result = strategy_ops.get_plan_diagnostics(14, company_id=10)

    assert captured["call"] == (14, 10)
    assert "Plano B" in result


def test_tools_strategy_wrappers_delegate_to_strategy_domain(monkeypatch):
    calls = []

    monkeypatch.setattr(
        tools_module.strategy_ops_domain,
        "list_plans",
        lambda company_id=None, mode=None: calls.append(("list", company_id, mode)) or "plans-ok",
    )
    monkeypatch.setattr(
        tools_module.strategy_ops_domain,
        "get_plan_diagnostics",
        lambda plan_id, company_id=None: calls.append(("diagnostics", plan_id, company_id)) or "diag-ok",
    )
    monkeypatch.setattr(
        tools_module.strategy_ops_domain,
        "update_plan_section",
        lambda plan_id, section_key, status="completed", company_id=None: calls.append(("update", plan_id, section_key, status, company_id)) or "update-ok",
    )

    assert tools_module.list_plans.func(10, "growth") == "plans-ok"
    assert tools_module.get_plan_diagnostics.func(7, 10) == "diag-ok"
    assert tools_module.update_plan_section.func(7, "finance", "completed", 10) == "update-ok"
    assert calls == [
        ("list", 10, "growth"),
        ("diagnostics", 7, 10),
        ("update", 7, "finance", "completed", 10),
    ]
