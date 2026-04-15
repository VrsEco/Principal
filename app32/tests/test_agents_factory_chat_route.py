import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import agents as agents_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["LOGIN_DISABLED"] = True
    app.register_blueprint(agents_route.agents_bp)
    return app


def test_agents_chat_uses_service_boundary(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, role="admin"))

    captured = {}

    def _fake_chat_with_agent(**kwargs):
        captured.update(kwargs)
        return {"response": "ok", "agent": "factory", "thread_id": "web_7_factory", "menu_metadata": {}}

    monkeypatch.setattr(agents_route.AgentConversationService, "chat_with_agent", staticmethod(_fake_chat_with_agent))

    with app.test_request_context('/api/agents/chat', method='POST', json={"message": "diagnosticar factory", "contact": "factory"}):
        session['active_company_id'] = 31
        response = agents_route.agents_chat.__wrapped__()

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["agent"] == "factory"
    assert captured["contact"] == "factory"
    assert captured["company_id"] == 31


def test_agents_contacts_includes_factory(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(agents_route, "_is_platform_admin_local", lambda: False)

    with app.test_request_context('/api/agents/contacts', method='GET'):
        session['active_company_id'] = 31
        response = agents_route.get_agents_contacts.__wrapped__()

    payload = response.get_json()
    assert payload["success"] is True
    assert any(item["id"] == "factory" for item in payload["contacts"])
