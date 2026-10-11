"""Os serviços de backlog seguem o projeto operacional vigente; sem marcador, mantêm o padrão histórico."""

import pytest

from services import engineering_backlog_project_service as svc


@pytest.fixture()
def vigente(monkeypatch):
    monkeypatch.setattr(svc, "current_engineering_project_code", lambda fallback: "AA.J.21")


def test_helper_prefers_env_then_marker_then_fallback(monkeypatch):
    monkeypatch.setattr(svc, "current_engineering_project_code", lambda fallback: "AA.J.21")
    monkeypatch.delenv("X_PROJECT_CODE", raising=False)
    assert svc.backlog_project_code("AA.J.31", "X_PROJECT_CODE") == "AA.J.21"
    monkeypatch.setenv("X_PROJECT_CODE", "AA.J.99")
    assert svc.backlog_project_code("AA.J.31", "X_PROJECT_CODE") == "AA.J.99"
    monkeypatch.setattr(svc, "current_engineering_project_code", lambda fallback: fallback)
    monkeypatch.delenv("X_PROJECT_CODE")
    assert svc.backlog_project_code("AA.J.31", "X_PROJECT_CODE") == "AA.J.31"


@pytest.mark.parametrize(
    "module,cls",
    [
        ("ai_capability_backlog_service", "AICapabilityBacklogService"),
        ("monitoring_audit_request_service", "MonitoringAuditRequestService"),
        ("tool_backlog_service", "ToolBacklogService"),
        ("workflow_backlog_service", "WorkflowBacklogService"),
    ],
)
def test_class_services_resolve_the_current_project(vigente, module, cls):
    import importlib

    klass = getattr(importlib.import_module(f"services.{module}"), cls)
    assert klass.BACKLOG_PROJECT_CODE == "AA.J.31"  # último recurso
    assert klass.backlog_project_code() == "AA.J.21"


def test_agent_backlog_uses_current_project_and_keeps_the_robot_project(vigente, monkeypatch):
    from services import agent_backlog_service as agents

    monkeypatch.delenv("AGENT_BACKLOG_PROJECT_CODE", raising=False)
    assert agents._resolve_project_code("agent_action", {}) == "AA.J.21"
    assert agents._resolve_project_code("e2e_failure", {}) == agents.DEFAULT_ROBOT_FAILURE_PROJECT_CODE
    assert agents._resolve_project_code("agent_action", {"project_code": "AA.J.5"}) == "AA.J.5"


def test_workflow_gap_and_conversation_regression_follow_the_current_project(vigente, monkeypatch):
    from services import conversation_regression_runtime as runtime
    from services import workflow_gap_service as gaps

    monkeypatch.delenv("WORKFLOW_GAP_PROJECT_CODE", raising=False)
    assert gaps._workflow_gap_project_code() == "AA.J.21"
    monkeypatch.setattr(runtime, "backlog_project_code", lambda fallback, env_key=None: "AA.J.21")
    assert runtime.backlog_project_code("AA.J.31") == "AA.J.21"
