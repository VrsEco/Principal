from __future__ import annotations

import logging
import pytest

from src.intelligence.audit import (
    build_ai_execution_audit_record,
    build_persistable_ai_execution_audit_payload,
    emit_ai_execution_audit_event,
    AIExecutionAuditPersistenceError,
)


def test_build_persistable_ai_execution_audit_payload_redacts_sensitive_metadata():
    record = build_ai_execution_audit_record(
        event_type="sapiens.test",
        runtime="sapiens",
        status="success",
        company_id=31,
        metadata={
            "password": "123",
            "nested": {"token": "abc", "safe": "ok"},
        },
    )

    payload = build_persistable_ai_execution_audit_payload(record)

    assert payload["schema_version"]
    assert payload["metadata_json"]["password"] == "[REDACTED]"
    assert payload["metadata_json"]["nested"]["token"] == "[REDACTED]"
    assert payload["metadata_json"]["nested"]["safe"] == "ok"


def test_emit_ai_execution_audit_event_marks_skipped_without_app_context():
    record = build_ai_execution_audit_record(
        event_type="mcp.test",
        runtime="mcp",
        status="success",
        company_id=31,
    )

    payload = emit_ai_execution_audit_event(record)

    assert payload["persistence"]["status"] == "skipped_no_app_context"


def test_emit_ai_execution_audit_event_persists_when_app_context(monkeypatch):
    record = build_ai_execution_audit_record(
        event_type="sapiens.tool_policy.blocked",
        runtime="sapiens",
        status="blocked",
        company_id=31,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr("src.intelligence.audit.has_app_context", lambda: True)
    monkeypatch.setattr(
        "src.intelligence.audit.persist_ai_execution_audit_event",
        lambda current: captured.setdefault("payload", build_persistable_ai_execution_audit_payload(current)),
    )

    payload = emit_ai_execution_audit_event(record)

    assert captured["payload"]["schema_version"] == payload["persistence"]["schema_version"]
    assert payload["persistence"]["status"] == "persisted"


def test_audit_redacts_sequences_and_logs_before_persistence(caplog):
    record = build_ai_execution_audit_record(
        event_type="mcp.test", runtime="mcp", status="success", company_id=9,
        metadata={"rows": [{"access_token": "SECRET_VALUE", "nested": [{"client_secret": "SECRET_VALUE"}]}]},
    )
    with caplog.at_level(logging.INFO, logger="src.intelligence.audit"):
        payload = emit_ai_execution_audit_event(record)
    assert "SECRET_VALUE" not in caplog.text
    assert payload["metadata"]["rows"][0]["access_token"] == "[REDACTED]"
    assert build_persistable_ai_execution_audit_payload(record)["metadata_json"] == payload["metadata"]


@pytest.mark.parametrize("app_context", [False, True])
def test_required_audit_persistence_fails_closed(monkeypatch, app_context):
    record = build_ai_execution_audit_record(
        event_type="mcp.test", runtime="mcp", status="allowed", company_id=9,
    )
    monkeypatch.setattr("src.intelligence.audit.has_app_context", lambda: app_context)
    def unavailable(current):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr("src.intelligence.audit.persist_ai_execution_audit_event", unavailable)
    with pytest.raises(AIExecutionAuditPersistenceError, match="auditoria durável indisponível"):
        emit_ai_execution_audit_event(record, require_persistence=True)


def test_optional_audit_persistence_preserves_read_availability(monkeypatch):
    monkeypatch.setattr("src.intelligence.audit.has_app_context", lambda: True)
    def unavailable(current):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr("src.intelligence.audit.persist_ai_execution_audit_event", unavailable)
    record = build_ai_execution_audit_record(event_type="mcp.read", runtime="mcp", status="allowed", company_id=9)
    assert emit_ai_execution_audit_event(record)["persistence"]["status"] == "failed"
