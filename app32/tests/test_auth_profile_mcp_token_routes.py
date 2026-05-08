import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import auth as auth_route


class _FakeUserMcpTokenService:
    def __init__(self):
        self.calls = []

    def get_status(self, user_id):
        self.calls.append(("status", user_id))
        return {
            "has_active_token": True,
            "token_masked": "mcpu_1****yz",
            "status": "active",
            "companies": [{"id": 12, "label": "AY - Poly Chargers", "selected": True}],
            "default_company_id": 12,
            "last_used_at": None,
            "last_client_name": None,
            "last_surface": "user",
            "last_company_id": 12,
            "expires_at": "2026-06-07T10:00:00",
            "days_to_expire": 30,
        }

    def generate_token(self, **kwargs):
        self.calls.append(("generate", kwargs))
        return {
            "token": "mcpu_token_teste",
            "status": self.get_status(kwargs["user_id"]),
            "config": {
                "text": "Token: mcpu_token_teste",
                "json": {"url": "https://app.gestaoversus.com.br/mcp/user/?company_id=12", "token": "mcpu_token_teste"},
            },
        }

    def renew_token(self, **kwargs):
        self.calls.append(("renew", kwargs))
        return self.generate_token(**kwargs)

    def revoke_token(self, **kwargs):
        self.calls.append(("revoke", kwargs))
        payload = self.get_status(kwargs["user_id"])
        payload["has_active_token"] = False
        payload["status"] = "missing"
        return payload

    def build_client_config(self, **kwargs):
        self.calls.append(("config", kwargs))
        return {
            "text": "config",
            "json": {"company_id": kwargs.get("company_id")},
            "technical_config_text": "config tecnica",
            "activation_prompt": "prompt ativar sapiens",
        }


def _build_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    app.register_blueprint(auth_route.auth_bp)
    return app


def _fake_user():
    return SimpleNamespace(
        id=10,
        name='Ana',
        email='ana@empresa.com',
        role='collaborator',
        is_authenticated=True,
        to_dict=lambda: {'id': 10, 'name': 'Ana'},
    )


def test_profile_mcp_token_status_route(monkeypatch):
    app = _build_app()
    fake_service = _FakeUserMcpTokenService()
    monkeypatch.setattr(auth_route, 'current_user', _fake_user())
    monkeypatch.setattr(auth_route, 'user_mcp_token_service', fake_service)

    response = app.test_client().get('/profile/mcp-token/status')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['has_active_token'] is True
    assert fake_service.calls[0] == ("status", 10)


def test_profile_mcp_token_generate_route(monkeypatch):
    app = _build_app()
    fake_service = _FakeUserMcpTokenService()
    monkeypatch.setattr(auth_route, 'current_user', _fake_user())
    monkeypatch.setattr(auth_route, 'user_mcp_token_service', fake_service)

    response = app.test_client().post(
        '/profile/mcp-token/generate',
        json={'company_id': 12, 'surface': 'user', 'client_name': 'Antigravity'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['token'] == 'mcpu_token_teste'
    generate_call = next(call for call in fake_service.calls if call[0] == 'generate')
    assert generate_call[1]['company_id'] == 12
    assert generate_call[1]['client_name'] == 'Antigravity'


def test_profile_mcp_token_revoke_route(monkeypatch):
    app = _build_app()
    fake_service = _FakeUserMcpTokenService()
    monkeypatch.setattr(auth_route, 'current_user', _fake_user())
    monkeypatch.setattr(auth_route, 'user_mcp_token_service', fake_service)

    response = app.test_client().post('/profile/mcp-token/revoke')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['has_active_token'] is False


def test_profile_mcp_token_config_route(monkeypatch):
    app = _build_app()
    fake_service = _FakeUserMcpTokenService()
    monkeypatch.setattr(auth_route, 'current_user', _fake_user())
    monkeypatch.setattr(auth_route, 'user_mcp_token_service', fake_service)

    response = app.test_client().post(
        '/profile/mcp-token/config',
        json={'company_id': 12, 'surface': 'user', 'client_name': 'Claude Code'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    config_call = next(call for call in fake_service.calls if call[0] == 'config')
    assert config_call[1]['company_id'] == 12
    assert config_call[1]['client_name'] == 'Claude Code'
