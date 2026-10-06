"""MCP: create_project_task_secure — tenant, RBAC, idempotência, estado do projeto e catálogo."""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Company, Employee, Project, ProjectTask, User, db
from services.project_task_mcp_service import ProjectTaskMCPService
from src.core import mcp_surface_registry as registry
from src.intelligence.tools_domains import task_ops


@pytest.fixture()
def ctx():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[m.__table__ for m in (User, Company, Employee, Project, ProjectTask)])
        db.session.add_all([
            Company(id=9, name="Versus", client_code="AA"),
            Company(id=2, name="Outra", client_code="BB"),
        ])
        db.session.add_all([
            Employee(id=1, company_id=9, name="Ana Souza", status="active"),
            Employee(id=2, company_id=2, name="Bruno Lima", status="active"),
        ])
        db.session.flush()
        db.session.add_all([
            Project(id=26, company_id=9, name="Marketing Digital", code_sequence=26, status="in_progress"),
            Project(id=30, company_id=2, name="Projeto B", code_sequence=1, status="in_progress"),
            Project(id=31, company_id=9, name="Arquivado", code_sequence=31, status="archived"),
            Project(id=32, company_id=9, name="Cancelado", code_sequence=32, status="cancelled"),
            Project(id=33, company_id=9, name="Concluído", code_sequence=33, status="completed"),
            Project(id=34, company_id=9, name="Excluído", code_sequence=34, status="planned", is_deleted=True),
        ])
        db.session.commit()
        yield app


def _create(**overrides):
    kwargs = dict(
        company_id=9,
        user_id=7,
        task_name="Publicar calendário editorial",
        idempotency_key="k-1",
        project_code="AA.J.26",
    )
    kwargs.update(overrides)
    return ProjectTaskMCPService.create_task(**kwargs)


def test_creates_task_in_own_company_project_with_audit_and_listing(ctx):
    payload, error = _create(
        responsible_name="ana souza",
        due_date="2026-10-30",
        priority="high",
        description="Detalhar pauta",
    )

    assert error is None
    assert payload["project_id"] == 26
    assert payload["project_code"] == "AA.J.26"
    assert payload["idempotent_replay"] is False
    task = payload["task"]
    assert task["id"] and task["code"].startswith("AA.J.26.")
    assert task["what"] == "Publicar calendário editorial"
    assert task["who"] == "Ana Souza" and task["employee_id"] == 1
    assert task["status"] == "planned" and task["stage"] == "inbox" and task["priority"] == "high"

    stored = db.session.get(ProjectTask, task["id"])
    audit = stored.logs[0]
    assert audit["origin"] == "MCP" and audit["actor_user_id"] == 7
    assert audit["company_id"] == 9 and audit["project_id"] == 26 and audit["idempotency_key"] == "k-1"

    listed, list_error = ProjectTaskMCPService.list_tasks(company_id=9, project_id=26)
    assert list_error is None
    assert task["id"] in {item["id"] for item in listed["items"]}


def test_project_id_resolves_and_in_progress_status_maps_stage(ctx):
    payload, error = _create(project_code=None, project_id=26, status="in_progress")
    assert error is None
    assert payload["task"]["status"] == "in_progress" and payload["task"]["stage"] == "executing"


def test_project_of_another_company_is_denied(ctx):
    for kwargs in ({"project_code": None, "project_id": 30}, {"project_code": "BB.J.1"}):
        payload, error = _create(**kwargs)
        assert payload is None and error
    assert ProjectTask.query.count() == 0


def test_conflicting_project_id_and_code_are_rejected(ctx):
    payload, error = _create(project_id=31, project_code="AA.J.26")
    assert payload is None and "diferentes" in error


def test_responsible_must_belong_to_company(ctx):
    payload, error = _create(responsible_name="Bruno Lima")
    assert payload is None and "Responsável" in error
    assert ProjectTask.query.count() == 0


@pytest.mark.parametrize("project_id,expected", [
    (31, "archived"),
    (32, "cancelled"),
    (33, "completed"),
])
def test_closed_projects_are_refused(ctx, project_id, expected):
    payload, error = _create(project_code=None, project_id=project_id)
    assert payload is None and expected in error
    assert ProjectTask.query.count() == 0


def test_soft_deleted_project_is_refused(ctx):
    payload, error = _create(project_code=None, project_id=34)
    assert payload is None and "excluído" in error


