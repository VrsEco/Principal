import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_automation_service as automation_module
from services.financial_automation_service import FinancialAutomationService


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self

    def asc(self):
        return self


class _EmptyRecords:
    def filter(self, *args, **kwargs):
        return self

    def count(self):
        return 0

    def all(self):
        return []


class _Docs:
    def __init__(self, docs):
        self._docs = docs

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._docs)

    def count(self):
        return len(self._docs)


class _Batch:
    id = 44
    origin_type = "manual_upload"
    source_label = "Lote parsing"
    status_summary_json = {}
    records = _EmptyRecords()

    def __init__(self, docs):
        self.documents = _Docs(docs)

    def to_dict(self):
        return {"id": self.id, "origin_type": self.origin_type, "source_label": self.source_label}


class _Record:
    deleted_at = _Column()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = None
        self.source_document = None
        self.batch = None

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "batch_id": self.batch_id,
            "source_document_id": self.source_document_id,
            "status": self.status,
            "entry_direction": self.entry_direction,
            "settlement_state": self.settlement_state,
            "description": self.description,
            "amount": float(self.amount),
            "normalized_payload_json": self.normalized_payload_json,
            "metadata_json": self.metadata_json,
        }


class _Session:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = 700 + index

    def commit(self):
        return None

    def rollback(self):
        return None


def _install_common(monkeypatch, batch):
    session = _Session()
    monkeypatch.setattr(automation_module.db, "session", session)
    monkeypatch.setattr(automation_module, "FinancialAutomationRecord", _Record)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_load_batch_for_company", lambda *args, **kwargs: batch)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_append_history", lambda **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_refresh_batch_summary", lambda batch: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_serialize_record", lambda item: item.to_dict())
    monkeypatch.setattr(
        automation_module.FinancialAutomationService,
        "_apply_auto_suggestions_to_record_kwargs",
        lambda **kwargs: kwargs["record_kwargs"],
    )
    monkeypatch.setattr(
        automation_module.FinancialAutomationService,
        "_apply_duplicate_metadata_to_record_kwargs",
        lambda **kwargs: kwargs["record_kwargs"],
    )
    return session


def test_parse_batch_documents_converts_csv_rows_to_imported_records(monkeypatch):
    document = SimpleNamespace(
        id=10,
        file_name="extrato.csv",
        document_type="spreadsheet",
        source_kind="spreadsheet",
        structured_payload_json={"source_kind": "spreadsheet"},
        extracted_text=None,
        preview_payload_json={},
        records=_EmptyRecords(),
        original_relative_path="extrato.csv",
        stored_relative_path="extrato.csv",
        document_group_key=None,
    )
    batch = _Batch([document])
    _install_common(monkeypatch, batch)

    row_input = SimpleNamespace(
        normalized_payload={
            "movement_nature": "debit",
            "occurred_on": None,
            "due_date": None,
        },
        amount=Decimal("123.45"),
        due_date=None,
        occurred_on=None,
        description="Despesa CSV",
        processing_status="accepted",
        error_message=None,
        bank_reference="BR-1",
        document_number="CSV-1",
        counterparty_name="Fornecedor CSV",
    )
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_read_document_bytes", lambda *args, **kwargs: b"csv")
    monkeypatch.setattr(automation_module.FinancialImportService, "_parse_source_rows", lambda source_type, file_bytes: [{"row": 1}])
    monkeypatch.setattr(automation_module.FinancialImportService, "_normalize_row", lambda row_number, raw_row: row_input)
    monkeypatch.setattr(automation_module, "FinancialAutomationDocument", type("DocModel", (), {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "query": SimpleNamespace(filter=lambda *args, **kwargs: SimpleNamespace(first=lambda: document))}))

    result, error = FinancialAutomationService.parse_batch_documents(
        company_id=9,
        batch_id=44,
        upload_root="C:/tmp/uploads",
        allowed_company_ids=[9],
        performed_by_user_id=7,
    )

    assert error is None
    assert result["count"] == 1
    assert result["records"][0]["description"] == "Despesa CSV"
    assert result["records"][0]["metadata_json"]["document_parser"] == "csv"
    assert result["records"][0]["metadata_json"]["parser_mode"] == "structured_import"


