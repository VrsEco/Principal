from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import AgentAction, FinancialIngestionRecord, UserLog, WorkflowExecutionLog
from services.financial_service import FinancialService


class OperationalAuditService:
    """Consolida trilhas de auditoria operacionais do APP32.

    O serviço não cria novas tabelas: ele reutiliza os ledgers existentes para
    expor, com escopo multi-tenant obrigatório, a visão de MCP/Sapiens/agentes e
    revisões humanas que alimentam o catálogo único de tools.
    """

    DEFAULT_LIMIT = 50
    MAX_LIMIT = 200
    VALID_SOURCES = {"human_review", "sapiens_workflow", "agent_action"}

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

        if cls._should_include(normalized_source, "human_review"):
            events.extend(cls._collect_human_review_events(company_id=company_id, limit=normalized_limit))
        if cls._should_include(normalized_source, "sapiens_workflow"):
            events.extend(cls._collect_workflow_events(company_id=company_id, limit=normalized_limit))
        if cls._should_include(normalized_source, "agent_action"):
            events.extend(cls._collect_agent_action_events(company_id=company_id, limit=normalized_limit))

        events = sorted(events, key=cls._sort_key, reverse=True)[:normalized_limit]
        summary = cls._build_summary(events)

        return {
            "company_id": int(company_id),
            "filters": {"source": normalized_source or "all", "limit": normalized_limit},
            "summary": summary,
            "events": events,
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

        user_logs = (
            UserLog.query.filter(
                UserLog.company_id == company_id,
                UserLog.entity_type == "financial_ingestion_record",
            )
            .order_by(UserLog.created_at.desc(), UserLog.id.desc())
            .limit(limit)
            .all()
        )
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

    @staticmethod
    def _actor_label(actor: Dict[str, Any]) -> str:
        return actor.get("user_name") or actor.get("user_email") or actor.get("agent") or "Usuário APP32"

    @staticmethod
    def _title_for_human_review(record: Any, event_type: str) -> str:
        reference = getattr(record, "origin_reference", None) or getattr(record, "source_file_name", None) or f"registro {getattr(record, 'id', '')}"
        return f"{event_type} · {reference}"

    @staticmethod
    def _truncate(value: str, size: int = 240) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= size:
            return text
        return f"{text[: size - 1]}…"
