from __future__ import annotations

from datetime import timedelta
from typing import Dict, Optional, Sequence, Tuple

from models.financial import FinancialImportBatch, FinancialReconciliationMatch
from services.financial_classification_dashboard_service import FinancialClassificationDashboardService
from services.financial_dashboard_analytics import FinancialDashboardAnalytics
from services.financial_service import FinancialService


class FinancialExecutiveDashboardService:
    """Orquestra o cockpit executivo do financeiro preservando a lógica madura do módulo."""

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

        start_date, end_date, error = FinancialDashboardAnalytics.resolve_period(period_start, period_end)
        if error:
            return None, error

        entries = FinancialDashboardAnalytics.list_entries(company_id)
        settlements = FinancialDashboardAnalytics.list_settlements(company_id)
        cash_flow_panel = FinancialDashboardAnalytics.build_cash_flow_panel(
            company_id=company_id,
            entries=entries,
            settlements=settlements,
            period_start=start_date,
            period_end=end_date,
        )
        dre_matrix = FinancialDashboardAnalytics.build_dre_matrix(
            company_id=company_id,
            entries=entries,
            settlements=settlements,
            period_start=start_date,
            period_end=end_date,
        )

        classification, _ = FinancialClassificationDashboardService.get_dashboard(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
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
        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "scoreboard": FinancialDashboardAnalytics.build_scoreboard(
                start_date,
                end_date,
                cash_flow_panel,
                dre_matrix,
                import_batches=processed_batches,
                confirmed_matches=confirmed_matches,
            ),
            "cash_flow_panel": cash_flow_panel,
            "dre_matrix": dre_matrix,
            "quick_actions": FinancialDashboardAnalytics.build_quick_actions(),
            "classification": classification,
        }, None
