import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import processes as processes_route
from services.strategic_management_panel_service import _evaluate_indicator_status, _resolve_period


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(processes_route.processes_bp)
    return app


def _panel_payload(company_id=9):
    return {
        "company_id": company_id,
        "period": {"key": "month", "label": "Junho/2026", "start": "2026-06-01", "end": "2026-06-30"},
        "groups": [
            {
                "key": "strategic",
                "label": "Indicadores Estratégicos",
                "short_label": "Estratégicos",
                "subtitle": "Resultado e direção",
                "color": "#ef4444",
                "total": 1,
                "alerts_count": 1,
                "semaphore": {"green": 0, "yellow": 0, "red": 1, "blue": 0, "gray": 0},
                "subgroups": [],
            }
        ],
        "meetings": [],
        "actions": {},
        "generated_at": "2026-06-14T00:00:00",
    }


def test_strategic_management_panel_api_is_tenant_scoped(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        processes_route,
        "build_strategic_management_panel",
        lambda company_id, period=None: _panel_payload(company_id),
    )

    response = app.test_client().get("/api/companies/9/process-portal/strategic-management?period=month")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["company_id"] == 9
    assert payload["data"]["groups"][0]["key"] == "strategic"


def test_strategic_management_panel_short_route_redirects_to_active_company(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    with client.session_transaction() as session:
        session["active_company_id"] = 9

    response = client.get("/process-portal/strategic-management", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/companies/9/process-portal/strategic-management")


def test_strategic_management_panel_page_uses_executive_template(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        processes_route,
        "Company",
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda company_id: SimpleNamespace(id=company_id, name="Empresa Teste"))),
    )
    monkeypatch.setattr(processes_route, "build_strategic_management_panel", lambda company_id, period=None: _panel_payload(company_id))
    monkeypatch.setattr(
        processes_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|{context['company_id']}|{context['panel']['groups'][0]['short_label']}",
    )

    response = app.test_client().get("/companies/9/process-portal/strategic-management")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "modules/processes/strategic_management_panel.html" in body
    assert "|9|" in body
    assert "Estratégicos" in body


def test_period_resolution_keeps_context_as_filter_not_cadastro():
    period = _resolve_period("quarter")

    assert period["key"] == "quarter"
    assert period["start"] <= period["end"]
    assert "trimestre" in period["label"]


def test_indicator_status_requires_corrective_action_when_red():
    indicator = SimpleNamespace(polarity="positive")
    latest = SimpleNamespace(measured_value=70)
    goal = SimpleNamespace(goal_value=100)

    status = _evaluate_indicator_status(indicator, latest, goal)

    assert status["semaphore"] == "red"
    assert "ação corretiva governada" in status["detail"]


def test_process_portal_has_strategic_management_quick_access():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "process_portal_compact.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Painel de Gestão Estratégica" in content
    assert "strategic_management_panel_page" in content
    assert "Acesso Rápido" in content


def test_strategic_management_panel_action_modal_links_indicator_to_project_or_activity():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Nova atividade / projeto" in content
    assert "Escolha se a correção será um novo projeto ou uma atividade" in content
    assert "indicator_id" in content
    assert "process_id" in content
    assert "/api/projects/${projectId}/tasks" in content


def test_project_form_warns_to_create_activities_when_project_is_indicator_corrective():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "projects", "project_form_v2.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Projeto corretivo vinculado ao indicador" in content
    assert "Após criar o projeto, crie as atividades corretivas" in content
    assert "data.indicator_id" in content


def test_standard_sidebar_has_strategic_management_quick_access():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "partials", "sidebar_standard.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "/process-portal/strategic-management" in content
    assert "Painel de Gestão Estratégica" in content
