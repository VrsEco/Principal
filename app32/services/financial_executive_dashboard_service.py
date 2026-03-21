from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialClosing,
    FinancialEntry,
    FinancialImportBatch,
    FinancialReconciliationMatch,
    FinancialSettlement,
)
from services.financial_classification_dashboard_service import FinancialClassificationDashboardService
from services.financial_closing_service import FinancialClosingService
from services.financial_report_service import FinancialReportService
from services.financial_service import FinancialService


class FinancialExecutiveDashboardService:
    """Dashboard executivo integrado do APP Financeiro."""

    @staticmethod
    def get_dashboard(
        *,
        company_id: int,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if period_start and period_end:
            try:
                start_date, end_date = FinancialReportService._parse_period(period_start, period_end)
            except ValueError:
                return None, "Datas inválidas. Use YYYY-MM-DD."
        else:
            end_date = date.today()
            start_date = end_date.replace(day=1)

        if start_date > end_date:
            return None, "Período inválido para dashboard."

        cash_flow, error = FinancialReportService.generate_report(
            company_id=company_id,
            report_type="cash_flow",
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        dre, error = FinancialReportService.generate_report(
            company_id=company_id,
            report_type="dre",
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        open_items, error = FinancialReportService.generate_report(
            company_id=company_id,
            report_type="open_items",
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        classification, error = FinancialClassificationDashboardService.get_dashboard(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        closing_preview, error = FinancialClosingService.preview_closing(
            company_id=company_id,
            period_start=start_date,
            period_end=end_date,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        total_entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.competence_date >= start_date,
            FinancialEntry.competence_date <= end_date,
        ).count()
        total_settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date >= start_date,
            FinancialSettlement.settlement_date <= end_date,
        ).count()
        processed_batches = FinancialImportBatch.query.filter(
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
            FinancialImportBatch.imported_at >= start_date,
            FinancialImportBatch.imported_at < (end_date + timedelta(days=1)),
        ).count()
        confirmed_matches = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.deleted_at.is_(None),
            FinancialReconciliationMatch.match_status == "confirmed",
            FinancialReconciliationMatch.created_at >= start_date,
            FinancialReconciliationMatch.created_at < (end_date + timedelta(days=1)),
        ).count()

        last_closing = FinancialClosing.query.filter(
            FinancialClosing.company_id == company_id,
            FinancialClosing.deleted_at.is_(None),
        ).order_by(FinancialClosing.period_end.desc(), FinancialClosing.id.desc()).first()

        scoreboard = {
            "entries": total_entries,
            "settlements": total_settlements,
            "batches": processed_batches,
            "confirmed_matches": confirmed_matches,
            "net_cash": cash_flow["totals"]["net"],
            "dre_result": dre["totals"]["result"],
            "open_amount": open_items["totals"]["open_amount"],
            "open_count": open_items["totals"]["open_count"],
            "classification_coverage": classification["summary"]["coverage_rate"],
            "classification_applied_rate": classification["summary"]["applied_rate"],
            "can_close": closing_preview["can_close"],
        }

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "scoreboard": scoreboard,
            "cash_flow": cash_flow,
            "dre": dre,
            "open_items": open_items,
            "classification": classification,
            "closing_preview": closing_preview,
            "last_closing": last_closing.to_dict() if last_closing else None,
        }, None
