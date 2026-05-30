from __future__ import annotations

from app32.tests.e2e.load.workspace_functional_harness import execute_workspace_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_workspace_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, *, status_code=200, headers=None, text="", url="http://localhost:5002/my-work"):
            self.status_code = status_code
            self.headers = headers or {}
            self.text = text
            self.url = url
            self.ok = status_code < 400

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

        def request_json(self, method, path, *, json_payload=None, operation):
            if "filter-options" in path:
                return {"success": True, "data": {"companies": [{"id": 9}], "collaborators": [{"id": 4}]}}
            return {"success": True, "data": [{"id": 1}], "stats": {"total": 1}}

        def request(self, method, path, *, json_payload=None):
            return _Response(headers={"Content-Type": "text/html"}, text="<html>print view</html>")

        def assert_not_login_redirect(self, response, *, operation):
            return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.workspace_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_workspace_functional_probe(settings=_settings())

    assert len(results) == 3
    assert all(result.success for result in results)


def test_workspace_functional_harness_flags_public_error(monkeypatch):
    class _Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        text = "Erro interno do servidor. Tente novamente ou contate o suporte."
        url = "http://localhost:5002/my-work/export-pdf"
        ok = True

        def raise_for_status(self):
            return None

    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

        def request_json(self, method, path, *, json_payload=None, operation):
            return {"success": True, "data": {}}

        def request(self, method, path, *, json_payload=None):
            return _Response()

        def assert_not_login_redirect(self, response, *, operation):
            return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.workspace_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_workspace_functional_probe(settings=_settings())

    export_result = next(result for result in results if result.check_name == "workspace.export_pdf")
    assert export_result.success is False
    assert export_result.details["has_public_error"] is True
