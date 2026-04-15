from __future__ import annotations

from typing import Any, Optional, Sequence

from services.financial_executive_dashboard_service import FinancialExecutiveDashboardService


class FinancialResultsQueryService:
    """Vertical piloto read-only de resultado financeiro para a Sapiens Factory."""

    @classmethod
    def get_company_financial_results(cls, *, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None, period_start: Optional[str] = None, period_end: Optional[str] = None) -> tuple[dict[str, Any] | None, str | None]:
        dashboard, error = FinancialExecutiveDashboardService.get_dashboard(
            company_id=company_id,
            period_start=period_start,
            period_end=period_end,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        dashboard = dashboard or {}
        score_items = list((dashboard.get("scoreboard") or {}).get("items") or [])
        score_by_key = {str(item.get("key") or ""): item for item in score_items}
        summary = {
            "period_start": dashboard.get("period_start"),
            "period_end": dashboard.get("period_end"),
            "cash_inflow": score_by_key.get("cash_inflow"),
            "cash_outflow": score_by_key.get("cash_outflow"),
            "cash_balance": score_by_key.get("cash_balance"),
            "dre_neto": score_by_key.get("dre_liquido"),
        }
        return {
            "summary": summary,
            "scoreboard": score_items,
            "cash_flow_panel": dashboard.get("cash_flow_panel") or {},
            "dre_matrix": dashboard.get("dre_matrix") or {},
        }, None
