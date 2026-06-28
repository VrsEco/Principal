from __future__ import annotations

from app32.tests.e2e.load.financial_functional_harness import execute_financial_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_financial_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, content_type, text="", content=b"bin", status_code=200):
            self.status_code = status_code
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
            if "/financial/schedules/123" in path:
                return _Response("text/html", text='data-tab="automacoes" data-panel="automacoes" Automações do título financeiro')
            if path.endswith("export-pdf"):
                return _Response("application/pdf", content=b"%PDF-1.4")
            if path.endswith("export-xlsx"):
                return _Response("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", content=b"PK")
            if path.startswith("/api/financial/reconciliation/rows/0/create-bordero-match"):
                return _Response("application/json", text='{"error":"Linha do extrato não encontrada"}', status_code=400)
            if path.startswith("/financial/reconciliation"):
                return _Response("text/html", text='Criar borderô e conciliar reconciliation-amount-filter selectedBankRowIds = []')
            if path.startswith("/financial/transfers"):
                return _Response("text/html", text='Transferência Bancária Nova transferência data-company-id="7"')
            if path.startswith("/financial/schedules"):
                return _Response("text/html", text="Títulos Financeiros Favorecido")
            if "extrato-bancario" in path:
                return _Response("text/html", text="Extrato bancario")
            return _Response("text/html", text="Relatório financeiro")
        def request_json(self, method, path, *, json_payload=None, operation):
            if path.startswith("/api/financial/catalogs/bank_accounts"):
                return [{"id": 10, "name": "Conta Corrente", "company_id": 7}]
            return [{"id": 123, "counterparty_id": 77, "summary": {"counterparty_name": "Cliente Teste"}}]
        def assert_not_login_redirect(self, response, *, operation): return None

    monkeypatch.setattr(
        "app32.tests.e2e.load.financial_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    results = execute_financial_functional_probe(settings=_settings())
    assert len(results) == 12
    assert all(result.success for result in results)
    assert any(result.check_name == "financial.bank_reconciliation_workspace" for result in results)
    assert any(result.check_name == "financial.bordero_match_guard" for result in results)
    assert any(result.check_name == "financial.bordero_create_page" for result in results)
    assert any(result.check_name == "financial.transfers_page" for result in results)
    assert any(result.check_name == "financial.bank_accounts_catalog_for_transfer" for result in results)
    assert any(result.check_name == "financial.schedule_local_automations_tab" for result in results)
    assert any(result.check_name == "financial.schedules_api_counterparty_contract" for result in results)
