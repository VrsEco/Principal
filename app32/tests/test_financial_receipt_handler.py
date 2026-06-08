import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers.financial_receipt_handler import (
    FinancialReceiptIngestExecutionHandler,
    FinancialReceiptIngestRequest,
)


def test_financial_receipt_handler_stages_file_and_returns_batch_summary():
    captured = {}

    handler = FinancialReceiptIngestExecutionHandler(
        upload_root_provider=lambda: "C:/tmp/uploads",
        stage_channel_documents=lambda **kwargs: (
            captured.update(kwargs) or {
                "batch": {"id": 41},
                "documents": [{"id": 12, "file_name": "recibo_taxi.pdf"}],
                "records": [{
                    "id": 99,
                    "document_type": "receipt_pdf",
                    "description": "Recibo - Taxi",
                    "status": "imported",
                    "metadata_json": {"dedupe": {"status": "unique"}},
                }],
                "record": {
                    "id": 99,
                    "document_type": "receipt_pdf",
                    "description": "Recibo - Taxi",
                    "status": "imported",
                    "metadata_json": {"dedupe": {"status": "unique"}},
                },
            },
            None,
        ),
    )

    result = handler.execute(
        FinancialReceiptIngestRequest(
            payload={
                "_attachment": {
                    "file_name": "recibo_taxi.pdf",
                    "mime_type": "application/pdf",
                    "file_bytes": b"%PDF-1.4 fake",
                },
                "_channel_label": "WhatsApp",
            },
            active_company_id=9,
            user_id=7,
        )
    )

    assert captured["company_id"] == 9
    assert captured["user_id"] == 7
    assert captured["documents"][0]["file_name"] == "recibo_taxi.pdf"
    assert captured["source_metadata"]["source_channel"] == "whatsapp"
    assert "Lote: 41" in result.response_text
    assert "Registro: 99" in result.response_text


def test_financial_receipt_handler_passes_deterministic_source_metadata():
    captured = {}

    handler = FinancialReceiptIngestExecutionHandler(
        upload_root_provider=lambda: "C:/tmp/uploads",
        stage_channel_documents=lambda **kwargs: (
            captured.update(kwargs) or {"batch": {"id": 1}, "documents": [{"id": 1}], "records": [{"id": 2}], "record": {"id": 2}},
            None,
        ),
    )

    handler.execute(
        FinancialReceiptIngestRequest(
            payload={
                "_attachment": {
                    "file_name": "recibo_taxi.pdf",
                    "mime_type": "application/pdf",
                    "file_bytes": b"%PDF-1.4 fake",
                },
                "_channel_label": "WhatsApp",
                "_source_channel": "whatsapp",
                "_source_contact": "5571996426565",
                "_source_external_reference": "wamid-123",
                "_thread_id": "wa_5571996426565",
            },
            active_company_id=9,
            user_id=7,
        )
    )

    assert captured["source_metadata"] == {
        "source_channel": "whatsapp",
        "source_contact": "5571996426565",
        "source_external_reference": "wamid-123",
        "source_thread_id": "wa_5571996426565",
    }


def test_financial_receipt_handler_groups_multiple_files_in_same_batch():
    captured = {}

    handler = FinancialReceiptIngestExecutionHandler(
        upload_root_provider=lambda: "C:/tmp/uploads",
        stage_channel_documents=lambda **kwargs: (
            captured.update(kwargs) or {
                "batch": {"id": 77},
                "documents": [
                    {"id": 1, "file_name": "img_1.jpg"},
                    {"id": 2, "file_name": "img_2.jpg"},
                ],
                "records": [
                    {"id": 10, "status": "imported"},
                    {"id": 11, "status": "imported"},
                ],
                "record": {"id": 10},
            },
            None,
        ),
    )

    result = handler.execute(
        FinancialReceiptIngestRequest(
            payload={
                "_attachments": [
                    {"file_name": "img_1.jpg", "mime_type": "image/jpeg", "file_bytes": b"img-1"},
                    {"file_name": "img_2.jpg", "mime_type": "image/jpeg", "file_bytes": b"img-2"},
                ],
                "_channel_label": "WhatsApp",
                "_source_label": "WhatsApp - 2 arquivo(s)",
            },
            active_company_id=9,
            user_id=7,
        )
    )

    assert len(captured["documents"]) == 2
    assert captured["documents"][0]["file_name"] == "img_1.jpg"
    assert captured["documents"][1]["file_name"] == "img_2.jpg"
    assert "Lote: 77" in result.response_text
    assert "Documentos no lote: 2" in result.response_text
    assert "tratados separadamente" in result.response_text
