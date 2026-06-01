from __future__ import annotations

from app32.tests.e2e.load.financial_functional_harness import execute_financial_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_financial_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, content_type, text="", content=b"bin"):
            self.status_code = 200
            self.headers = {"Content-Type": content_type}
            self.text = text
            self.content = content
            self.url = "http://localhost:5002/financial/reports/agendamento"
            self.ok = True
        def raise_for_status(self): return None

    class _FakeHTTP:
        def login(self): return {"success": True}
        def select_company(self): return {"success": True}
        def request(self, method, path, *, json_payload=None):
            if path.endswith("export-pdf"):
                return _Response("application/pdf", content=b"%PDF-1.4")
            if path.endswith("export-xlsx"):
                return _Response("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", content=b"PK")
            if "extrato-bancario" in path:
                return _Response("text/html", text="Extrato bancario")
            return _Response("text/html", text="Relatório financeiro")
        def assert_not_login_redirect(self, response, *, operation): return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.financial_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    results = execute_financial_functional_probe(settings=_settings())
    assert len(results) == 5
    assert all(result.success for result in results)
    assert any(result.check_name == "financial.bordero_create_page" for result in results)
