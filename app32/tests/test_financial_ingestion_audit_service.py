import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_ingestion_service import FinancialIngestionService
import services.financial_ingestion_service as ingestion_module


class _FakeColumn:
    def __eq__(self, other):
        return None

    def is_(self, other):
        return None


def test_update_record_registers_guided_audit_trail_and_user_log(monkeypatch):
    added = []
    committed = {"value": False}

    record = SimpleNamespace(
        id=51,
        company_id=9,
        import_batch_id=None,
        related_schedule_id=None,
        related_entry_id=None,
        completion_status="review_required",
        review_status="pending_review",
        review_notes="nota antiga",
        normalized_payload_json={"description": "Antes", "amount": 100, "metadata_json": {}},
        raw_payload_json={},
        llm_response_json={},
        metadata_json={},
        reviewed_at=None,
        origin_reference="Prestação 51",
        source_file_name="prestacao_51.pdf",
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return record

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
    monkeypatch.setattr(
        ingestion_module,
        "FinancialIngestionRecord",
        SimpleNamespace(
            query=_FakeQuery(),
            company_id=_FakeColumn(),
            id=_FakeColumn(),
            deleted_at=_FakeColumn(),
        ),
    )
    monkeypatch.setattr(ingestion_module.db.session, "add", lambda item: added.append(item))
    monkeypatch.setattr(ingestion_module.db.session, "commit", lambda: committed.update(value=True))
    monkeypatch.setattr(ingestion_module.db.session, "refresh", lambda obj: None)
    monkeypatch.setattr(
        ingestion_module.FinancialIngestionService,
        "_serialize",
        lambda obj: {
            "metadata_json": obj.metadata_json,
            "review_notes": obj.review_notes,
            "normalized_payload_json": obj.normalized_payload_json,
        },
    )

    result, error = FinancialIngestionService.update_record(
        record_id=51,
        company_id=9,
        payload={
            "review_notes": "nota nova",
            "normalized_payload_json": {"description": "Depois", "amount": 125, "metadata_json": {}},
        },
        allowed_company_ids=[9],
        audit_context={
            "event_type": "guided_review_update",
            "description": "Atualização guiada",
            "actor": {
                "user_id": 7,
                "user_email": "qa@gestaoversus.com.br",
                "user_name": "QA",
                "endpoint": "/api/financial/ingestions/51",
                "method": "PUT",
            },
        },
    )

    assert error is None
    assert committed["value"] is True
    trail = result["metadata_json"]["guided_audit_trail"]
    assert trail[-1]["event_type"] == "guided_review_update"
    assert trail[-1]["actor"]["user_id"] == 7
    assert trail[-1]["changes"]["review_notes"]["after"] == "nota nova"
    assert trail[-1]["changes"]["normalized_payload_json"]["description"]["after"] == "Depois"
    assert any(getattr(item, "entity_type", "") == "financial_ingestion_record" for item in added)


def test_convert_record_registers_conversion_audit(monkeypatch):
    committed = {"value": False}

    record = SimpleNamespace(
        id=77,
        company_id=9,
        import_batch_id=None,
        related_schedule_id=None,
        related_entry_id=None,
        completion_status="review_required",
        review_status="pending_review",
        review_notes="Pronto para converter",
        normalized_payload_json={"description": "Conta teste", "amount": 200, "entry_type": "payable", "metadata_json": {}},
        raw_payload_json={"amount": 200},
        llm_response_json={},
        metadata_json={},
        reviewed_at=None,
        origin_reference="Prestação 77",
        source_file_name="prestacao_77.pdf",
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return record

    monkeypatch.setattr(
        ingestion_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )
    monkeypatch.setattr(
        ingestion_module,
        "FinancialIngestionRecord",
        SimpleNamespace(
            query=_FakeQuery(),
            company_id=_FakeColumn(),
            id=_FakeColumn(),
            deleted_at=_FakeColumn(),
        ),
    )
    monkeypatch.setattr(
        ingestion_module.FinancialIngestionService,
        "_build_schedule_payload",
        lambda **kwargs: {"company_id": 9, "name": "Conta teste"},
    )
    monkeypatch.setattr(
        ingestion_module.FinancialScheduleService,
        "create_schedule",
        lambda payload, allowed_company_ids=None: ({"id": 901, "name": payload["name"]}, None),
    )
    monkeypatch.setattr(ingestion_module.db.session, "add", lambda item: None)
    monkeypatch.setattr(ingestion_module.db.session, "commit", lambda: committed.update(value=True))
    monkeypatch.setattr(
        ingestion_module.FinancialIngestionService,
        "_serialize",
        lambda obj: {"metadata_json": obj.metadata_json, "related_schedule_id": obj.related_schedule_id},
    )

    result, error = FinancialIngestionService.convert_record(
        record_id=77,
        company_id=9,
        target_type="schedule",
        allowed_company_ids=[9],
        audit_context={
            "actor": {
                "user_id": 9,
                "user_email": "gestor@gestaoversus.com.br",
                "user_name": "Gestor",
            }
        },
    )

    assert error is None
    assert committed["value"] is True
    assert result["schedule"]["id"] == 901
    assert record.related_schedule_id == 901
    trail = result["record"]["metadata_json"]["guided_audit_trail"]
    assert trail[-1]["event_type"] == "guided_conversion"
    assert trail[-1]["metadata"]["target_type"] == "schedule"
    assert trail[-1]["metadata"]["target_id"] == 901
