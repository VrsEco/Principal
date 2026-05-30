from __future__ import annotations

from app32.tests.e2e.load.work_journey_functional_harness import execute_work_journey_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_work_journey_functional_harness_validates_actions(monkeypatch):
    class _Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        text = "<div data-work-journey-root></div>"
        url = "http://localhost:5002/companies/9/work-journey"
        ok = True

        def raise_for_status(self):
            return None

    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

        def request_json(self, method, path, *, json_payload=None, operation):
            if path.endswith("/board"):
                return {"success": True, "data": {"employee": {"id": 77}}}
            return {"success": True, "data": {"items": []}}

        def request(self, method, path, *, json_payload=None):
            return _Response()

        def assert_not_login_redirect(self, response, *, operation):
            return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.work_journey_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_work_journey_functional_probe(settings=_settings())

    assert len(results) == 3
    assert all(result.success for result in results)
