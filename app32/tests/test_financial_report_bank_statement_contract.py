import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_report_service as report_module
from services.financial_report_service import FinancialReportService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def in_(self, other):
        return ("in", other)

    def __lt__(self, other):
        return ("lt", other)

    def asc(self):
        return self


class _QueryStub:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)


def test_build_bank_statement_exposes_component_allocations(monkeypatch):
    settlement = SimpleNamespace(
        id=10,
        financial_entry_id=99,
        settlement_date=date(2026, 4, 20),
        settlement_code="LIQ-000010",
        bank_account_id=3,
        reconciliation_status="pending",
        net_amount=120.0,
        principal_amount=100.0,
    )
    entry = SimpleNamespace(
        id=99,
        movement_nature="debit",
        entry_code="LAN-99",
        description="Pagamento teste",
        counterparty_id=4,
    )

    monkeypatch.setattr(report_module.FinancialReportService, "_settlement_query", lambda company_id, filters: _QueryStub([settlement]))
    monkeypatch.setattr(report_module.FinancialReportService, "_name_map", lambda model, company_id: {3: "Banco XP", 4: "Fornecedor Teste"})
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_current_balance", lambda **kwargs: 0)
    monkeypatch.setattr(
        report_module.FinancialService,
        "serialize_settlement",
        lambda settlement, **kwargs: {
            "settlement_component_summary": {"principal": 100.0, "financial_correction": 20.0, "discount": 5.0},
            "settlement_allocation_breakdown": {
                "principal": {"items": [{"chart_account_id": 1}]},
                "financial_correction": {"items": [{"chart_account_id": 2}, {"chart_account_id": 3}]},
                "discount": {"items": []},
            },
        },
    )
    monkeypatch.setattr(
        report_module,
        "FinancialEntry",
        type("FinancialEntryStub", (), {"company_id": _Column(), "id": _Column(), "deleted_at": _Column(), "query": _QueryStub([entry])}),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialSettlement",
        type("FinancialSettlementStub", (), {"company_id": _Column(), "deleted_at": _Column(), "settlement_status": _Column(), "settlement_date": _Column(), "id": _Column(), "query": _QueryStub([])}),
    )

    filters = SimpleNamespace(report_type="bank_statement", period_start=date(2026, 4, 1), period_end=date(2026, 4, 30), bank_account_id=None, include_reconciled_only=False)

    result = FinancialReportService._build_bank_statement(7, filters)

    assert result["rows"][0]["valor_principal"] == 100.0
    assert result["rows"][0]["valor_correcao"] == 20.0
    assert result["rows"][0]["valor_desconto"] == 5.0
    assert result["rows"][0]["rateio_principal_itens"] == 1
    assert result["rows"][0]["rateio_correcao_itens"] == 2
    assert result["rows"][0]["rateio_desconto_itens"] == 0


def test_export_pdf_bank_statement_uses_dedicated_app32_layout():
    payload = {
        "report_type": "bank_statement",
        "report_slug": "extrato-bancario",
        "title": "Extrato Bancário",
        "subtitle": "Extrato gerencial.",
        "company_name": "Empresa Teste",
        "generated_at": "30/04/2026 23:18",
        "filters": [
            {"label": "Período", "value": "2026-03-01 até 2026-04-30"},
            {"label": "Conta bancária", "value": "003 - Caixinha Carol"},
        ],
        "summary_cards": [
            {"label": "Saldo inicial", "value": "R$ 0,00", "tone": "neutral"},
            {"label": "Saldo final", "value": "R$ -996,28", "tone": "negative"},
        ],
        "columns": [
            {"key": "data", "label": "Data"},
            {"key": "codigo", "label": "Liquidação"},
            {"key": "conta_bancaria", "label": "Conta bancária"},
            {"key": "descricao", "label": "Descrição"},
            {"key": "movimento", "label": "Movimento"},
            {"key": "valor", "label": "Valor"},
            {"key": "conciliacao", "label": "Conciliação"},
            {"key": "saldo", "label": "Saldo"},
        ],
        "rows": [
            {
                "data": "2026-04-13",
                "codigo": "BX-000004",
                "conta_bancaria": "003 - Caixinha Carol",
                "descricao": "Averbação teste",
                "movimento": "Saída",
                "movimento_tone": "negative",
                "valor": "101.86",
                "valor_label": "R$ 101,86",
                "conciliacao": "pending",
                "conciliacao_label": "Pendente",
                "conciliacao_tone": "neutral",
                "saldo": "-996.28",
                "saldo_label": "R$ -996,28",
                "saldo_tone": "negative",
            }
        ],
    }

    pdf_bytes = FinancialReportService.export_pdf(payload)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
