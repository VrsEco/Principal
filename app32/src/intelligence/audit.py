from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from flask import has_app_context
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text


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
    principal_id: int | None = Field(default=None, gt=0)
    auth_method: str | None = Field(default=None, max_length=40)
    client_id: str | None = Field(default=None, max_length=200)
    surface: str | None = Field(default=None, max_length=40)
    token_scopes: list[str] = Field(default_factory=list)
    policy_allowed: bool | None = None
    policy_reason: str | None = Field(default=None, max_length=500)
    approval_request_id: int | None = Field(default=None, gt=0)
    payload_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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
    principal_id: int | None = None,
    auth_method: str | None = None,
    client_id: str | None = None,
    surface: str | None = None,
    token_scopes: list[str] | tuple[str, ...] = (),
    policy_allowed: bool | None = None,
    policy_reason: str | None = None,
    approval_request_id: int | None = None,
    payload_digest: str | None = None,
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
        principal_id=principal_id, auth_method=auth_method, client_id=client_id,
        surface=surface, token_scopes=list(token_scopes), policy_allowed=policy_allowed,
        policy_reason=policy_reason, approval_request_id=approval_request_id,
        payload_digest=payload_digest,
        metadata=dict(metadata or {}),
    )


AI_MCP_AUDIT_RETENTION_DAYS = 180
AI_MCP_AUDIT_SCHEMA_VERSION = "2026-09-16.v2"
AI_MCP_AUDIT_REDACTED_METADATA_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "client_secret",
        "set-cookie",
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
        "ix_ai_mcp_audit_events_company_principal_time",
        "ix_ai_mcp_audit_events_company_policy_time",
        "ix_ai_mcp_audit_events_company_approval",
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
        "principal_id", "auth_method", "client_id", "surface", "token_scopes",
        "policy_allowed", "policy_reason", "approval_request_id", "payload_digest",
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
        elif isinstance(value, (list, tuple)):
            redacted[key] = _redact_audit_sequence(value)
        else:
            redacted[key] = value
    return redacted


def _redact_audit_sequence(values: list | tuple) -> list:
    return [
        redact_ai_audit_metadata(value) if isinstance(value, Mapping)
        else _redact_audit_sequence(value) if isinstance(value, (list, tuple))
        else value
        for value in values
    ]


class AIExecutionAuditPersistenceError(RuntimeError):
    """A operação governada não pode prosseguir sem trilha durável."""


def build_persistable_ai_execution_audit_payload(record: AIExecutionAuditRecord) -> dict[str, Any]:
    """Prepara payload compatível com a persistência PostgreSQL."""

    payload = record.model_dump(mode="json")
    payload["schema_version"] = AI_MCP_AUDIT_SCHEMA_VERSION
    payload["metadata"] = redact_ai_audit_metadata(record.metadata)
    payload["metadata_json"] = payload.pop("metadata")
    return payload


def persist_ai_execution_audit_event(record: AIExecutionAuditRecord) -> dict[str, Any]:
    """Persiste em transação própria; schema pertence exclusivamente ao Alembic."""
    from models import db

    payload = build_persistable_ai_execution_audit_payload(record)
    plan = build_ai_execution_audit_persistence_plan()
    columns = [column for column in plan.required_columns if column not in {"id", "created_at"}]
    json_columns = {"metadata_json", "token_scopes"}
    values = [f"CAST(:{column} AS JSONB)" if column in json_columns else f":{column}" for column in columns]
    parameters = {column: payload[column] for column in columns}
    for column in json_columns:
        parameters[column] = json.dumps(parameters[column], ensure_ascii=False, default=str)
    # Não commitar/rollback a sessão operacional da tool nem criar schema em request.
    with db.engine.begin() as connection:
        connection.execute(text(
            f"INSERT INTO {plan.table_name} ({', '.join(columns)}) VALUES ({', '.join(values)})"
        ), parameters)
    return payload


def emit_ai_execution_audit_event(
    record: AIExecutionAuditRecord,
    *,
    logger: logging.Logger | None = None,
    require_persistence: bool = False,
) -> dict[str, Any]:
    """Emite dados redigidos; ações governadas podem exigir persistência durável."""

    payload = record.model_dump(mode="json")
    payload["metadata"] = redact_ai_audit_metadata(record.metadata)
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

    if require_persistence and payload["persistence"]["status"] != "persisted":
        raise AIExecutionAuditPersistenceError("operação bloqueada: auditoria durável indisponível")
    return payload
