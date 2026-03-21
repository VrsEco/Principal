import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_ingestion_service import FinancialIngestionService
import services.financial_ingestion_service as ingestion_module


def test_sanitize_json_converts_datetime_date_decimal_and_sequences():
    payload = {
        "captured_at": datetime(2026, 3, 20, 10, 30, 0),
        "due_date": date(2026, 3, 31),
        "amount": Decimal("1500.75"),
        "tags": {"ocr", "invoice"},
        "timeline": [date(2026, 3, 20), datetime(2026, 3, 20, 11, 45, 0)],
    }

    sanitized = FinancialIngestionService._sanitize_json(payload)

    assert sanitized["captured_at"] == "2026-03-20T10:30:00"
    assert sanitized["due_date"] == "2026-03-31"
    assert sanitized["amount"] == 1500.75
    assert sorted(sanitized["tags"]) == ["invoice", "ocr"]
    assert sanitized["timeline"] == ["2026-03-20", "2026-03-20T11:45:00"]


def test_create_record_sanitizes_ocr_payload_before_insert(monkeypatch):
    captured = {}

    class _FakeRecord:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)
            self.related_schedule = None
            self.related_entry = None

    monkeypatch.setattr(
        ingestion_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )
    monkeypatch.setattr(
        ingestion_module.FinancialIngestionService,
        "_validate_related_links",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(ingestion_module, "FinancialIngestionRecord", _FakeRecord)
    monkeypatch.setattr(ingestion_module.db.session, "add", lambda record: captured.setdefault("added", record))
    monkeypatch.setattr(ingestion_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(ingestion_module.db.session, "refresh", lambda record: None)
    monkeypatch.setattr(
        ingestion_module.FinancialIngestionService,
        "_serialize",
        lambda record: {
            "raw_payload_json": record.raw_payload_json,
            "normalized_payload_json": record.normalized_payload_json,
            "metadata_json": record.metadata_json,
        },
    )

    result, error = FinancialIngestionService.create_record(
        payload={
            "company_id": 9,
            "origin_type": "sapiens_image",
            "origin_reference": "ocr-image-001",
            "raw_payload_json": {
                "captured_at": datetime(2026, 3, 20, 10, 30, 0),
                "received_on": date(2026, 3, 20),
            },
            "normalized_payload_json": {
                "description": "Fatura OCR",
                "due_date": date(2026, 3, 31),
                "amount": Decimal("1500.75"),
            },
            "metadata_json": {
                "pipeline": "image-processing",
                "timeline": [date(2026, 3, 20), datetime(2026, 3, 20, 11, 0, 0)],
            },
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert captured["committed"] is True
    assert captured["kwargs"]["raw_payload_json"]["captured_at"] == "2026-03-20T10:30:00"
    assert captured["kwargs"]["raw_payload_json"]["received_on"] == "2026-03-20"
    assert captured["kwargs"]["normalized_payload_json"]["due_date"] == "2026-03-31"
    assert captured["kwargs"]["normalized_payload_json"]["amount"] == 1500.75
    assert captured["kwargs"]["metadata_json"]["timeline"] == [
        "2026-03-20",
        "2026-03-20T11:00:00",
    ]
