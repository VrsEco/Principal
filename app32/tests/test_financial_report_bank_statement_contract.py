import os
import sys
from datetime import date
from decimal import Decimal
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


class _RecordingQueryStub(_QueryStub):
    def __init__(self, items):
        super().__init__(items)
        self.filters = []

    def filter(self, *args, **kwargs):
        self.filters.extend(args)
        return self


class _NamedColumn(_Column):
    def __init__(self, name):
        self.name = name

    def __ne__(self, other):
        return ("ne", self.name, other)

    def __lt__(self, other):
        return ("lt", self.name, other)

    def in_(self, other):
        return ("in", self.name, list(other))


def test_bank_statement_opening_balance_uses_statement_filters_and_includes_transfers(monkeypatch):
    history_settlement = SimpleNamespace(
        id=1,
        financial_entry_id=10,
        settlement_date=date(2026, 5, 25),
        bank_account_id=15,
        net_amount=Decimal("28381.42"),
    )
    transfer_entry = SimpleNamespace(
        id=10,
        movement_nature="debit",
        status="settled",
        entry_type="transfer",
        metadata_json={"is_transfer": True},
    )
    settlement_query = _RecordingQueryStub([history_settlement])
    entry_query = _RecordingQueryStub([transfer_entry])
    monkeypatch.setattr(
        report_module,
        "FinancialSettlement",
        type(
            "FinancialSettlementStub",
            (),
            {
                "company_id": _NamedColumn("company_id"),
                "deleted_at": _NamedColumn("deleted_at"),
                "settlement_status": _NamedColumn("settlement_status"),
                "settlement_date": _NamedColumn("settlement_date"),
                "bank_account_id": _NamedColumn("bank_account_id"),
                "query": settlement_query,
            },
        ),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialEntry",
        type(
            "FinancialEntryStub",
            (),
            {
                "company_id": _NamedColumn("company_id"),
                "id": _NamedColumn("id"),
                "deleted_at": _NamedColumn("deleted_at"),
                "query": entry_query,
            },
        ),
    )
    filters = SimpleNamespace(
        report_type="bank_statement",
        period_start=date(2026, 6, 1),
        bank_account_id=None,
        bank_account_ids=[15],
        include_reconciled_only=False,
        include_receivable=True,
        include_payable=True,
        include_partial=True,
        include_settled=True,
    )

    balance = FinancialReportService._bank_statement_opening_balance(1, filters)

    assert balance == Decimal("-28381.42")
    assert ("in", "bank_account_id", [15]) in settlement_query.filters


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

    assert "movimento" not in [column["key"] for column in result["columns"]]
    assert result["rows"][0]["valor"] == -120.0
    assert result["rows"][0]["valor_label"] == "- 120,00"
    assert "R$" not in result["rows"][0]["valor_label"]
    assert result["rows"][0]["valor_tone"] == "negative"
    assert result["rows"][0]["valor_principal"] == 100.0
    assert result["rows"][0]["valor_correcao"] == 20.0
    assert result["rows"][0]["valor_desconto"] == 5.0
    assert result["rows"][0]["rateio_principal_itens"] == 1
    assert result["rows"][0]["rateio_correcao_itens"] == 2
    assert result["rows"][0]["rateio_desconto_itens"] == 0


