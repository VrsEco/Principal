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
    def _normalize_memory_phase(
        *,
        phase_name: str,
        block: Optional[Dict[str, Any]],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(block or {})
        if phase_name == "current":
            principal = normalized.get("principal")
            if principal in (None, ""):
                principal = normalized.get("principal_settled")
            if principal in (None, ""):
                principal = payload.get("principal_settled_now") or payload.get("settled_principal_current") or 0

            correction = normalized.get("financial_correction")
            if correction in (None, ""):
                correction = payload.get("adjustments_settled_now") or 0

            discount = normalized.get("discount")
            if discount in (None, ""):
                discount = payload.get("discount_now") or 0

            gross_amount = normalized.get("gross_amount")
            if gross_amount in (None, ""):
                gross_amount = (
                    payload.get("gross_amount")
                    or payload.get("total_due_current")
                    or (float(principal or 0) + float(correction or 0) - float(discount or 0))
                )

            normalized["principal"] = principal
            normalized["financial_correction"] = correction
            normalized["discount"] = discount
            normalized["gross_amount"] = gross_amount
            return normalized

        principal = normalized.get("principal")
        if principal in (None, ""):
            principal = normalized.get("principal_open")
        if principal in (None, ""):
            principal = payload.get("principal_before" if phase_name == "before" else "principal_after")
        if principal in (None, ""):
            principal = payload.get("principal_open_before" if phase_name == "before" else "open_principal_after") or 0

        correction = normalized.get("financial_correction")
        if correction in (None, ""):
            correction = normalized.get("adjustments_open")
        if correction in (None, ""):
            correction = payload.get("adjustments_open_before" if phase_name == "before" else "adjustments_open_after") or 0

        discount = normalized.get("discount")
        if discount in (None, ""):
            discount = normalized.get("discounts_open")
        if discount in (None, ""):
            discount = payload.get("discounts_open_before" if phase_name == "before" else "discounts_open_after") or 0

        gross_amount = normalized.get("gross_amount")
        if gross_amount in (None, ""):
            gross_amount = normalized.get("total_open")
        if gross_amount in (None, ""):
            gross_amount = payload.get("total_due_before" if phase_name == "before" else "total_due_after")
        if gross_amount in (None, ""):
            gross_amount = float(principal or 0) + float(correction or 0) - float(discount or 0)

        normalized["principal"] = principal
        normalized["financial_correction"] = correction
        normalized["discount"] = discount
        normalized["gross_amount"] = gross_amount
        return normalized

    @staticmethod
    def _serialize_log(log: FinancialTitleCalculationLog) -> Dict[str, Any]:
        payload = log.to_dict() if hasattr(log, "to_dict") else dict(log.__dict__)
        snapshot = dict(payload.get("snapshot_json") or {})
        metadata = dict(payload.get("metadata_json") or {})
        before = FinancialTitleCalculationService._normalize_memory_phase(
            phase_name="before",
            block=dict(snapshot.get("before") or metadata.get("before") or {}),
            payload=payload,
        )
        current = FinancialTitleCalculationService._normalize_memory_phase(
            phase_name="current",
            block=dict(snapshot.get("current") or metadata.get("current") or {}),
            payload=payload,
        )
        after = FinancialTitleCalculationService._normalize_memory_phase(
            phase_name="after",
            block=dict(snapshot.get("after") or metadata.get("after") or {}),
            payload=payload,
        )
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
        payload["tenant_scope"] = dict(metadata.get("tenant_scope") or {})
        return payload

    @staticmethod
    def _is_hidden_from_memory(payload: Dict[str, Any]) -> bool:
        metadata = dict(payload.get("metadata_json") or {})
        return bool(metadata.get("hidden_from_memory"))

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

        serialized_logs = [
            FinancialTitleCalculationService._serialize_log(log)
            for log in logs
        ]
        visible_logs = [
            payload
            for payload in serialized_logs
            if not FinancialTitleCalculationService._is_hidden_from_memory(payload)
        ]

        return {
            "schedule": title.to_dict() if hasattr(title, "to_dict") else {
                "id": getattr(title, "id", schedule_id),
                "company_id": getattr(title, "company_id", company_id),
                "schedule_code": getattr(title, "schedule_code", None),
            },
            "logs": visible_logs,
            "count": len(visible_logs),
            "limit": normalized_limit,
        }, None
