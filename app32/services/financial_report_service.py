from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialChartAccount, FinancialCostCenter, FinancialEntry, FinancialSettlement
from services.financial_service import FinancialService


class FinancialReportService:
    """Relatórios automáticos do financeiro com foco gerencial e operacional."""

    REPORT_TYPES = ("cash_flow", "dre", "settlements", "open_items")

    @staticmethod
    def _parse_period(period_start: str, period_end: str):
        return (
            datetime.strptime(period_start, "%Y-%m-%d").date(),
            datetime.strptime(period_end, "%Y-%m-%d").date(),
        )

    @staticmethod
    def _entry_filters(company_id: int, period_start, period_end):
        return (
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.competence_date >= period_start,
            FinancialEntry.competence_date <= period_end,
        )

    @staticmethod
    def _settlement_filters(company_id: int, period_start, period_end):
        return (
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date >= period_start,
            FinancialSettlement.settlement_date <= period_end,
        )

    @staticmethod
    def _chart_account_name(account_id: Optional[int], company_id: int) -> str:
        if not account_id:
            return "Sem conta"
        item = FinancialChartAccount.query.filter(
            FinancialChartAccount.id == account_id,
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).first()
        return item.name if item else f"Conta #{account_id}"

    @staticmethod
    def _cost_center_name(center_id: Optional[int], company_id: int) -> str:
        if not center_id:
            return "Sem centro"
        item = FinancialCostCenter.query.filter(
            FinancialCostCenter.id == center_id,
            FinancialCostCenter.company_id == company_id,
            FinancialCostCenter.deleted_at.is_(None),
        ).first()
        return item.name if item else f"Centro #{center_id}"

    @staticmethod
    def _build_cash_flow(company_id: int, period_start, period_end) -> Dict:
        settlements = FinancialSettlement.query.filter(
            *FinancialReportService._settlement_filters(company_id, period_start, period_end)
        ).order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc()).all()

        by_day: Dict[str, Dict[str, Decimal]] = {}
        total_in = Decimal("0")
        total_out = Decimal("0")
        for item in settlements:
            date_key = item.settlement_date.isoformat()
            slot = by_day.setdefault(date_key, {"credit": Decimal("0"), "debit": Decimal("0")})
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == item.financial_entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            nature = (entry.movement_nature if entry else "debit") or "debit"
            amount = Decimal(item.net_amount or 0)
            slot[nature] += amount
            if nature == "credit":
                total_in += amount
            else:
                total_out += amount

        return {
            "report_type": "cash_flow",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "totals": {
                "inflow": float(total_in),
                "outflow": float(total_out),
                "net": float(total_in - total_out),
            },
            "items": [
                {
                    "date": date_key,
                    "inflow": float(values["credit"]),
                    "outflow": float(values["debit"]),
                    "net": float(values["credit"] - values["debit"]),
                }
                for date_key, values in sorted(by_day.items())
            ],
        }

    @staticmethod
    def _build_dre(company_id: int, period_start, period_end) -> Dict:
        entries = FinancialEntry.query.filter(
            *FinancialReportService._entry_filters(company_id, period_start, period_end)
        ).all()

        groups: Dict[str, Decimal] = {}
        for entry in entries:
            chart_name = FinancialReportService._chart_account_name(entry.chart_account_id, company_id)
            groups.setdefault(chart_name, Decimal("0"))
            amount = Decimal(entry.original_amount or 0)
            if entry.movement_nature == "credit":
                groups[chart_name] += amount
            else:
                groups[chart_name] -= amount

        total = sum(groups.values(), Decimal("0"))
        return {
            "report_type": "dre",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "totals": {
                "result": float(total),
            },
            "items": [
                {"group": name, "amount": float(amount)}
                for name, amount in sorted(groups.items(), key=lambda item: item[0])
            ],
        }

    @staticmethod
    def _build_settlements(company_id: int, period_start, period_end) -> Dict:
        settlements = FinancialSettlement.query.filter(
            *FinancialReportService._settlement_filters(company_id, period_start, period_end)
        ).all()

        items = []
        total_principal = Decimal("0")
        total_interest = Decimal("0")
        total_penalty = Decimal("0")
        for item in settlements:
            total_principal += Decimal(item.principal_amount or 0)
            total_interest += Decimal(item.interest_amount or 0)
            total_penalty += Decimal(item.penalty_amount or 0)
            items.append(item.to_dict())

        return {
            "report_type": "settlements",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "totals": {
                "principal": float(total_principal),
                "interest": float(total_interest),
                "penalty": float(total_penalty),
                "net": float(total_principal + total_interest + total_penalty),
            },
            "items": items,
        }

    @staticmethod
    def _build_open_items(company_id: int, period_start, period_end) -> Dict:
        entries = FinancialEntry.query.filter(
            *FinancialReportService._entry_filters(company_id, period_start, period_end),
            FinancialEntry.status.in_(["draft", "pending_review", "scheduled", "posted", "partially_settled"]),
        ).order_by(FinancialEntry.due_date.asc().nullslast(), FinancialEntry.id.asc()).all()

        items = []
        total_open = Decimal("0")
        by_center: Dict[str, Decimal] = {}
        for entry in entries:
            total_open += Decimal(entry.original_amount or 0)
            center_name = FinancialReportService._cost_center_name(entry.cost_center_id, company_id)
            by_center.setdefault(center_name, Decimal("0"))
            by_center[center_name] += Decimal(entry.original_amount or 0)
            items.append(entry.to_dict())

        return {
            "report_type": "open_items",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "totals": {
                "open_amount": float(total_open),
                "open_count": len(items),
            },
            "by_cost_center": [
                {"cost_center": name, "amount": float(amount)}
                for name, amount in sorted(by_center.items(), key=lambda item: item[0])
            ],
            "items": items,
        }

    @staticmethod
    def list_report_types(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        return [
            {"code": "cash_flow", "label": "Fluxo de Caixa"},
            {"code": "dre", "label": "DRE Gerencial"},
            {"code": "settlements", "label": "Liquidações"},
            {"code": "open_items", "label": "Itens em Aberto"},
        ], None

    @staticmethod
    def generate_report(
        *,
        company_id: int,
        report_type: str,
        period_start: str,
        period_end: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if report_type not in FinancialReportService.REPORT_TYPES:
            return None, "Tipo de relatório financeiro inválido."

        try:
            start_date, end_date = FinancialReportService._parse_period(period_start, period_end)
        except ValueError:
            return None, "Datas inválidas. Use YYYY-MM-DD."

        if start_date > end_date:
            return None, "Período inválido para relatório."

        if report_type == "cash_flow":
            return FinancialReportService._build_cash_flow(company_id, start_date, end_date), None
        if report_type == "dre":
            return FinancialReportService._build_dre(company_id, start_date, end_date), None
        if report_type == "settlements":
            return FinancialReportService._build_settlements(company_id, start_date, end_date), None
        return FinancialReportService._build_open_items(company_id, start_date, end_date), None
