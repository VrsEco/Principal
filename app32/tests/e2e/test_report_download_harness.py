from __future__ import annotations

from app32.tests.e2e.load.report_download_harness import execute_report_download_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_report_download_probe_collects_results(monkeypatch):
    class _FakeResponse:
        ok = True
        status_code = 200
        text = "<html>report</html>"
        headers = {"Content-Type": "text/html; charset=utf-8"}

    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

        def request(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setattr(
        "app32.tests.e2e.load.report_download_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_report_download_probe(settings=_settings())

    assert results[0].success is True
    assert "html" in results[0].content_type.lower()
