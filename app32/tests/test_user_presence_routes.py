import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask
from werkzeug.exceptions import Forbidden

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import configs as configs_route


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config.update(TESTING=True, LOGIN_DISABLED=True, SECRET_KEY="test-secret")
    app.register_blueprint(configs_route.configs_bp)
    return app


def test_presence_admin_context_rejects_cross_tenant_company(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: SimpleNamespace(id=7, name="Empresa 7"))
    monkeypatch.setattr(configs_route, "is_platform_admin", lambda: False)
    monkeypatch.setattr(configs_route, "has_company_full_access", lambda company_id: company_id == 7)

    with app.test_request_context("/configs/system/presence?company_id=8"):
        with pytest.raises(Forbidden):
            configs_route._resolve_presence_admin_context()


def test_presence_state_api_always_passes_explicit_company_id(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(configs_route, "_resolve_presence_admin_context", lambda: (17, []))

    def _fake_list(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "summary": {}, "items": []}

    monkeypatch.setattr(configs_route.UserPresenceService, "list_company_presence", _fake_list)
    response = app.test_client().get("/api/configs/system/presence?company_id=999")

    assert response.status_code == 200
    assert captured["company_id"] == 17
    assert response.get_json()["presence"]["company_id"] == 17


def test_presence_heartbeat_uses_active_company_from_signed_session(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=23))
    monkeypatch.setattr(configs_route, "is_platform_admin", lambda: False)
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: [41])

    def _fake_heartbeat(**kwargs):
        captured.update(kwargs)
        return {"status": "online", "company_id": kwargs["company_id"]}

    monkeypatch.setattr(configs_route.UserPresenceService, "heartbeat", _fake_heartbeat)
    client = app.test_client()
    with client.session_transaction() as flask_session:
        flask_session["active_company_id"] = 41

    response = client.post(
        "/api/presence/heartbeat",
        json={},
        headers={"Origin": "http://localhost"},
    )

    assert response.status_code == 200
    assert captured["user_id"] == 23
    assert captured["company_id"] == 41


def test_presence_page_and_system_card_are_linked():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    system_template = open(os.path.join(root, "templates", "configs_system.html"), encoding="utf-8").read()
    presence_template = open(os.path.join(root, "templates", "configs_user_presence.html"), encoding="utf-8").read()
    base_template = open(os.path.join(root, "templates", "base.html"), encoding="utf-8").read()

    assert "configs.user_presence_page" in system_template
    assert "Usuários Online" in system_template
    assert "/api/configs/system/presence" in presence_template
    assert "user_presence.js" in base_template
    assert "current_user.is_authenticated" in base_template
