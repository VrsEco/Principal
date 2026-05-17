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


def test_instruction_registry_frontend_state_api_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.InstructionRegistryService,
        "build_frontend_state",
        lambda: {
            "summary": {"entries": 3, "active_entries": 2, "tenant_overrides": 1, "channels": ["stable"], "runtimes": ["squad_cliente"]},
            "entries": [],
            "recent_audit": [],
            "recent_changes": [],
            "supported_runtimes": ["squad_cliente", "squad_versus", "engineering"],
            "supported_channels": ["stable", "beta", "hotfix"],
            "supported_environments": ["production", "staging", "development"],
        },
    )

    response = app.test_client().get("/api/configs/ai/mcp/instruction-registry/frontend-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["state"]["summary"]["entries"] == 3
    assert "engineering" in payload["state"]["supported_runtimes"]
    assert "production" in payload["state"]["supported_environments"]


def test_instruction_registry_promote_api_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.InstructionRegistryService,
        "promote_entry",
        lambda payload, actor_user_id=None: SimpleNamespace(
            to_dict=lambda: {
                "id": 9,
                "runtime_profile": "squad_cliente",
                "channel": payload["target_channel"],
                "status": payload["target_status"],
            }
        ),
    )

    class _FakeUser:
        id = 7

    monkeypatch.setattr(configs_route, "current_user", _FakeUser())

    response = app.test_client().post(
        "/api/configs/ai/mcp/instruction-registry/promote",
        json={
            "source_entry_id": 1,
            "target_channel": "stable",
            "target_status": "active",
            "target_rollout_status": "active",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["entry"]["channel"] == "stable"
