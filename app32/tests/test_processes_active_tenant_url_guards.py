from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, session
from werkzeug.exceptions import Forbidden

from api.routes import processes as processes_route
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    return app


def test_company_url_route_rejects_tenant_different_from_active_session(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, "has_permission", lambda *_args: True)

    with app.test_request_context("/companies/22/process-portal"):
        session["active_company_id"] = 9
        response, status = processes_route.process_portal_page(22)

    assert status == 403
    assert "não corresponde" in response["error"]


def test_process_object_lookup_cannot_switch_active_tenant(monkeypatch):
    app = _app()
    process = SimpleNamespace(id=101, company_id=22)
    monkeypatch.setattr(
        processes_route,
        "Process",
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda process_id: process)),
    )
    monkeypatch.setattr(processes_route, "current_user", SimpleNamespace(is_authenticated=True))

    with app.test_request_context("/processes/101"):
        session["active_company_id"] = 9
        with pytest.raises(Forbidden):
            processes_route._get_process_with_access(101)


def test_routine_lookup_hides_routine_outside_active_tenant(monkeypatch):
    app = _app()
    monkeypatch.setattr(processes_route, "current_user", SimpleNamespace(is_authenticated=True))

    class Cursor:
        def execute(self, *_args):
            return None

        def fetchone(self):
            return {"id": 77, "company_id": 22, "name": "Rotina externa"}

    with app.test_request_context("/api/routines/77/collaborators"):
        session["active_company_id"] = 9
        assert processes_route._fetch_routine_scope(Cursor(), 77) is None


def test_process_company_routes_use_active_company_guard():
    source = (Path(__file__).resolve().parents[1] / "api" / "routes" / "processes.py").read_text(encoding="utf-8")

    expected_routes = (
        "/companies/<int:company_id>/process-portal",
        "/api/companies/<int:company_id>/process-portal",
        "/companies/<int:company_id>/bpms-analysis",
        "/companies/<int:company_id>/process-instances",
        "/companies/<int:company_id>/process-routines",
        "/api/companies/<int:company_id>/process-routines",
        "/api/companies/<int:company_id>/routine-events",
        "/api/companies/<int:company_id>/employees",
    )
    for route in expected_routes:
        offset = source.index(route)
        guarded_block = source[offset:offset + 240]
        assert "@active_company_permission_required(" in guarded_block

    assert "Processo não pertence à empresa ativa." in source
    assert "Macroprocesso não pertence à empresa ativa." in source
