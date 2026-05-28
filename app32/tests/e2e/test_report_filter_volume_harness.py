from __future__ import annotations

from app32.tests.e2e.data.profiles import LARGE_DATASET
from app32.tests.e2e.load.report_filter_volume_harness import execute_report_filter_volume_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_report_filter_volume_probe_collects_results(monkeypatch):
    class _FakeResponse:
        def __init__(self):
            self.ok = True
            self.status_code = 200

    class _FakeHTTP:
        def login(self):
            return {"success": True}

        def select_company(self):
            return {"success": True}

        def request(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setattr(
        "app32.tests.e2e.load.report_filter_volume_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_report_filter_volume_probe(settings=_settings(), profile=LARGE_DATASET)

    assert results
    assert all(result.success for result in results)
