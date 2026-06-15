import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import configs as configs_route


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

    app.register_blueprint(configs_route.configs_bp)
    return app


def test_robot_tests_center_page_route(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="M1 - Empresa de Testes Versus", client_code="M1")
    fake_state = {"company": {"id": 9}, "summary_cards": [], "test_packages": [], "areas": [], "errors": []}

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.RobotTestsCenterService, "build_overview_state", lambda active_company, company_id: fake_state)
    monkeypatch.setattr(
        configs_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|{context['state']['company']['id']}|Central do Robô de Testes",
    )

    response = app.test_client().get("/qa/robot-tests")

    assert response.status_code == 200
    assert "modules/operations/robot_tests_center.html" in response.get_data(as_text=True)
    assert "Central do Robô de Testes" in response.get_data(as_text=True)


def test_robot_tests_overview_api_is_tenant_scoped(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="M1 - Empresa de Testes Versus", client_code="M1")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.RobotTestsCenterService,
        "build_overview_state",
        lambda active_company, company_id: {"company": {"id": company_id}, "summary_cards": [{"label": "Erros abertos", "value": 0}]},
    )

    response = app.test_client().get("/api/qa/robot-tests/overview?company_id=9")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["state"]["company"]["id"] == 9


def test_robot_tests_run_create_api(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="M1 - Empresa de Testes Versus", client_code="M1")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.RobotTestsCenterService,
        "start_run",
        lambda package_key, suite_id, environment, company_id, user_id=None: {
            "package_key": package_key,
            "suite_id": suite_id or "full_system_validation",
            "environment": environment,
            "company_id": company_id,
            "user_id": user_id,
        },
    )

    response = app.test_client().post(
        "/api/qa/robot-tests/runs",
        json={"company_id": 9, "package_key": "complete", "environment": "PROD_SAFE"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["result"]["company_id"] == 9
    assert payload["result"]["suite_id"] == "full_system_validation"


def test_robot_tests_error_action_api(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="M1 - Empresa de Testes Versus", client_code="M1")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=5))
    monkeypatch.setattr(
        configs_route.RobotTestsCenterService,
        "handle_error_action",
        lambda error_id, action, company_id, user_id, create_task_fn: {
            "error_id": error_id,
            "action": action,
            "company_id": company_id,
            "user_id": user_id,
        },
    )

    response = app.test_client().post(
        "/api/qa/robot-tests/errors/run-1-0/actions",
        json={"company_id": 9, "action": "details"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["result"]["company_id"] == 9
