from __future__ import annotations

from app32.tests.e2e.load.contracts_functional_harness import execute_contracts_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_contracts_functional_harness_validates_fiscal_invoice_workspace(monkeypatch):
    class _Response:
        def __init__(self, content_type, text=""):
            self.status_code = 200
            self.headers = {"Content-Type": content_type}
            self.text = text
            self.content = text.encode("utf-8")
            self.url = "http://localhost:5002/contracts/invoices"
            self.ok = True

        def raise_for_status(self):
            return None

    class _FakeHTTP:
        def login(self): return {"success": True}
        def select_company(self): return {"success": True}
        def request(self, method, path, *, json_payload=None):
            return _Response(
                "text/html",
                text=(
                    'Notas Fiscais Registros fiscais Ações em lote '
                    'PJ emissora name="issuer_legal_entity_id" Aplicar filtros '
                    'Organização fiscal Gerar planilha XLSX Upload planilha/XML/PDF'
                ),
            )
        def assert_not_login_redirect(self, response, *, operation): return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.contracts_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )

    results = execute_contracts_functional_probe(settings=_settings())

    assert len(results) == 3
    assert all(result.success for result in results)
    assert {result.check_name for result in results} == {
        "contracts.fiscal_invoices_workspace",
        "contracts.fiscal_invoices_issuer_filter",
        "contracts.fiscal_invoices_bulk_actions_panel",
    }
