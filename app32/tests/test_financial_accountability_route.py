import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial as financial_route
from utils import permissions as permission_utils


class _FakeColumn:
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __eq__(self, other):
        return lambda row: getattr(row, self.attr_name) == other

    def is_(self, other):
        return lambda row: getattr(row, self.attr_name) is other

    def in_(self, values):
        values = set(values or [])
        return lambda row: getattr(row, self.attr_name) in values

    def asc(self):
        return ("asc", self.attr_name)

    def desc(self):
        return ("desc", self.attr_name)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *conditions):
        filtered = self._rows
        for condition in conditions:
            if callable(condition):
                filtered = [row for row in filtered if condition(row)]
        return _FakeQuery(filtered)

    def order_by(self, *columns):
        rows = list(self._rows)
        for column in reversed(columns):
            if isinstance(column, tuple):
                direction, attr_name = column
            else:
                direction, attr_name = "asc", getattr(column, "attr_name", "name")
            rows.sort(
                key=lambda row: getattr(row, attr_name, "") if getattr(row, attr_name, "") is not None else "",
                reverse=direction == "desc",
            )
        return _FakeQuery(rows)

    def all(self):
        return list(self._rows)


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

    app.register_blueprint(financial_route.financial_bp)
    return app


def test_financial_accountability_route_redirects_to_automation_center(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(financial_route, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get("/financial/accountability?company_id=9", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/financial/automation")


def test_legacy_financial_ingestions_route_redirects_to_automation_center(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(financial_route, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get("/financial/ingestions?company_id=9", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/financial/automation")


def test_legacy_financial_classification_routes_redirect_to_automation_center(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(financial_route, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    queue_response = client.get("/financial/classification-queue?company_id=9", follow_redirects=False)
    dashboard_response = client.get("/financial/classification-dashboard?company_id=9", follow_redirects=False)

    assert queue_response.status_code == 302
    assert queue_response.headers["Location"].endswith("/financial/automation")
    assert dashboard_response.status_code == 302
    assert dashboard_response.headers["Location"].endswith("/financial/automation")
