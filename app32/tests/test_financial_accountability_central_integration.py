import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_automation_service as automation_module
from services.financial_automation_service import FinancialAutomationService


def test_ingest_accountability_documents_uploads_parses_and_returns_records(monkeypatch):
    calls = {}

    def fake_upload(**kwargs):
        calls["upload"] = kwargs
        return {
            "batch": {"id": 91, "origin_type": "accountability"},
            "documents": [{"id": 10, "file_name": "recibo.pdf"}],
            "records": [],
        }, None

    def fake_parse(**kwargs):
        calls["parse"] = kwargs
        return {
            "batch": {"id": 91, "origin_type": "accountability"},
            "records": [{"id": 700, "description": "Recibo taxi"}],
            "parsed_documents": 1,
            "skipped_documents": 0,
            "count": 1,
        }, None

    monkeypatch.setattr(automation_module.FinancialAutomationService, "upload_batch_files", fake_upload)
    monkeypatch.setattr(automation_module.FinancialAutomationService, "parse_batch_documents", fake_parse)

    result, error = FinancialAutomationService.ingest_accountability_documents(
        company_id=9,
        files=[object()],
        upload_root="C:/tmp/uploads",
        source_label="Prestação abril",
        created_by_user_id=7,
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["contract_version"] == "financial_accountability_central_v1"
    assert result["origin_type"] == "accountability"
    assert result["count"] == 1
    assert result["records"][0]["description"] == "Recibo taxi"
    assert calls["upload"]["origin_type"] == "accountability"
    assert calls["upload"]["source_label"] == "Prestação abril"
    assert calls["parse"]["batch_id"] == 91
    assert calls["parse"]["performed_by_user_id"] == 7


def test_ingest_accountability_documents_propagates_upload_error(monkeypatch):
    monkeypatch.setattr(
        automation_module.FinancialAutomationService,
        "upload_batch_files",
        lambda **kwargs: (None, "Selecione ao menos um arquivo para upload na Central."),
    )

    result, error = FinancialAutomationService.ingest_accountability_documents(
        company_id=9,
        files=[],
        upload_root="C:/tmp/uploads",
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Selecione ao menos um arquivo para upload na Central."
