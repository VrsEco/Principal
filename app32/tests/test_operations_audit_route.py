import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import main as main_route


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

    app.register_blueprint(main_route.main_bp)
    return app


def test_operations_audit_panel_route_renders_template(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(
        main_route,
        "_resolve_active_company",
        lambda: SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
    )
    monkeypatch.setattr(
        main_route,
        "render_template",
        lambda template_name, **context: captured.update({"template_name": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/operations/audit")

    assert response.status_code == 200
    assert captured["template_name"] == "modules/operations/audit.html"
    assert captured["context"]["active_company"].id == 9


def test_operations_hub_route_was_removed():
    app = _build_app()

    response = app.test_client().get("/operations")

    assert response.status_code == 404


def test_operations_audit_api_returns_payload(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(
        main_route,
        "_resolve_active_company",
        lambda: SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
    )
    monkeypatch.setattr(main_route, "has_company_full_access", lambda company_id=None: True)
    monkeypatch.setattr(main_route, "is_platform_admin", lambda: False)
    monkeypatch.setattr(main_route, "get_accessible_company_ids", lambda: [9])
    monkeypatch.setattr(
        main_route.OperationalAuditService,
        "build_panel",
        classmethod(
            lambda cls, **kwargs: (
                {
                    "company_id": 9,
                    "summary": {"total": 1, "by_source": {"ai_mcp_runtime": 1}},
                    "events": [{"entity_id": 501, "source": "ai_mcp_runtime", "title": "Evento"}],
                    "approvals": [],
                    "analytics": {"cards": []},
                },
                None,
            )
        ),
    )

    response = app.test_client().get("/api/operations/audit?company_id=9")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["summary"]["total"] == 1
    assert payload["events"][0]["source"] == "ai_mcp_runtime"
