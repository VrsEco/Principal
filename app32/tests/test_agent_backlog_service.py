from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import agent_backlog_service


class _Task:
    id = 123
    project_id = 144

    @property
    def code(self):
        return "AA.J.19.1"


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
    assert "Prompt pronto para o Squad de Engenharia" in captured["notes"]
    assert "robot_error_id: " not in captured["notes"] or "Prompt pronto" in captured["notes"]


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
