from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.intelligence.audit import (
    AIExecutionAuditPersistencePlan,
    build_ai_execution_audit_persistence_plan,
    build_ai_execution_audit_record,
    build_persistable_ai_execution_audit_payload,
    redact_ai_audit_metadata,
)


def test_persistence_plan_requires_company_partition_and_indexes() -> None:
    plan = build_ai_execution_audit_persistence_plan()

    assert plan.table_name == "ai_mcp_audit_events"
    assert plan.partition_key == "company_id"
    assert "company_id" in plan.required_columns
    assert "ix_ai_mcp_audit_events_company_occurred_at" in plan.required_indexes
    assert plan.retention_days >= 180

    with pytest.raises(ValidationError):
        AIExecutionAuditPersistencePlan(partition_key="user_id")


def test_audit_metadata_redaction_is_recursive() -> None:
    metadata = {
        "token": "abc",
        "nested": {"password": "123", "safe": "ok"},
        "safe": 42,
    }

    assert redact_ai_audit_metadata(metadata) == {
        "token": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "safe": "ok"},
        "safe": 42,
    }


def test_persistable_payload_uses_metadata_json_and_schema_version() -> None:
    record = build_ai_execution_audit_record(
        event_type="mcp.tool.executed",
        runtime="mcp_user",
        status="allowed",
        domain="routine",
        operation="read",
        tool_name="list_project_tasks",
        scope="user",
        company_id=31,
        user_id=8,
        metadata={"authorization": "Bearer secret", "rows": 3},
    )

    payload = build_persistable_ai_execution_audit_payload(record)

    assert payload["schema_version"].startswith("2026-04-10")
    assert "metadata" not in payload
    assert payload["metadata_json"] == {"authorization": "[REDACTED]", "rows": 3}
    assert payload["company_id"] == 31
    assert payload["tool_name"] == "list_project_tasks"
