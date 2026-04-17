import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_automation_service as automation_module
from services.financial_automation_service import FinancialAutomationService


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self

    def in_(self, other):
        return self

    def asc(self):
        return self


class _Batch:
    def __init__(self, batch_id=1, origin_type="manual_upload", source_label="Lote teste"):
        self.id = batch_id
        self.origin_type = origin_type
        self.source_label = source_label
        self.status_summary_json = {}
        self.updated_at = None
        self.documents = SimpleNamespace(filter=lambda *args, **kwargs: SimpleNamespace(count=lambda: 0))
        self.records = SimpleNamespace(filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: []))

    def __hash__(self):
        return hash(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "origin_type": self.origin_type,
            "source_label": self.source_label,
            "status_summary_json": self.status_summary_json,
        }


class _Record:
    def __init__(self, record_id, settlement_state, batch=None):
        self.id = record_id
        self.company_id = 9
        self.batch_id = 1
        self.batch = batch or _Batch()
        self.status = "validated"
        self.entry_direction = "payable"
        self.settlement_state = settlement_state
        self.description = f"Registro {record_id}"
        self.counterparty_id = None
        self.bank_account_id = None
        self.chart_account_id = None
        self.cost_center_id = None
        self.domain_type = None
        self.domain_source_id = None
        self.amount = 150
        self.competence_date = None
        self.due_date = None
        self.confidence_score = 0.8
        self.validation_notes = None
        self.normalized_payload_json = {}
        self.metadata_json = {}
        self.generated_financial_entry_id = None
        self.generated_financial_schedule_id = None
        self.validated_by_user_id = None
        self.validated_at = None
        self.generated_by_user_id = None
        self.generated_at = None
        self.created_at = None
        self.updated_at = None
        self.deleted_at = None
        self.source_document = None

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "batch_id": self.batch_id,
            "status": self.status,
            "entry_direction": self.entry_direction,
            "settlement_state": self.settlement_state,
            "description": self.description,
            "counterparty_id": self.counterparty_id,
            "bank_account_id": self.bank_account_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "domain_type": self.domain_type,
            "domain_source_id": self.domain_source_id,
            "amount": self.amount,
            "competence_date": self.competence_date,
            "due_date": self.due_date,
            "confidence_score": self.confidence_score,
            "validation_notes": self.validation_notes,
            "normalized_payload_json": self.normalized_payload_json,
            "metadata_json": self.metadata_json,
            "generated_financial_entry_id": self.generated_financial_entry_id,
            "generated_financial_schedule_id": self.generated_financial_schedule_id,
        }


def test_automation_center_template_contains_bulk_validation_flow():
    template = Path(
        r"C:\GestaoVersus\app32\app32\templates\modules\financial\automation_center.html"
    ).read_text(encoding="utf-8")

    assert "Central de Automação Financeira" in template
    assert 'id="fa-mark-validated"' in template
    assert 'id="fa-mark-excluded"' in template
    assert 'id="fa-generate"' in template
    assert "Importada" in template
    assert "Validada" in template
    assert "Gerada" in template
    assert "Excluída" in template


def test_automation_center_js_uses_data_field_mapping_and_origin_labels():
    script = Path(
        r"C:\GestaoVersus\app32\app32\static\js\financial_automation_center.js"
    ).read_text(encoding="utf-8")

    assert "statusLabels" in script
    assert "originLabels" in script
    assert "row.querySelectorAll('[data-field]')" in script
    assert "'domain_link'" in script
    assert "record.batch?.source_label" in script


def test_generate_records_routes_settled_to_entry_and_open_to_schedule(monkeypatch):
    batch = _Batch()
    settled_record = _Record(record_id=1, settlement_state="settled", batch=batch)
    open_record = _Record(record_id=2, settlement_state="open", batch=batch)
    records = [settled_record, open_record]

    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return records

    class _RecordModel:
        company_id = _Column()
        deleted_at = _Column()
        status = _Column()
        id = _Column()
        query = _Query()

    monkeypatch.setattr(automation_module, "FinancialAutomationRecord", _RecordModel)
    monkeypatch.setattr(
        automation_module.FinancialAutomationGenerateInput,
        "model_validate",
        lambda payload: SimpleNamespace(company_id=9, record_ids=None, only_status="validated", generated_by_user_id=77),
    )
    monkeypatch.setattr(automation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_generate_entry_from_record", lambda *args, **kwargs: (501, None))
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_generate_schedule_from_record", lambda *args, **kwargs: (901, None))
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_append_history", lambda **kwargs: None)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "_refresh_batch_summary", lambda batch: None)
    monkeypatch.setattr(automation_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(automation_module.db.session, "rollback", lambda: None)

    result, error = FinancialAutomationService.generate_records(
        payload={"company_id": 9},
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["count"] == 2
    assert settled_record.generated_financial_entry_id == 501
    assert open_record.generated_financial_schedule_id == 901
    assert settled_record.status == "generated"
    assert open_record.status == "generated"


def test_bulk_update_status_rejects_manual_generated_transition(monkeypatch):
    batch = _Batch()
    item = _Record(record_id=1, settlement_state="open", batch=batch)

    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [item]

    class _RecordModel:
        company_id = _Column()
        id = _Column()
        deleted_at = _Column()
        query = _Query()

    monkeypatch.setattr(automation_module, "FinancialAutomationRecord", _RecordModel)
    monkeypatch.setattr(
        automation_module.FinancialAutomationBulkStatusInput,
        "model_validate",
        lambda payload: SimpleNamespace(company_id=9, record_ids=[1], status="generated", validation_notes=None),
    )
    monkeypatch.setattr(automation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)

    result, error = FinancialAutomationService.bulk_update_status(
        payload={"company_id": 9, "record_ids": [1], "status": "generated"},
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Use a ação de geração oficial para marcar registros como Gerada."