@pytest.mark.parametrize("overrides", [
    {"task_name": "   "},
    {"task_name": "x" * 301},
    {"due_date": "31-31-2026"},
    {"priority": "critical"},
    {"status": "completed"},
    {"idempotency_key": " "},
    {"project_code": None, "project_id": None},
])
def test_invalid_fields_are_rejected_without_side_effects(ctx, overrides):
    payload, error = _create(**overrides)
    assert payload is None and error
    assert ProjectTask.query.count() == 0


def test_same_idempotency_key_and_payload_does_not_duplicate(ctx):
    first, _ = _create()
    second, error = _create()

    assert error is None
    assert second["idempotent_replay"] is True
    assert second["task"]["id"] == first["task"]["id"]
    assert ProjectTask.query.count() == 1


def test_same_idempotency_key_with_different_payload_is_rejected(ctx):
    _create()
    payload, error = _create(task_name="Outro título")
    assert payload is None and "idempotency_key" in error
    assert ProjectTask.query.count() == 1


def _patch_policy(monkeypatch, *, allowed, company_id=9, reason="negado"):
    monkeypatch.setattr(
        task_ops,
        "_authorize_project_task_mcp",
        lambda **kwargs: (
            {"user_id": 7},
            SimpleNamespace(
                allowed=allowed,
                reason=reason,
                resolved_company_id=company_id,
                to_audit_event=lambda: {"allowed": allowed},
            ),
        ),
    )
    monkeypatch.setattr(
        task_ops,
        "evaluate_mutation_limit",
        lambda **kwargs: SimpleNamespace(allowed=True, to_dict=lambda: {}),
    )
    recorded = []
    monkeypatch.setattr(task_ops, "record_mutation_success", lambda **kwargs: recorded.append(kwargs))
    return recorded


def test_domain_tool_denied_by_policy_does_not_create(ctx, monkeypatch):
    recorded = _patch_policy(monkeypatch, allowed=False)
    result = task_ops.create_project_task_secure(
        task_name="Sem permissão", idempotency_key="k-x", project_code="AA.J.26", company_id=9
    )
    assert result["success"] is False and result["error"] == "negado"
    assert ProjectTask.query.count() == 0 and recorded == []


def test_domain_tool_audits_once_and_replay_is_not_recounted(ctx, monkeypatch):
    recorded = _patch_policy(monkeypatch, allowed=True)
    args = dict(task_name="Auditada", idempotency_key="k-a", project_code="AA.J.26", company_id=9)

    first = task_ops.create_project_task_secure(**args)
    replay = task_ops.create_project_task_secure(**args)

    assert first["success"] and replay["success"] and replay["idempotent_replay"] is True
    assert ProjectTask.query.count() == 1
    assert len(recorded) == 1
    metadata = recorded[0]["metadata"]
    assert metadata["origin"] == "MCP" and metadata["actor_user_id"] == 7
    assert metadata["project_id"] == 26 and metadata["idempotency_key"] == "k-a"


def test_domain_tool_requires_task_create_permission_from_real_policy(ctx, monkeypatch):
    monkeypatch.setattr(
        task_ops,
        "_build_mcp_principal",
        lambda company_id: {
            "user_id": 7,
            "company_id": company_id,
            "role": "cliente",
            "channel": "claude_code",
            "permissions": (),
            "accessible_company_ids": (9,),
        },
    )
    result = task_ops.create_project_task_secure(
        task_name="Sem RBAC", idempotency_key="k-r", project_code="AA.J.26", company_id=9
    )
    assert result["success"] is False
    assert ProjectTask.query.count() == 0


def test_tool_is_discoverable_in_projects_domain_with_human_gate(monkeypatch):
    capability = registry.catalog.get_tool_capability("create_project_task_secure")
    assert capability.domain == "projects"
    assert capability.human_gate is True
    assert capability.permissions == ("project.task.create",)

    assert "create_project_task_secure" in registry.PILOT_PROJECT_TASK_MUTATION_TOOL_NAMES
    assert "create_project_task_secure" not in registry.PILOT_USER_TOOL_NAMES

    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda permission: True)
    monkeypatch.setattr(
        "src.core.mcp_http_auth.get_http_request_identity",
        lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user")),
    )
    manifest = registry.get_unified_manifest(domain="projects", include_tools=True)
    names = {tool["name"] for tool in manifest["tools"]}
    assert {"list_project_tasks_secure", "create_project_task_secure"} <= names

    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda permission: False)
    manifest = registry.get_unified_manifest(domain="projects", include_tools=True)
    assert "create_project_task_secure" not in {tool["name"] for tool in manifest["tools"]}
