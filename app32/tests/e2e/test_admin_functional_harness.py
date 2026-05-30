from __future__ import annotations

from app32.tests.e2e.load.admin_functional_harness import execute_admin_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_admin_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, status_code=200, payload=None):
            self.status_code = status_code
            self.headers = {"Content-Type": "application/json"}
            self._payload = payload or {}
            self.text = "{}"
            self.content = b"{}"
            self.url = "http://localhost:5002/api/test"
            self.ok = status_code < 400
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")
        def json(self): return self._payload

    class _FakeHTTP:
        def login(self): return {"success": True}
        def select_company(self): return {"success": True}
        def request(self, method, path, *, json_payload=None):
            if path.endswith("/performance-settings"):
                return _Response(payload={"allow_postpone_after_due_date": True})
            return _Response(status_code=403, payload={"error": "forbidden"})
        def assert_not_login_redirect(self, response, *, operation): return None
        def _json_or_raise(self, response, *, operation): return response.json()

    monkeypatch.setattr(
        "app32.tests.e2e.load.admin_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    results = execute_admin_functional_probe(settings=_settings())
    assert len(results) == 3
    assert all(result.success for result in results)
