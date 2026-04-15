from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import inspect, text

from models import AgentAction, FinancialIngestionRecord, UserLog, WorkflowExecutionLog, db
from services.financial_service import FinancialService
from services.workflow_approval_service import (
    build_workflow_approval_metrics,
    serialize_workflow_approval_action,
)


logger = logging.getLogger(__name__)


class OperationalAuditService:
    """Consolida trilhas de auditoria operacionais e IA/MCP do APP32."""

    DEFAULT_LIMIT = 50
    MAX_LIMIT = 200
    VALID_SOURCES = {"ai_mcp_runtime", "human_review", "sapiens_workflow", "agent_action"}

    @classmethod
    def build_panel(
        cls,
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        source: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        normalized_source = (source or "").strip() or None
        if normalized_source and normalized_source not in cls.VALID_SOURCES:
            return None, "Fonte de auditoria operacional inválida."

        normalized_limit = cls._normalize_limit(limit)
        events: List[Dict[str, Any]] = []

        if cls._should_include(normalized_source, "ai_mcp_runtime"):
            events.extend(
                cls._safe_collect(
                    "ai_mcp_runtime",
                    cls._collect_ai_mcp_runtime_events,
                    company_id=company_id,
                    limit=normalized_limit,
                )
            )
        if cls._should_include(normalized_source, "human_review"):
            events.extend(cls._safe_collect("human_review", cls._collect_human_review_events, company_id=company_id, limit=normalized_limit))
        if cls._should_include(normalized_source, "sapiens_workflow"):
            events.extend(cls._safe_collect("sapiens_workflow", cls._collect_workflow_events, company_id=company_id, limit=normalized_limit))
        if cls._should_include(normalized_source, "agent_action"):
            events.extend(cls._safe_collect("agent_action", cls._collect_agent_action_events, company_id=company_id, limit=normalized_limit))

        events = sorted(events, key=cls._sort_key, reverse=True)[:normalized_limit]
        approvals = cls._safe_collect("workflow_approvals", cls._collect_workflow_approvals, company_id=company_id, limit=min(normalized_limit, 25))
        approvals_summary = build_workflow_approval_metrics([item["_action"] for item in approvals if item.get("_action")])
        approvals = [{key: value for key, value in item.items() if key != "_action"} for item in approvals]
        summary = cls._build_summary(events)

        return {
            "company_id": int(company_id),
            "filters": {"source": normalized_source or "all", "limit": normalized_limit},
            "summary": summary,
            "analytics": cls._build_analytics(events, approvals),
            "events": events,
            "approvals": approvals,
            "approvals_summary": approvals_summary,
        }, None

    @classmethod
    def _normalize_limit(cls, limit: Any) -> int:
        try:
            parsed = int(limit)
        except (TypeError, ValueError):
            parsed = cls.DEFAULT_LIMIT
        return max(1, min(parsed, cls.MAX_LIMIT))

    @staticmethod
    def _should_include(selected_source: Optional[str], candidate: str) -> bool:
        return selected_source in {None, candidate}

    @classmethod
    def _safe_collect(cls, source_name: str, collector, **kwargs) -> List[Dict[str, Any]]:
        try:
            return collector(**kwargs)
        except Exception:
            db.session.rollback()
            logger.exception("Falha ao coletar eventos de auditoria operacional para a fonte %s.", source_name)
            return [
                {
                    "source": source_name,
                    "title": f"Falha na coleta da fonte {source_name}",
                    "description": "A fonte apresentou divergência de schema ou erro operacional. A tela foi mantida ativa em modo resiliente.",
                    "actor": "Sistema",
                    "entity_type": "audit_source",
                    "entity_id": None,
                    "status": "degraded",
                    "channel": source_name,
                    "created_at": cls._iso(datetime.now()),
                    "raw": {"source": source_name, "status": "degraded"},
                }
            ]

    @classmethod
    def _build_summary(cls, events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        by_source = {source: 0 for source in sorted(cls.VALID_SOURCES)}
        by_status: Dict[str, int] = {}
        for event in events:
            source = event.get("source") or "unknown"
            status = event.get("status") or "unknown"
            if source in by_source:
                by_source[source] += 1
            by_status[status] = by_status.get(status, 0) + 1
        return {"total": len(events), "by_source": by_source, "by_status": by_status}

    @classmethod
    def _build_analytics(cls, events: Sequence[Dict[str, Any]], approvals: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        by_tool = Counter()
        by_domain = Counter()
        by_runtime = Counter()
        by_status = Counter()
        for event in events:
            runtime = str(event.get("runtime") or event.get("source") or "unknown")
            status = str(event.get("status") or "unknown")
            tool_name = str(event.get("tool_name") or "").strip()
            domain = str(event.get("domain") or "").strip()
            by_runtime[runtime] += 1
            by_status[status] += 1
            if tool_name:
                by_tool[tool_name] += 1
            if domain:
                by_domain[domain] += 1

        pending_approvals = sum(1 for item in approvals if (item.get("approval") or {}).get("approval_status") == "pending")
        tool_gate_pending = sum(
            1
            for item in approvals
            if (item.get("approval") or {}).get("approval_status") == "pending"
            and str((item.get("approval") or {}).get("action_key") or "").startswith("tool.")
        )

        return {
            "top_tools": [{"name": name, "count": count} for name, count in by_tool.most_common(8)],
            "top_domains": [{"name": name, "count": count} for name, count in by_domain.most_common(8)],
            "by_runtime": dict(by_runtime),
            "by_status": dict(by_status),
            "cards": [
                {"id": "events_total", "label": "Eventos auditados", "value": len(events), "hint": "Linha do tempo consolidada"},
                {"id": "human_gate_pending", "label": "Approvals pendentes", "value": pending_approvals, "hint": "Fila operacional aberta"},
                {"id": "tool_gate_pending", "label": "Tools aguardando gate", "value": tool_gate_pending, "hint": "Pedidos sensíveis do runtime"},
                {"id": "blocked_total", "label": "Bloqueios/gates", "value": by_status.get("blocked", 0) + by_status.get("human_gate_requested", 0), "hint": "Governança em ação"},
            ],
        }

    @staticmethod
    def _sort_key(event: Dict[str, Any]) -> datetime:
        value = event.get("created_at") or event.get("timestamp")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return datetime.min
        return datetime.min

    @staticmethod
    def _iso(value: Any) -> Optional[str]:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    @classmethod
    def _collect_ai_mcp_runtime_events(cls, *, company_id: int, limit: int) -> List[Dict[str, Any]]:
        inspector = inspect(db.engine)
        if not inspector.has_table("ai_mcp_audit_events"):
            return []

        rows = db.session.execute(
            text(
                """
                SELECT id, event_type, runtime, status, domain, operation, tool_name, scope,
                       company_id, user_id, thread_id, execution_id, request_id, trace_id,
                       metadata_json, occurred_at, created_at
                  FROM ai_mcp_audit_events
                 WHERE company_id = :company_id
                 ORDER BY occurred_at DESC, id DESC
                 LIMIT :limit
                """
            ),
            {"company_id": int(company_id), "limit": int(limit)},
        ).mappings().all()

        events: list[dict[str, Any]] = []
        for row in rows:
            metadata = dict(row.get("metadata_json") or {})
            tool_name = row.get("tool_name")
            domain = row.get("domain")
            status = row.get("status")
            runtime = row.get("runtime")
            events.append(
                {
                    "source": "ai_mcp_runtime",
                    "title": cls._build_ai_runtime_title(row),
                    "description": cls._build_ai_runtime_description(row, metadata),
                    "actor": f"user:{row.get('user_id')}" if row.get("user_id") else (runtime or "runtime"),
                    "entity_type": "ai_mcp_audit_event",
                    "entity_id": row.get("id"),
                    "status": status,
                    "channel": row.get("scope") or runtime,
                    "created_at": cls._iso(row.get("occurred_at") or row.get("created_at")),
                    "raw": dict(row),
                    "runtime": runtime,
                    "domain": domain,
                    "tool_name": tool_name,
                    "operation": row.get("operation"),
                    "scope": row.get("scope"),
                    "thread_id": row.get("thread_id"),
                    "trace_id": row.get("trace_id"),
                    "request_id": row.get("request_id"),
                    "metadata_preview": metadata,
                }
            )
        return events

    @classmethod
    def _collect_human_review_events(cls, *, company_id: int, limit: int) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        records = (
            FinancialIngestionRecord.query.filter(
                FinancialIngestionRecord.company_id == company_id,
                FinancialIngestionRecord.deleted_at.is_(None),
            )
            .order_by(FinancialIngestionRecord.updated_at.desc(), FinancialIngestionRecord.id.desc())
            .limit(limit)
            .all()
        )
        for record in records:
            metadata = record.metadata_json or {}
            trail = metadata.get("guided_audit_trail") or []
            for audit_item in trail[-limit:]:
                if not isinstance(audit_item, dict):
                    continue
                actor = audit_item.get("actor") or {}
                event_type = audit_item.get("event_type") or "human_review"
                events.append(
                    {
                        "source": "human_review",
                        "title": cls._title_for_human_review(record, event_type),
                        "description": audit_item.get("description") or "Revisão humana registrada na ingestão financeira.",
                        "actor": cls._actor_label(actor),
                        "entity_type": "financial_ingestion_record",
                        "entity_id": getattr(record, "id", None),
                        "status": event_type,
                        "channel": getattr(record, "source_channel", None) or "financial_ingestion",
                        "created_at": audit_item.get("timestamp") or cls._iso(getattr(record, "updated_at", None)),
                        "raw": audit_item,
                    }
                )

        try:
            user_logs = (
                UserLog.query.filter(
                    UserLog.company_id == company_id,
                    UserLog.entity_type == "financial_ingestion_record",
                )
                .order_by(UserLog.created_at.desc(), UserLog.id.desc())
                .limit(limit)
                .all()
            )
        except Exception:
            db.session.rollback()
            logger.exception("Falha ao consultar UserLog na auditoria operacional da empresa %s.", company_id)
            user_logs = []

        for log in user_logs:
            events.append(
                {
                    "source": "human_review",
                    "title": getattr(log, "entity_name", None) or f"{getattr(log, 'action', 'AUDIT')} financeiro",
                    "description": getattr(log, "description", None) or "Registro de auditoria de usuário.",
                    "actor": getattr(log, "user_name", None) or getattr(log, "user_email", None) or "Usuário APP32",
                    "entity_type": getattr(log, "entity_type", None),
                    "entity_id": getattr(log, "entity_id", None),
                    "status": getattr(log, "action", None),
                    "channel": getattr(log, "endpoint", None) or "user_log",
                    "created_at": cls._iso(getattr(log, "created_at", None)),
                    "raw": log.to_dict() if hasattr(log, "to_dict") else {},
                }
            )

        return events

    @classmethod
    def _collect_workflow_events(cls, *, company_id: int, limit: int) -> List[Dict[str, Any]]:
        logs = (
            WorkflowExecutionLog.query.filter(WorkflowExecutionLog.company_id == company_id)
            .order_by(WorkflowExecutionLog.created_at.desc(), WorkflowExecutionLog.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "source": "sapiens_workflow",
                "title": f"Workflow {log.workflow_code}",
                "description": cls._truncate(log.request_text or log.response_text or "Execução de workflow Sapiens/MCP registrada."),
                "actor": f"user:{log.user_id}" if getattr(log, "user_id", None) else "Sapiens/MCP",
                "entity_type": "workflow_execution_log",
                "entity_id": log.id,
                "status": log.status,
                "channel": log.channel,
                "created_at": cls._iso(log.created_at),
                "raw": log.to_dict() if hasattr(log, "to_dict") else {},
            }
            for log in logs
        ]

    @classmethod
    def _collect_agent_action_events(cls, *, company_id: int, limit: int) -> List[Dict[str, Any]]:
        actions = (
            AgentAction.query.filter(AgentAction.company_id == company_id)
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "source": "agent_action",
                "title": action.title,
                "description": action.description,
                "actor": action.requesting_agent or action.handling_agent or "Agente APP32",
                "entity_type": "agent_action",
                "entity_id": action.id,
                "status": action.status,
                "channel": action.type,
                "created_at": cls._iso(action.created_at),
                "raw": action.to_dict() if hasattr(action, "to_dict") else {},
            }
            for action in actions
        ]

    @classmethod
    def _collect_workflow_approvals(cls, *, company_id: int, limit: int) -> List[Dict[str, Any]]:
        actions = (
            AgentAction.query.filter_by(company_id=company_id, type="workflow_approval_request")
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc())
            .limit(limit)
            .all()
        )
        serialized: list[dict[str, Any]] = []
        for action in actions:
            item = serialize_workflow_approval_action(action)
            item["_action"] = action
            serialized.append(item)
        return serialized

    @staticmethod
    def _actor_label(actor: Dict[str, Any]) -> str:
        return actor.get("user_name") or actor.get("user_email") or actor.get("agent") or "Usuário APP32"

    @staticmethod
    def _title_for_human_review(record: Any, event_type: str) -> str:
        reference = getattr(record, "origin_reference", None) or getattr(record, "source_file_name", None) or f"registro {getattr(record, 'id', '')}"
        return f"{event_type} · {reference}"

    @staticmethod
    def _truncate(value: str, size: int = 240) -> str:
        text_value = " ".join(str(value or "").split())
        if len(text_value) <= size:
            return text_value
        return f"{text_value[: size - 1]}…"

    @classmethod
    def _build_ai_runtime_title(cls, row: Dict[str, Any]) -> str:
        tool_name = row.get("tool_name")
        event_type = row.get("event_type")
        if tool_name:
            return f"{tool_name} · {row.get('status') or 'evento'}"
        if event_type:
            return str(event_type)
        return "Evento IA/MCP"

    @classmethod
    def _build_ai_runtime_description(cls, row: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        reason = str(metadata.get("reason") or "").strip()
        if reason:
            return reason
        operation = str(row.get("operation") or "").strip()
        domain = str(row.get("domain") or "").strip()
        runtime = str(row.get("runtime") or "").strip()
        parts = [part for part in (runtime, domain, operation) if part]
        if parts:
            return " · ".join(parts)
        return "Evento persistido da trilha IA/MCP."
