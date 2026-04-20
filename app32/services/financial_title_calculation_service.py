from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple

from models import FinancialSchedule, FinancialTitleCalculationLog
from services.financial_service import FinancialService


class FinancialTitleCalculationService:
    """Consultas da memória de cálculo dos Títulos Financeiros.

    Mantém a regra de multi-tenancy fora das rotas e entrega uma visão
    auditável dos eventos de cálculo gerados a cada Baixa.
    """

    DEFAULT_LIMIT = 100
    MAX_LIMIT = 500

    @staticmethod
    def _normalize_limit(limit: Optional[int]) -> int:
        try:
            normalized = int(limit or FinancialTitleCalculationService.DEFAULT_LIMIT)
        except (TypeError, ValueError):
            normalized = FinancialTitleCalculationService.DEFAULT_LIMIT
        return max(1, min(normalized, FinancialTitleCalculationService.MAX_LIMIT))

    @staticmethod
    def _serialize_log(log: FinancialTitleCalculationLog) -> Dict[str, Any]:
        payload = log.to_dict() if hasattr(log, "to_dict") else dict(log.__dict__)
        snapshot = dict(payload.get("snapshot_json") or {})
        metadata = dict(payload.get("metadata_json") or {})
        before = dict(snapshot.get("before") or metadata.get("before") or {})
        current = dict(snapshot.get("current") or metadata.get("current") or {})
        after = dict(snapshot.get("after") or metadata.get("after") or {})
        payload["memory_contract_version"] = (
            snapshot.get("contract_version")
            or metadata.get("memory_contract_version")
            or metadata.get("ledger_version")
        )
        payload["memory_timeline"] = {
            "before": before,
            "current": current,
            "after": after,
        }
        payload["actor"] = dict(metadata.get("actor") or {})
        payload["evidence"] = dict(metadata.get("evidence") or {})
        payload["component_summary"] = dict(metadata.get("component_summary") or {})
        return payload

    @staticmethod
    def list_title_calculation_logs(
        *,
        company_id: int,
        schedule_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        limit: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        title = (
            FinancialSchedule.query.filter(
                FinancialSchedule.id == schedule_id,
                FinancialSchedule.company_id == company_id,
                FinancialSchedule.deleted_at.is_(None),
            )
            .first()
        )
        if not title:
            return None, "Título financeiro não encontrado no escopo da empresa."

        normalized_limit = FinancialTitleCalculationService._normalize_limit(limit)
        logs = (
            FinancialTitleCalculationLog.query.filter(
                FinancialTitleCalculationLog.company_id == company_id,
                FinancialTitleCalculationLog.financial_schedule_id == schedule_id,
            )
            .order_by(
                FinancialTitleCalculationLog.calculation_date.desc(),
                FinancialTitleCalculationLog.id.desc(),
            )
            .limit(normalized_limit)
            .all()
        )

        return {
            "schedule": title.to_dict() if hasattr(title, "to_dict") else {
                "id": getattr(title, "id", schedule_id),
                "company_id": getattr(title, "company_id", company_id),
                "schedule_code": getattr(title, "schedule_code", None),
            },
            "logs": [FinancialTitleCalculationService._serialize_log(log) for log in logs],
            "count": len(logs),
            "limit": normalized_limit,
        }, None
