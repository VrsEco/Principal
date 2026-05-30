from __future__ import annotations

from app32.tests.e2e.load.reports_functional_harness import execute_reports_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_reports_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, *, text):
            self.status_code = 200
            self.headers = {"Content-Type": "text/html"}
            self.text = text
            self.url = "http://localhost:5002/report"
            self.ok = True
        def raise_for_status(self): return None

    class _FakeHTTP:
        def login(self): return {"success": True}
        def select_company(self): return {"success": True}
        def request(self, method, path, *, json_payload=None):
            if "work-journey/report" in path:
                return _Response(text="Relatório da jornada")
            return _Response(text="<html>print view</html>")
        def assert_not_login_redirect(self, response, *, operation): return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.reports_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    results = execute_reports_functional_probe(settings=_settings())
    assert len(results) == 3
    assert all(result.success for result in results)
