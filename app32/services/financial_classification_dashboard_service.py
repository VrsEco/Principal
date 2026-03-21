from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialClassificationMemory,
    FinancialClassificationSuggestion,
    FinancialImportRow,
    FinancialReconciliationMatch,
)
from services.financial_classification_hybrid_service import FinancialClassificationHybridService
from services.financial_service import FinancialService


class FinancialClassificationDashboardService:
    """Métricas executivas da classificação híbrida e da governança de importação."""

    @staticmethod
    def get_dashboard(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        base_rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        )
        base_suggestions = FinancialClassificationSuggestion.query.filter(
            FinancialClassificationSuggestion.company_id == company_id,
            FinancialClassificationSuggestion.deleted_at.is_(None),
        )
        base_memories = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.deleted_at.is_(None),
        )
        base_matches = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.deleted_at.is_(None),
        )

        total_rows = base_rows.count()
        validated_rows = base_rows.filter(FinancialImportRow.processing_status == "validated").count()
        imported_rows = base_rows.filter(FinancialImportRow.processing_status == "imported").count()
        rejected_rows = base_rows.filter(FinancialImportRow.processing_status == "rejected").count()

        total_suggestions = base_suggestions.count()
        applied_suggestions = base_suggestions.filter(
            FinancialClassificationSuggestion.status.in_(["applied", "confirmed"])
        ).count()
        rejected_suggestions = base_suggestions.filter(
            FinancialClassificationSuggestion.status == "rejected"
        ).count()

        active_memories = base_memories.filter(FinancialClassificationMemory.is_active.is_(True)).count()
        inactive_memories = base_memories.filter(FinancialClassificationMemory.is_active.is_(False)).count()

        confirmed_matches = base_matches.filter(FinancialReconciliationMatch.match_status == "confirmed").count()
        rejected_matches = base_matches.filter(FinancialReconciliationMatch.match_status == "rejected").count()

        queue_items, queue_error = FinancialClassificationHybridService.list_pending_queue(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if queue_error:
            return None, queue_error

        pending_queue = queue_items or []
        queue_breakdown = {
            "strong_suggestion": len([item for item in pending_queue if item.get("queue_status") == "strong_suggestion"]),
            "confirm": len([item for item in pending_queue if item.get("queue_status") == "confirm"]),
            "ask_user": len([item for item in pending_queue if item.get("queue_status") == "ask_user"]),
        }

        source_layer_rows = (
            db.session.query(
                FinancialClassificationSuggestion.source_layer,
                db.func.count(FinancialClassificationSuggestion.id),
            )
            .filter(
                FinancialClassificationSuggestion.company_id == company_id,
                FinancialClassificationSuggestion.deleted_at.is_(None),
            )
            .group_by(FinancialClassificationSuggestion.source_layer)
            .all()
        )
        source_breakdown = [{"label": label or "n/a", "count": count} for label, count in source_layer_rows]

        queue_total = len(pending_queue)
        coverage_rate = round(((validated_rows + imported_rows) / total_rows) * 100, 2) if total_rows else 0.0
        applied_rate = round((applied_suggestions / total_suggestions) * 100, 2) if total_suggestions else 0.0
        ask_user_rate = round((queue_breakdown["ask_user"] / queue_total) * 100, 2) if queue_total else 0.0

        top_memories = (
            base_memories.order_by(
                FinancialClassificationMemory.times_confirmed.desc(),
                FinancialClassificationMemory.updated_at.desc(),
            )
            .limit(5)
            .all()
        )

        return {
            "summary": {
                "total_rows": total_rows,
                "validated_rows": validated_rows,
                "imported_rows": imported_rows,
                "rejected_rows": rejected_rows,
                "total_suggestions": total_suggestions,
                "applied_suggestions": applied_suggestions,
                "rejected_suggestions": rejected_suggestions,
                "active_memories": active_memories,
                "inactive_memories": inactive_memories,
                "confirmed_matches": confirmed_matches,
                "rejected_matches": rejected_matches,
                "queue_total": queue_total,
                "coverage_rate": coverage_rate,
                "applied_rate": applied_rate,
                "ask_user_rate": ask_user_rate,
            },
            "queue_breakdown": queue_breakdown,
            "source_breakdown": source_breakdown,
            "top_memories": [item.to_dict() for item in top_memories],
        }, None