def test_infer_document_source_type_preserves_xls_extension():
    batch = SimpleNamespace(origin_type="manual_upload")
    document = SimpleNamespace(
        document_type="spreadsheet",
        source_kind="spreadsheet",
        file_name="lote_legado.xls",
    )

    source_type = FinancialAutomationService._infer_document_source_type(batch, document)

    assert source_type == "xls"


def test_auto_suggestions_do_not_override_unresolved_spreadsheet_bank_account(monkeypatch):
    monkeypatch.setattr(
        automation_module.FinancialCatalogService,
        "enrich_reference_payload",
        lambda **kwargs: {**kwargs["payload"], "bank_account_id": 99},
    )
    monkeypatch.setattr(
        automation_module.FinancialAutomationService,
        "_find_classification_memory_suggestion",
        lambda **kwargs: None,
    )

    result = FinancialAutomationService._apply_auto_suggestions_to_record_kwargs(
        company_id=9,
        source_document=None,
        record_kwargs={
            "entry_direction": "payable",
            "description": "Histórico com texto de outra conta",
            "amount": Decimal("100.00"),
            "bank_account_id": None,
            "normalized_payload_json": {"bank_account_code": "Conta Inexistente"},
            "metadata_json": {},
        },
    )

    assert result["bank_account_id"] is None
    assert result["normalized_payload_json"]["bank_account_id"] is None
    assert result["metadata_json"]["auto_suggestions"]["bank_account"]["source"] == "unresolved_spreadsheet"
    assert result["metadata_json"]["auto_suggestions"]["bank_account"]["explicit_reference"] == "Conta Inexistente"


def test_auto_suggestions_preserve_resolved_spreadsheet_bank_account(monkeypatch):
    monkeypatch.setattr(
        automation_module.FinancialCatalogService,
        "enrich_reference_payload",
        lambda **kwargs: {**kwargs["payload"], "bank_account_id": 99},
    )
    monkeypatch.setattr(
        automation_module.FinancialAutomationService,
        "_find_classification_memory_suggestion",
        lambda **kwargs: None,
    )

    result = FinancialAutomationService._apply_auto_suggestions_to_record_kwargs(
        company_id=9,
        source_document=None,
        record_kwargs={
            "entry_direction": "payable",
            "description": "Histórico com texto de outra conta",
            "amount": Decimal("100.00"),
            "bank_account_id": 8,
            "normalized_payload_json": {"bank_account_code": "Conta Pagamentos"},
            "metadata_json": {},
        },
    )

    assert result["bank_account_id"] == 8
    assert result["normalized_payload_json"]["bank_account_id"] == 8
    assert result["metadata_json"]["auto_suggestions"]["bank_account"]["source"] == "spreadsheet"


def test_parse_batch_documents_creates_fallback_record_for_unstructured_document(monkeypatch):
    document = SimpleNamespace(
        id=11,
        file_name="recibo.pdf",
        document_type="unknown_document",
        source_kind="pdf",
        structured_payload_json={},
        extracted_text="Recibo de taxi\nTotal R$ 1.234,56",
        preview_payload_json={"extracted_preview": "Recibo de taxi", "extraction_method": "pdf_text"},
        records=_EmptyRecords(),
        original_relative_path="recibo.pdf",
        stored_relative_path="recibo.pdf",
        document_group_key=None,
    )
    batch = _Batch([document])
    _install_common(monkeypatch, batch)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_read_document_bytes", lambda *args, **kwargs: b"")

    result, error = FinancialAutomationService.parse_batch_documents(
        company_id=9,
        batch_id=44,
        upload_root="C:/tmp/uploads",
        allowed_company_ids=[9],
        performed_by_user_id=7,
    )

    assert error is None
    assert result["count"] == 1
    record = result["records"][0]
    assert record["description"] == "Recibo de taxi"
    assert record["amount"] == 1234.56
    assert record["metadata_json"]["document_parser"] == "document_fallback"
    assert record["metadata_json"]["parser_mode"] == "document_preview"
