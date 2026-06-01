import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import configs as configs_route


class _Task:
    id = 77
    task_code = "AA.J.31.77"


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


def test_e2e_operations_center_frontend_state_route(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    fake_state = {"summary": {"total_runs": 3, "failed_runs": 1}, "latest_runs": [], "execution_modes": [], "filters": {}, "system_actions": {}, "suite_catalog": [], "partial_suite_catalog": [], "supervised_executions": [], "runbooks": [], "commands": [], "latest_by_mode": [], "latest_diff": {"status": "stable"}, "backlog_candidates": []}

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.E2EOperationsCenterService, "build_frontend_state", lambda company=None: fake_state)

    response = app.test_client().get("/api/configs/qa/e2e/frontend-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["state"]["summary"]["total_runs"] == 3


def test_e2e_operations_center_execution_create_route(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    fake_execution = {"execution_id": "exec-1", "status": "running"}

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.E2ESupervisedExecutionService,
        "start_execution",
        lambda suite_id, environment: {**fake_execution, "suite_id": suite_id, "environment": environment},
    )

    response = app.test_client().post(
        "/api/configs/qa/e2e/executions",
        json={"suite_id": "smoke_real_navigation", "environment": "DEV_FULL"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["execution"]["environment"] == "DEV_FULL"


def test_e2e_operations_center_execution_list_route(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.E2ESupervisedExecutionService,
        "list_executions",
        lambda: [{"execution_id": "exec-1", "status": "passed"}],
    )

    response = app.test_client().get("/api/configs/qa/e2e/executions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["executions"][0]["execution_id"] == "exec-1"


def test_e2e_operations_center_run_download_and_backlog_sync_routes(monkeypatch, tmp_path):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"run_id":"run-1"}', encoding='utf-8')
    backlog_path = tmp_path / "backlog_candidates.json"
    backlog_path.write_text('[]', encoding='utf-8')
    artifact_path = tmp_path / "trace.zip"
    artifact_path.write_text('trace', encoding='utf-8')

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.E2EOperationsCenterService, "get_run_detail", lambda run_id: {"run_id": run_id})

    def _resolve(run_id, kind, artifact_index=None):
        if kind == 'manifest':
            return manifest_path
        if kind == 'backlog_candidates':
            return backlog_path
        return artifact_path

    monkeypatch.setattr(configs_route.E2EOperationsCenterService, "resolve_run_file", _resolve)
    monkeypatch.setattr(
        configs_route.E2EOperationsCenterService,
        "sync_backlog_candidates",
        lambda run_id, user_id, company_id, create_task_fn: {"created": [{"task_id": 77, "task_code": "AA.J.31.77"}], "errors": [], "requested": 1},
    )
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=5))

    response_manifest = app.test_client().get("/api/configs/qa/e2e/runs/run-1/manifest")
    response_backlog = app.test_client().get("/api/configs/qa/e2e/runs/run-1/backlog-candidates")
    response_artifact = app.test_client().get("/api/configs/qa/e2e/runs/run-1/artifacts/0")
    response_sync = app.test_client().post("/api/configs/qa/e2e/runs/run-1/backlog-sync")

    assert response_manifest.status_code == 200
    assert response_backlog.status_code == 200
    assert response_artifact.status_code == 200
    assert response_sync.status_code == 201
    assert response_sync.get_json()["result"]["created"][0]["task_code"] == "AA.J.31.77"


def test_e2e_operations_center_template_route(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    fake_state = {
        "summary": {"total_runs": 3, "failed_runs": 1, "backlog_candidates": 2},
        "active_company": {"client_code": "VRS", "name": "Versus"},
        "system_actions": {
            "inventory_scan": {"suite_id": "inventory_system_scan", "label": "Checar e mapear todo o sistema"},
            "full_validation": {"suite_id": "full_system_validation", "label": "Fazer teste completo do sistema"},
            "partial_execution": {"label": "Fazer teste parcial"},
        },
        "execution_modes": [{"label": "DEV_FULL", "description": "Execução destrutiva", "destructive": True}],
        "filters": {"environments": ["ALL", "DEV_FULL"], "statuses": ["ALL", "passed"], "suites": ["ALL", "smoke_real_navigation"]},
        "latest_runs": [],
        "latest_by_mode": [],
        "latest_diff": {"status": "stable", "regressions": [], "recovered": [], "new_journeys": []},
        "backlog_candidates": [],
        "suite_catalog": [],
        "partial_suite_catalog": [],
        "supervised_executions": [],
        "runbooks": [],
        "commands": [],
    }

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.E2EOperationsCenterService, "build_frontend_state", lambda company=None: fake_state)
    monkeypatch.setattr(
        configs_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|{context['state']['execution_modes'][0]['label']}|Central de Testes E2E|{context['state']['summary']['backlog_candidates']}",
    )

    response = app.test_client().get("/qa/e2e")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Central de Testes E2E" in html
    assert "DEV_FULL" in html
    assert "2" in html
