from __future__ import annotations

import os
import sys

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes.strategic_tree import strategic_tree_bp


class _User(UserMixin):
    id = 3
    role = "client"


class _Service:
    def list_trees(self, actor):
        return {"company_id": actor.company_id, "trees": []}

    def create_tree(self, actor, **kwargs):
        return {"company_id": actor.company_id, "tree": {"id": 1, "title": kwargs["title"]}, "root": {"id": 2}}


@pytest.fixture()
def route_client(monkeypatch):
    import api.routes.strategic_tree as module

    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", TESTING=True)
    login = LoginManager(app)
    login.user_loader(lambda user_id: _User())
    app.register_blueprint(strategic_tree_bp)
    monkeypatch.setattr(module, "service", _Service())
    monkeypatch.setattr(module, "can_access_company", lambda company_id, user=None: company_id == 9)
    monkeypatch.setattr(module, "get_accessible_company_ids", lambda user=None: [9])
    monkeypatch.setattr(module, "get_access_profile", lambda company_id, user=None: "client")
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "3"
        session["_fresh"] = True
        session["active_company_id"] = 9
        session["strategic_tree_csrf_token"] = "csrf-test"
    return client


def test_route_uses_active_company_and_does_not_accept_tenant_override(route_client):
    response = route_client.get("/api/knowledge/strategic-trees?company_id=2")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["company_id"] == 9


def test_route_rejects_write_without_csrf(route_client):
    response = route_client.post(
        "/api/knowledge/strategic-trees",
        json={"title": "Tentativa"},
    )

    assert response.status_code == 403
    assert "Token de segurança" in response.get_json()["error"]


def test_route_accepts_write_with_session_csrf(route_client):
    response = route_client.post(
        "/api/knowledge/strategic-trees",
        headers={"X-CSRF-Token": "csrf-test"},
        json={"title": "Reestruturação da Versus"},
    )

    assert response.status_code == 201
    assert response.get_json()["tree"]["title"] == "Reestruturação da Versus"