def test_build_bank_statement_dossier_collects_title_entry_and_settlement_attachments(monkeypatch):
    settlement = SimpleNamespace(
        id=10,
        financial_entry_id=99,
        settlement_date=date(2026, 4, 20),
        settlement_code="LIQ-000010",
        bank_account_id=3,
        reconciliation_status="pending",
        net_amount=120.0,
        principal_amount=100.0,
        metadata_json={"attachments": [{"id": "settlement-doc", "name": "baixa.pdf", "url": "/uploads/baixa.pdf"}]},
    )
    entry = SimpleNamespace(
        id=99,
        movement_nature="debit",
        entry_code="LAN-99",
        description="Pagamento teste",
        counterparty_id=4,
        financial_schedule_id=55,
        competence_date=date(2026, 4, 1),
        due_date=date(2026, 4, 15),
        chart_account_id=1,
        cost_center_id=2,
        metadata_json={"attachments": [{"id": "entry-doc", "name": "lancamento.pdf", "url": "/uploads/lancamento.pdf"}]},
    )
    schedule = SimpleNamespace(
        id=55,
        schedule_code="TIT-55",
        name="Título teste",
        metadata_json={"attachments": [{"id": "title-doc", "name": "titulo.pdf", "url": "/uploads/titulo.pdf"}]},
    )
    allocation = SimpleNamespace(financial_entry_id=99, chart_account_id=7, cost_center_id=8)

    monkeypatch.setattr(report_module.FinancialReportService, "_settlement_query", lambda company_id, filters: _QueryStub([settlement]))
    monkeypatch.setattr(
        report_module.FinancialReportService,
        "_name_map",
        lambda model, company_id: {
            1: "1 - Conta direta",
            2: "2 - Centro direto",
            3: "Banco XP",
            4: "Fornecedor Teste",
            7: "7 - Conta rateada",
            8: "8 - Centro rateado",
        },
    )
    monkeypatch.setattr(report_module.FinancialDashboardAnalytics, "calculate_current_balance", lambda **kwargs: 0)
    monkeypatch.setattr(
        report_module.FinancialService,
        "serialize_settlement",
        lambda settlement, **kwargs: {
            "settlement_component_summary": {"principal": 100.0},
            "settlement_allocation_breakdown": {"principal": {"items": [{"chart_account_id": 1, "cost_center_id": 2}]}},
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
    monkeypatch.setattr(
        report_module,
        "FinancialSchedule",
        type("FinancialScheduleStub", (), {"company_id": _Column(), "id": _Column(), "deleted_at": _Column(), "query": _QueryStub([schedule])}),
    )
    monkeypatch.setattr(
        report_module,
        "FinancialEntryAllocation",
        type("FinancialEntryAllocationStub", (), {"company_id": _Column(), "financial_entry_id": _Column(), "deleted_at": _Column(), "query": _QueryStub([allocation])}),
    )

    filters = SimpleNamespace(
        report_type="bank_statement_dossier",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        bank_account_id=None,
        bank_account_ids=[],
        include_reconciled_only=False,
    )

    result = FinancialReportService._build_bank_statement(7, filters)

    assert result["dossier_document_count"] == 3
    assert {item["source_type"] for item in result["dossier_documents"]} == {"title", "entry", "settlement"}
    assert result["rows"][0]["competencia"] == "2026-04-01"
    assert result["rows"][0]["vencimento"] == "2026-04-15"
    assert "7 - Conta rateada" in result["rows"][0]["plano_contas"]
    assert "8 - Centro rateado" in result["rows"][0]["centro_resultados"]


def test_bank_statement_dossier_normalize_defaults_to_portrait():
    filters, error = FinancialReportService._normalize_filters(
        "bank_statement_dossier",
        {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        },
    )

    assert error is None
    assert filters is not None
    assert filters.orientation == "portrait"


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
                "movimento_tone": "negative",
                "valor": "101.86",
                "valor_label": "- 101,86",
                "valor_tone": "negative",
                "conciliacao": "pending",
                "conciliacao_label": "Pendente",
                "conciliacao_tone": "neutral",
                "saldo": "-996.28",
                "saldo_label": "- 996,28",
                "saldo_tone": "negative",
            }
        ],
    }

    pdf_bytes = FinancialReportService.export_pdf(payload)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_export_pdf_bank_statement_dossier_supports_complete_and_simple_modes():
    payload = {
        "report_type": "bank_statement_dossier",
        "report_slug": "dossie-extrato-bancario",
        "title": "Dossiê do Extrato Bancário",
        "subtitle": "Dossiê documental.",
        "statement_title": "Extrato Bancário",
        "statement_subtitle": "Extrato gerencial.",
        "company_name": "Empresa Teste",
        "generated_at": "06/06/2026 10:00",
        "period_start": "2026-06-01",
        "period_end": "2026-06-06",
        "filters": [{"label": "Período", "value": "2026-06-01 até 2026-06-06"}],
        "summary_cards": [
            {"label": "Saldo inicial", "value": "R$ 0,00", "tone": "neutral"},
            {"label": "Entradas", "value": "R$ 10,00", "tone": "positive"},
            {"label": "Saídas", "value": "R$ 0,00", "tone": "negative"},
            {"label": "Saldo final", "value": "R$ 10,00", "tone": "primary"},
        ],
        "columns": [
            {"key": "data", "label": "Data"},
            {"key": "codigo", "label": "Baixa"},
            {"key": "conta_bancaria", "label": "Conta bancária"},
            {"key": "lancamento", "label": "Lançamento"},
            {"key": "descricao", "label": "Descrição"},
            {"key": "favorecido", "label": "Favorecido"},
            {"key": "valor", "label": "Valor"},
            {"key": "conciliacao", "label": "Conciliação"},
            {"key": "saldo", "label": "Saldo"},
        ],
        "rows": [
            {
                "data": "2026-06-02",
                "codigo": "BX-1",
                "conta_bancaria": "Banco",
                "lancamento": "LAN-1",
                "descricao": "Teste",
                "favorecido": "Fornecedor",
                "movimento_tone": "positive",
                "valor": "10",
                "valor_label": "10,00",
                "valor_tone": "positive",
                "conciliacao": "pending",
                "conciliacao_label": "Pendente",
                "conciliacao_tone": "neutral",
                "saldo": "10",
                "saldo_label": "10,00",
                "saldo_tone": "positive",
            }
        ],
        "dossier_document_count": 1,
        "dossier_documents": [
            {
                "source_label": "Baixa",
                "document_name": "comprovante.pdf",
                "competence_date": "2026-06-01",
                "due_date": "2026-06-05",
                "settlement_date": "2026-06-06",
                "chart_account": "1 - Teste",
                "cost_center": "CR",
                "counterparty": "Fornecedor",
                "entry_code": "LAN-1",
                "settlement_code": "BX-1",
                "amount": "R$ 10,00",
                "attachment": {"name": "comprovante.pdf", "url": "/uploads/inexistente.pdf", "content_type": "application/pdf"},
            }
        ],
    }

    complete_pdf = FinancialReportService.export_pdf({**payload, "dossier_mode": "complete"})
    simple_pdf = FinancialReportService.export_pdf({**payload, "dossier_mode": "simple"})

    assert complete_pdf.startswith(b"%PDF")
    assert simple_pdf.startswith(b"%PDF")
    assert len(complete_pdf) > 1000
    assert len(simple_pdf) > 1000
