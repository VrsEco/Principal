import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import indicators as indicators_route


class _FakeIndicatorQuery:
    def __init__(self, indicator):
        self.indicator = indicator

    def filter_by(self, **kwargs):
        return self

    def first_or_404(self):
        return self.indicator


class _FakeCountQuery:
    def __init__(self, count_value):
        self._count_value = count_value

    def filter_by(self, **kwargs):
        return self

    def count(self):
        return self._count_value


class _FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    return app


def test_delete_indicator_blocks_when_has_linked_goal_or_data(monkeypatch):
    app = _build_app()
    indicator = SimpleNamespace(id=33, company_id=9, is_active=True)

    monkeypatch.setattr(indicators_route, "Indicator", SimpleNamespace(query=_FakeIndicatorQuery(indicator)))
    monkeypatch.setattr(indicators_route, "IndicatorGoal", SimpleNamespace(query=_FakeCountQuery(2)))
    monkeypatch.setattr(indicators_route, "IndicatorData", SimpleNamespace(query=_FakeCountQuery(1)))

    with app.test_request_context("/api/indicators/33", method="DELETE"):
        session["active_company_id"] = 9
        response, status = indicators_route.delete_indicator.__wrapped__(33)

    assert status == 409
    assert "vinculados" in response.get_json()["error"]
    assert indicator.is_active is True


def test_delete_indicator_soft_deletes_when_no_links(monkeypatch):
    app = _build_app()
    indicator = SimpleNamespace(id=33, company_id=9, is_active=True)
    fake_db_session = _FakeSession()

    monkeypatch.setattr(indicators_route, "Indicator", SimpleNamespace(query=_FakeIndicatorQuery(indicator)))
    monkeypatch.setattr(indicators_route, "IndicatorGoal", SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(indicators_route, "IndicatorData", SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(indicators_route, "db", SimpleNamespace(session=fake_db_session))

    with app.test_request_context("/api/indicators/33", method="DELETE"):
        session["active_company_id"] = 9
        response = indicators_route.delete_indicator.__wrapped__(33)

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["is_active"] is False
    assert "soft delete" in payload["message"]
    assert fake_db_session.commits == 1
