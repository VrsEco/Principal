from __future__ import annotations

from src.intelligence.audit import (
    build_ai_execution_audit_record,
    build_persistable_ai_execution_audit_payload,
    emit_ai_execution_audit_event,
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
