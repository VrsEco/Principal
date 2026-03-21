from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialClosing, FinancialEntry, FinancialImportRow, FinancialSettlement
from schemas.financial import FinancialClosingInput
from services.financial_service import FinancialService


class FinancialClosingService:
    """Fechamento e conferência operacional do financeiro por período."""

    @staticmethod
    def _period_filters(model, period_start, period_end):
        if hasattr(model, "competence_date"):
            return model.competence_date >= period_start, model.competence_date <= period_end
        if hasattr(model, "settlement_date"):
            return model.settlement_date >= period_start, model.settlement_date <= period_end
        if hasattr(model, "occurred_on"):
            return model.occurred_on >= period_start, model.occurred_on <= period_end
        raise AttributeError("Modelo sem campo de período suportado.")

    @staticmethod
    def preview_closing(
        *,
        company_id: int,
        period_start,
        period_end,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        if period_start > period_end:
            return None, "Período inválido para fechamento."

        entry_filters = FinancialClosingService._period_filters(FinancialEntry, period_start, period_end)
        settlement_filters = FinancialClosingService._period_filters(FinancialSettlement, period_start, period_end)
        row_filters = FinancialClosingService._period_filters(FinancialImportRow, period_start, period_end)

        entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            *entry_filters,
        )
        settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            *settlement_filters,
        )
        import_rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
            *row_filters,
        )

        total_entries = entries.count()
        total_settlements = settlements.count()
        pending_review_entries = entries.filter(FinancialEntry.review_status.in_(["pending_review", "suggested_by_ai"])).count()
        open_entries = entries.filter(FinancialEntry.status.in_(["draft", "pending_review", "scheduled", "posted", "partially_settled"])).count()
        settled_entries = entries.filter(FinancialEntry.status == "settled").count()
        imported_not_matched = import_rows.filter(
            FinancialImportRow.processing_status.in_(["validated", "imported"]),
            FinancialImportRow.matched_entry_id.is_(None),
        ).count()
        rejected_import_rows = import_rows.filter(FinancialImportRow.processing_status == "rejected").count()

        total_original = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialEntry.original_amount), 0))
            .filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
                *entry_filters,
            )
            .scalar()
        ) or Decimal("0")
        total_settled_amount = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.net_amount), 0))
            .filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                *settlement_filters,
            )
            .scalar()
        ) or Decimal("0")

        checklist = [
            {
                "code": "pending_review_entries",
                "label": "Lançamentos pendentes de revisão",
                "count": pending_review_entries,
                "status": "ok" if pending_review_entries == 0 else "attention",
            },
            {
                "code": "import_rows_not_matched",
                "label": "Linhas importadas sem match",
                "count": imported_not_matched,
                "status": "ok" if imported_not_matched == 0 else "attention",
            },
            {
                "code": "rejected_import_rows",
                "label": "Linhas rejeitadas na importação",
                "count": rejected_import_rows,
                "status": "ok" if rejected_import_rows == 0 else "attention",
            },
            {
                "code": "open_entries",
                "label": "Lançamentos ainda em aberto",
                "count": open_entries,
                "status": "ok" if open_entries == 0 else "attention",
            },
        ]

        summary = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_entries": total_entries,
            "settled_entries": settled_entries,
            "open_entries": open_entries,
            "pending_review_entries": pending_review_entries,
            "total_settlements": total_settlements,
            "imported_not_matched": imported_not_matched,
            "rejected_import_rows": rejected_import_rows,
            "total_original_amount": float(total_original),
            "total_settled_amount": float(total_settled_amount),
            "checklist": checklist,
            "can_close": all(item["count"] == 0 for item in checklist),
        }
        return summary, None

    @staticmethod
    def create_closing(
        *,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            data = FinancialClosingInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para fechamento financeiro: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        preview, error = FinancialClosingService.preview_closing(
            company_id=data.company_id,
            period_start=data.period_start,
            period_end=data.period_end,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        existing = FinancialClosing.query.filter(
            FinancialClosing.company_id == data.company_id,
            FinancialClosing.period_start == data.period_start,
            FinancialClosing.period_end == data.period_end,
            FinancialClosing.deleted_at.is_(None),
        ).first()
        if existing:
            return None, "Já existe fechamento financeiro para este período."

        try:
            closing = FinancialClosing(
                **data.model_dump(exclude={"summary_json"}),
                summary_json=preview,
                closed_at=datetime.utcnow() if data.status == "closed" else None,
            )
            db.session.add(closing)
            db.session.commit()
            return closing.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao registrar fechamento financeiro: {str(exc)}"

    @staticmethod
    def list_closings(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = FinancialClosing.query.filter(
            FinancialClosing.company_id == company_id,
            FinancialClosing.deleted_at.is_(None),
        ).order_by(FinancialClosing.period_end.desc(), FinancialClosing.id.desc()).all()
        return [item.to_dict() for item in items], None
