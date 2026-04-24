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
        stage_channel_document=lambda **kwargs: (
            captured.update(kwargs) or {
                "batch": {"id": 41},
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
    assert captured["file_name"] == "recibo_taxi.pdf"
    assert captured["source_metadata"]["source_channel"] == "whatsapp"
    assert "Lote: 41" in result.response_text
    assert "Registro: 99" in result.response_text


def test_financial_receipt_handler_passes_deterministic_source_metadata():
    captured = {}

    handler = FinancialReceiptIngestExecutionHandler(
        upload_root_provider=lambda: "C:/tmp/uploads",
        stage_channel_document=lambda **kwargs: (captured.update(kwargs) or {"batch": {"id": 1}, "record": {"id": 2}}, None),
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
