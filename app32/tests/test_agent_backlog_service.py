from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import agent_backlog_service


class _Task:
    id = 123


def test_agent_backlog_routes_e2e_failure_to_robot_failure_project(monkeypatch):
    captured = {}

    def fake_create_project_task(**kwargs):
        captured.update(kwargs)
        return {"task": _Task()}, None

    monkeypatch.setattr(agent_backlog_service.ProjectTaskService, "create_project_task", fake_create_project_task)

    task, error = agent_backlog_service.create_backlog_task(
        source_type="e2e_failure",
        title="Falha E2E: financeiro",
        description="Falha detectada pelo robô.",
        user_id=7,
        company_id=9,
        metadata={"run_id": "run-1"},
    )

    assert error is None
    assert task is not None
    assert captured["project_code"] == "AA.J.19"


def test_agent_backlog_accepts_project_code_override(monkeypatch):
    captured = {}

    def fake_create_project_task(**kwargs):
        captured.update(kwargs)
        return {"task": _Task()}, None

    monkeypatch.setattr(agent_backlog_service.ProjectTaskService, "create_project_task", fake_create_project_task)

    _, error = agent_backlog_service.create_backlog_task(
        source_type="e2e_failure",
        title="Falha E2E: override",
        description="Falha detectada pelo robô.",
        user_id=7,
        company_id=9,
        metadata={"project_code": "AA.J.99"},
    )

    assert error is None
    assert captured["project_code"] == "AA.J.99"
