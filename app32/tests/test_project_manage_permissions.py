import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import projects as project_routes


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    return app


def test_project_manage_exposes_task_edit_capability_for_collaborator_with_project_edit(monkeypatch):
    app = _build_app()
    fake_project = SimpleNamespace(id=9, owner="Gestor X")
    fake_company = SimpleNamespace(id=2, name="Gas Evolution")

    monkeypatch.setattr(project_routes, "_get_project_page_with_access", lambda project_id: (fake_project, fake_company))
    monkeypatch.setattr(project_routes, "is_collaborator_in_company", lambda company_id: True)
    monkeypatch.setattr(project_routes, "can_manage_project_tasks", lambda company_id: company_id == 2)
    monkeypatch.setattr(project_routes, "render_template", lambda template, **ctx: {"template": template, "context": ctx})

    with app.test_request_context("/projects/9/manage"):
        response = project_routes.project_manage.__wrapped__(9)

    assert response["template"] == "modules/projects/project_manage.html"
    assert response["context"]["is_collaborator"] is True
    assert response["context"]["can_edit_tasks"] is True


def test_project_manage_template_uses_task_edit_capability_flag():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "projects",
            "project_manage.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "CAN_EDIT_TASKS" in content
    assert "{% if can_edit_tasks %}" in content
    assert "card.draggable = CAN_EDIT_TASKS && !isHumanGateTask;" in content
    assert "if (!CAN_EDIT_TASKS) {" in content


def test_project_analysis_exposes_task_edit_capability_for_collaborator_with_project_edit(monkeypatch):
    app = _build_app()
    fake_company = SimpleNamespace(id=2, name="Gas Evolution")

    monkeypatch.setattr(project_routes, "get_active_company", lambda: fake_company)
    monkeypatch.setattr(project_routes, "is_collaborator_in_company", lambda company_id: True)
    monkeypatch.setattr(project_routes, "can_manage_project_tasks", lambda company_id: company_id == 2)
    monkeypatch.setattr(project_routes, "render_template", lambda template, **ctx: {"template": template, "context": ctx})

    with app.test_request_context("/projects/analysis"):
        response = project_routes.project_analysis.__wrapped__()

    assert response["template"] == "modules/projects/project_analysis.html"
    assert response["context"]["is_collaborator"] is True
    assert response["context"]["can_edit_tasks"] is True


def test_project_analysis_template_uses_task_edit_capability_flag():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "projects",
            "project_analysis.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "CAN_EDIT_TASKS" in content
    assert "{% if can_edit_tasks %}" in content


def test_projects_list_exposes_create_flag_for_collaborator_with_operational_access(monkeypatch):
    app = _build_app()
    fake_company = SimpleNamespace(id=2, name="Gas Evolution")

    monkeypatch.setattr(project_routes, "get_active_company", lambda: fake_company)
    monkeypatch.setattr(project_routes, "is_collaborator_in_company", lambda company_id: True)
    monkeypatch.setattr(project_routes, "can_create_projects", lambda company_id: company_id == 2)
    monkeypatch.setattr(project_routes, "render_template", lambda template, **ctx: {"template": template, "context": ctx})

    with app.test_request_context("/projects"):
        response = project_routes.projects_list.__wrapped__()

    assert response["template"] == "modules/projects/projects_v2.html"
    assert response["context"]["is_collaborator"] is True
    assert response["context"]["can_create_projects"] is True


def test_projects_list_template_uses_project_create_flag():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "projects",
            "projects_v2.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "can_create_projects" in content
    assert "{% if can_create_projects %}" in content


def test_project_manage_exposes_task_edit_capability_for_collaborator_without_project_edit(monkeypatch):
    app = _build_app()
    fake_project = SimpleNamespace(id=9, owner="Gestor X")
    fake_company = SimpleNamespace(id=2, name="Gas Evolution")

    monkeypatch.setattr(project_routes, "_get_project_page_with_access", lambda project_id: (fake_project, fake_company))
    monkeypatch.setattr(project_routes, "is_collaborator_in_company", lambda company_id: True)
    monkeypatch.setattr(project_routes, "can_manage_project_tasks", lambda company_id: company_id == 2)
    monkeypatch.setattr(project_routes, "render_template", lambda template, **ctx: {"template": template, "context": ctx})

    with app.test_request_context("/projects/9/manage"):
        response = project_routes.project_manage.__wrapped__(9)

    assert response["template"] == "modules/projects/project_manage.html"
    assert response["context"]["is_collaborator"] is True
    assert response["context"]["can_edit_tasks"] is True
