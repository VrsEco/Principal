import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.resources import process as process_resource


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back = True


def _build_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    return app


def test_macro_process_post_blocks_area_outside_company(monkeypatch):
    app = _build_app()
    resource = process_resource.MacroProcessListResource()
    fake_session = _FakeSession()

    monkeypatch.setattr(process_resource, "get_request_company_id", lambda: 12)
    monkeypatch.setattr(process_resource, "_get_area_in_company", lambda area_id, company_id: None)
    monkeypatch.setattr(process_resource.db, "session", fake_session)

    with app.test_request_context(
        "/api/macro-processes",
        method="POST",
        json={"area_id": 999, "name": "Planejamento", "order_index": 1, "owner": "Fabiano"},
    ):
        response, status = resource.post.__wrapped__(resource)

    assert status == 400
    assert response["error"] == "Área de processo não encontrada na empresa informada."
    assert fake_session.committed == 0
    assert fake_session.added == []


def test_process_post_blocks_macro_outside_company(monkeypatch):
    app = _build_app()
    resource = process_resource.ProcessListResource()
    fake_session = _FakeSession()

    monkeypatch.setattr(process_resource, "get_request_company_id", lambda: 12)
    monkeypatch.setattr(process_resource, "_get_macro_in_company", lambda macro_id, company_id: None)
    monkeypatch.setattr(process_resource.db, "session", fake_session)

    with app.test_request_context(
        "/api/processes",
        method="POST",
        json={"macro_id": 777, "name": "Diagnóstico", "order_index": 1},
    ):
        response, status = resource.post.__wrapped__(resource)

    assert status == 400
    assert response["error"] == "Macroprocesso não encontrado na empresa informada."
    assert fake_session.committed == 0
    assert fake_session.added == []


def test_process_map_get_uses_company_id_scope(monkeypatch):
    app = _build_app()
    resource = process_resource.ProcessListResource()
    captured = {}

    class _FakeQuery:
        def filter_by(self, **kwargs):
            captured.update(kwargs)
            return self

        def all(self):
            return []

    monkeypatch.setattr(process_resource, "get_request_company_id", lambda: 12)
    monkeypatch.setattr(process_resource, "Process", SimpleNamespace(query=_FakeQuery()))
    monkeypatch.setattr(process_resource, "_get_process_ids_with_bpmn_flow", lambda company_id, process_ids: set())

    with app.test_request_context("/api/processes?company_id=12", method="GET"):
        response, status = resource.get.__wrapped__(resource)

    assert status == 200
    assert response == []
    assert captured["company_id"] == 12

