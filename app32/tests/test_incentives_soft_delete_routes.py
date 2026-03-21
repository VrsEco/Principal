import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import incentives as incentives_route


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    return app


def test_delete_rule_set_route_returns_conflict_when_service_blocks(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(
        incentives_route,
        "IncentiveService",
        SimpleNamespace(soft_delete_rule_set=lambda company_id, rule_set_id: (False, "Plano possui vetores vinculados.")),
    )

    with app.test_request_context("/api/incentive-rule-sets/11", method="DELETE"):
        session["active_company_id"] = 9
        response, status_code = incentives_route.delete_rule_set.__wrapped__(11)

    assert status_code == 409
    assert response.get_json()["error"] == "Plano possui vetores vinculados."


def test_delete_rule_set_route_returns_success_when_service_allows(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(
        incentives_route,
        "IncentiveService",
        SimpleNamespace(soft_delete_rule_set=lambda company_id, rule_set_id: (True, "")),
    )

    with app.test_request_context("/api/incentive-rule-sets/11", method="DELETE"):
        session["active_company_id"] = 9
        response, status_code = incentives_route.delete_rule_set.__wrapped__(11)

    assert status_code == 200
    assert response.get_json()["ok"] is True


def test_protected_delete_rule_set_requires_reason_and_admin(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(incentives_route, "is_administrator", lambda company_id: False)

    with app.test_request_context("/api/incentive-rule-sets/11/protected-delete", method="DELETE", json={}):
        session["active_company_id"] = 9
        response, status_code = incentives_route.protected_delete_rule_set.__wrapped__(11)

    assert status_code == 403
    assert "administradores" in response.get_json()["error"]


def test_closing_delete_route_allows_operational_delete(monkeypatch):
    app = _build_app()
    calc = SimpleNamespace(id=12, company_id=9, status="calculated")

    monkeypatch.setattr(
        incentives_route,
        "IncentiveService",
        SimpleNamespace(
            get_calculation=lambda company_id, calc_id: calc,
            soft_delete_calculation=lambda company_id, calc_id, allow_protected=False: (True, ""),
        ),
    )
    monkeypatch.setattr(incentives_route, "_log_protected_action", lambda *args, **kwargs: None)

    with app.test_request_context("/api/incentives/closings/12", method="DELETE"):
        session["active_company_id"] = 9
        response, status_code = incentives_route.closing_update_delete.__wrapped__(12)

    assert status_code == 200
    assert response.get_json()["ok"] is True
