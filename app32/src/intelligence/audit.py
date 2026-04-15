from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from flask import has_app_context
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import inspect, text


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AIExecutionAuditRecord(_StrictModel):
    """Registro mínimo de auditoria para execuções AI/MCP do APP32."""

    event_type: str = Field(min_length=1, max_length=80)
    runtime: str = Field(min_length=1, max_length=40)
    status: str = Field(min_length=1, max_length=40)
    domain: str | None = Field(default=None, min_length=1, max_length=80)
    operation: str | None = Field(default=None, min_length=1, max_length=120)
    tool_name: str | None = Field(default=None, min_length=1, max_length=120)
    scope: str | None = Field(default=None, min_length=1, max_length=40)
    company_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    thread_id: str | None = Field(default=None, min_length=1, max_length=120)
    execution_id: str | None = Field(default=None, min_length=1, max_length=120)
    request_id: str | None = Field(default=None, min_length=1, max_length=120)
    trace_id: str | None = Field(default=None, min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _ensure_timezone(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at deve ser timezone-aware.")
        return self


def build_ai_execution_audit_record(
    *,
    event_type: str,
    runtime: str,
    status: str,
    domain: str | None = None,
    operation: str | None = None,
    tool_name: str | None = None,
    scope: str | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
    thread_id: str | None = None,
    execution_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AIExecutionAuditRecord:
    return AIExecutionAuditRecord(
        event_type=event_type,
        runtime=runtime,
        status=status,
        domain=domain,
        operation=operation,
        tool_name=tool_name,
        scope=scope,
        company_id=company_id,
        user_id=user_id,
        thread_id=thread_id,
        execution_id=execution_id,
        request_id=request_id,
        trace_id=trace_id,
        metadata=dict(metadata or {}),
    )


AI_MCP_AUDIT_RETENTION_DAYS = 180
AI_MCP_AUDIT_SCHEMA_VERSION = "2026-04-10.v1"
AI_MCP_AUDIT_REDACTED_METADATA_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
    }
)


class AIExecutionAuditPersistencePlan(_StrictModel):
    """Contrato de persistência para auditoria IA/MCP."""

    schema_version: str = AI_MCP_AUDIT_SCHEMA_VERSION
    table_name: str = "ai_mcp_audit_events"
    retention_days: int = Field(default=AI_MCP_AUDIT_RETENTION_DAYS, ge=30)
    partition_key: str = "company_id"
    required_indexes: tuple[str, ...] = (
        "ix_ai_mcp_audit_events_company_occurred_at",
        "ix_ai_mcp_audit_events_user_occurred_at",
        "ix_ai_mcp_audit_events_runtime_tool_occurred_at",
        "ix_ai_mcp_audit_events_trace_id",
    )
    required_columns: tuple[str, ...] = (
        "id",
        "schema_version",
        "event_type",
        "runtime",
        "status",
        "domain",
        "operation",
        "tool_name",
        "scope",
        "company_id",
        "user_id",
        "thread_id",
        "execution_id",
        "request_id",
        "trace_id",
        "metadata_json",
        "occurred_at",
        "created_at",
    )
    redacted_metadata_keys: tuple[str, ...] = tuple(sorted(AI_MCP_AUDIT_REDACTED_METADATA_KEYS))

    @model_validator(mode="after")
    def _ensure_company_partition(self):
        if self.partition_key != "company_id":
            raise ValueError("auditoria IA/MCP deve particionar/filtrar por company_id")
        if "company_id" not in self.required_columns:
            raise ValueError("company_id é obrigatório no plano de persistência")
        if not any("company" in index and "occurred_at" in index for index in self.required_indexes):
            raise ValueError("índice por company_id/occurred_at é obrigatório")
        return self


def build_ai_execution_audit_persistence_plan() -> AIExecutionAuditPersistencePlan:
    return AIExecutionAuditPersistencePlan()


def redact_ai_audit_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Reduz risco de persistir segredo em metadata livre antes de gravar auditoria."""

    redacted: dict[str, Any] = {}
    for key, value in dict(metadata or {}).items():
        normalized_key = str(key).strip().lower()
        if normalized_key in AI_MCP_AUDIT_REDACTED_METADATA_KEYS:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            redacted[key] = redact_ai_audit_metadata(value)
        else:
            redacted[key] = value
    return redacted


def build_persistable_ai_execution_audit_payload(record: AIExecutionAuditRecord) -> dict[str, Any]:
    """Prepara payload compatível com a persistência PostgreSQL."""

    payload = record.model_dump(mode="json")
    payload["schema_version"] = AI_MCP_AUDIT_SCHEMA_VERSION
    payload["metadata"] = redact_ai_audit_metadata(record.metadata)
    payload["metadata_json"] = payload.pop("metadata")
    return payload


def _ensure_ai_execution_audit_table() -> None:
    from models import db

    plan = build_ai_execution_audit_persistence_plan()
    table_name = plan.table_name
    inspector = inspect(db.engine)

    with db.engine.begin() as conn:
        if not inspector.has_table(table_name):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id BIGSERIAL PRIMARY KEY,
                        schema_version VARCHAR(40) NOT NULL,
                        event_type VARCHAR(80) NOT NULL,
                        runtime VARCHAR(40) NOT NULL,
                        status VARCHAR(40) NOT NULL,
                        domain VARCHAR(80),
                        operation VARCHAR(120),
                        tool_name VARCHAR(120),
                        scope VARCHAR(40),
                        company_id INTEGER,
                        user_id INTEGER,
                        thread_id VARCHAR(120),
                        execution_id VARCHAR(120),
                        request_id VARCHAR(120),
                        trace_id VARCHAR(120),
                        metadata_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        occurred_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )

        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {plan.required_indexes[0]} ON {table_name} (company_id, occurred_at DESC)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {plan.required_indexes[1]} ON {table_name} (user_id, occurred_at DESC)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {plan.required_indexes[2]} ON {table_name} (runtime, tool_name, occurred_at DESC)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {plan.required_indexes[3]} ON {table_name} (trace_id)"))


def persist_ai_execution_audit_event(record: AIExecutionAuditRecord) -> dict[str, Any]:
    """Persiste auditoria IA/MCP em PostgreSQL."""

    from models import db

    payload = build_persistable_ai_execution_audit_payload(record)
    plan = build_ai_execution_audit_persistence_plan()
    _ensure_ai_execution_audit_table()

    db.session.execute(
        text(
            f"""
            INSERT INTO {plan.table_name} (
                schema_version,
                event_type,
                runtime,
                status,
                domain,
                operation,
                tool_name,
                scope,
                company_id,
                user_id,
                thread_id,
                execution_id,
                request_id,
                trace_id,
                metadata_json,
                occurred_at
            ) VALUES (
                :schema_version,
                :event_type,
                :runtime,
                :status,
                :domain,
                :operation,
                :tool_name,
                :scope,
                :company_id,
                :user_id,
                :thread_id,
                :execution_id,
                :request_id,
                :trace_id,
                CAST(:metadata_json AS JSONB),
                :occurred_at
            )
            """
        ),
        {
            **payload,
            "metadata_json": json.dumps(payload["metadata_json"], ensure_ascii=False, default=str),
        },
    )
    db.session.commit()
    return payload


def emit_ai_execution_audit_event(
    record: AIExecutionAuditRecord,
    *,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Emite auditoria estruturada e persiste em PostgreSQL sem quebrar o fluxo IA/MCP."""

    payload = record.model_dump(mode="json")
    safe_logger = logger or logging.getLogger("src.intelligence.audit")
    try:
        safe_logger.info("AI_MCP_AUDIT %s", json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
    except Exception:  # pragma: no cover - auditoria jamais pode interromper o runtime
        safe_logger.debug("Falha ao serializar auditoria AI/MCP", exc_info=True)

    persistence_target = build_ai_execution_audit_persistence_plan().table_name
    if has_app_context():
        try:
            persisted_payload = persist_ai_execution_audit_event(record)
            payload["persistence"] = {
                "target": persistence_target,
                "status": "persisted",
                "schema_version": persisted_payload.get("schema_version"),
            }
        except Exception:  # pragma: no cover - persistência jamais pode interromper o runtime
            safe_logger.debug("Falha ao persistir auditoria AI/MCP em PostgreSQL", exc_info=True)
            payload["persistence"] = {"target": persistence_target, "status": "failed"}
    else:
        payload["persistence"] = {"target": persistence_target, "status": "skipped_no_app_context"}

    return payload
