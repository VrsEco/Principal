from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from models.financial import FinancialBankAccount, FinancialChartAccount, FinancialEntry, FinancialSettlement
from models.financial_budget import FinancialBudgetAmount, FinancialBudgetLine, FinancialBudgetVersion


class FinancialDashboardAnalytics:
    _OPEN_ENTRY_STATUSES = {"draft", "pending_review", "scheduled", "posted", "partially_settled"}
    _SETTLEMENT_STATUS_EXCLUDED = {"cancelled"}
    _OVERDRAFT_LIMIT_KEYS = (
        "overdraft_limit",
        "cheque_especial_limit",
        "special_limit",
        "credit_limit",
        "limite_cheque_especial",
        "limite",
    )

    @staticmethod
    def resolve_period(
        period_start: Optional[str],
        period_end: Optional[str],
    ) -> Tuple[Optional[date], Optional[date], Optional[str]]:
        if period_start and period_end:
            try:
                start_date = datetime.strptime(period_start, "%Y-%m-%d").date()
                end_date = datetime.strptime(period_end, "%Y-%m-%d").date()
            except ValueError:
                return None, None, "Datas inválidas. Use YYYY-MM-DD."
        else:
            end_date = date.today()
            start_date = end_date.replace(day=1)

        if start_date > end_date:
            return None, None, "Período inválido para dashboard."
        return start_date, end_date, None

    @staticmethod
    def list_entries(company_id: int) -> List[FinancialEntry]:
        return (
            FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            )
            .order_by(FinancialEntry.competence_date.asc(), FinancialEntry.id.asc())
            .all()
        )

    @staticmethod
    def list_settlements(company_id: int) -> List[FinancialSettlement]:
        return (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status.notin_(FinancialDashboardAnalytics._SETTLEMENT_STATUS_EXCLUDED),
            )
            .order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc())
            .all()
        )

    @staticmethod
    def build_cash_flow_panel(
        *,
        company_id: int,
        entries: Iterable[FinancialEntry],
        settlements: Iterable[FinancialSettlement],
        period_start: date,
        period_end: date,
    ) -> Dict:
        entries = list(entries)
        settlements = list(settlements)
        entries_by_id = {entry.id: entry for entry in entries}
        current_date = min(date.today(), period_end) if period_start <= date.today() else period_end
        current_balance = FinancialDashboardAnalytics.calculate_current_balance(
            settlements=settlements,
            entries_by_id=entries_by_id,
            as_of_date=current_date,
        )
        overdraft_limit = FinancialDashboardAnalytics.calculate_overdraft_limit(company_id)

        current_receivables = FinancialDashboardAnalytics.sum_due_entries(entries, period_start, period_end, "credit")
        current_payables = FinancialDashboardAnalytics.sum_due_entries(entries, period_start, period_end, "debit")
        overdue_receivables = FinancialDashboardAnalytics.sum_overdue_entries(entries, "credit")
        overdue_payables = FinancialDashboardAnalytics.sum_overdue_entries(entries, "debit")

        current_final_without_limits = current_balance + current_receivables["amount"] - current_payables["amount"]
        current_final_with_limits = current_final_without_limits + overdraft_limit

        next_start, next_end = FinancialDashboardAnalytics.next_period(period_start, period_end)
        next_receivables = FinancialDashboardAnalytics.sum_due_entries(entries, next_start, next_end, "credit")
        next_payables = FinancialDashboardAnalytics.sum_due_entries(entries, next_start, next_end, "debit")
        next_initial_balance = current_final_without_limits
        next_final_without_limits = next_initial_balance + next_receivables["amount"] - next_payables["amount"]
        next_final_with_limits = next_final_without_limits + overdraft_limit
        liquidated = FinancialDashboardAnalytics.sum_liquidations(
            settlements=settlements,
            entries_by_id=entries_by_id,
            period_start=period_start,
            period_end=period_end,
        )

        return {
            "overdue": {
                "receivable": float(overdue_receivables["amount"]),
                "receivable_count": overdue_receivables["count"],
                "payable": float(overdue_payables["amount"]),
                "payable_count": overdue_payables["count"],
            },
            "current": {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "balance": float(current_balance),
                "overdraft_limit": float(overdraft_limit),
                "receivables": float(current_receivables["amount"]),
                "receivables_count": current_receivables["count"],
                "payables": float(current_payables["amount"]),
                "payables_count": current_payables["count"],
                "final_without_limits": float(current_final_without_limits),
                "final_with_limits": float(current_final_with_limits),
                "liquidated_inflow": float(liquidated["credit"]),
                "liquidated_outflow": float(liquidated["debit"]),
            },
            "next_period": {
                "period_start": next_start.isoformat(),
                "period_end": next_end.isoformat(),
                "initial_balance": float(next_initial_balance),
                "overdraft_limit": float(overdraft_limit),
                "receivables": float(next_receivables["amount"]),
                "receivables_count": next_receivables["count"],
                "payables": float(next_payables["amount"]),
                "payables_count": next_payables["count"],
                "final_without_limits": float(next_final_without_limits),
                "final_with_limits": float(next_final_with_limits),
            },
        }

    @staticmethod
    def build_dre_matrix(
        *,
        company_id: int,
        entries: Iterable[FinancialEntry],
        settlements: Iterable[FinancialSettlement],
        period_start: date,
        period_end: date,
    ) -> Dict:
        entries = list(entries)
        rows: Dict[str, Dict[str, Decimal]] = {}
        totals = {key: Decimal("0") for key in ("budget", "competence", "due", "liquidation")}
        budget_rows = FinancialDashboardAnalytics.load_budget_totals(company_id=company_id, period_start=period_start, period_end=period_end)

        def ensure_row(group_name: str) -> Dict[str, Decimal]:
            return rows.setdefault(group_name, {key: Decimal("0") for key in totals})

        for group_name, amount in budget_rows.items():
            row = ensure_row(group_name)
            row["budget"] += amount
            totals["budget"] += amount

        for entry in entries:
            if FinancialDashboardAnalytics.is_transfer_entry(entry):
                continue

            row_name = FinancialDashboardAnalytics.chart_account_name(company_id, entry.chart_account_id)
            row = ensure_row(row_name)
            sign = FinancialDashboardAnalytics.entry_sign(entry)

            if FinancialDashboardAnalytics.affects_competence(entry) and period_start <= entry.competence_date <= period_end:
                amount = FinancialDashboardAnalytics.entry_amount(entry) * sign
                row["competence"] += amount
                totals["competence"] += amount

            if FinancialDashboardAnalytics.affects_due(entry) and entry.due_date and period_start <= entry.due_date <= period_end:
                amount = FinancialDashboardAnalytics.entry_amount(entry) * sign
                row["due"] += amount
                totals["due"] += amount

        entries_by_id = {entry.id: entry for entry in entries}
        for settlement in settlements:
            if not (period_start <= settlement.settlement_date <= period_end):
                continue
            entry = entries_by_id.get(settlement.financial_entry_id)
            if not entry or not FinancialDashboardAnalytics.affects_liquidation(entry):
                continue
            row_name = FinancialDashboardAnalytics.chart_account_name(company_id, entry.chart_account_id)
            row = ensure_row(row_name)
            amount = FinancialDashboardAnalytics.settlement_amount(settlement) * FinancialDashboardAnalytics.entry_sign(entry)
            row["liquidation"] += amount
            totals["liquidation"] += amount

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "rows": [
                {
                    "group": group_name,
                    "budget": float(row["budget"]),
                    "competence": float(row["competence"]),
                    "due": float(row["due"]),
                    "liquidation": float(row["liquidation"]),
                }
                for group_name, row in sorted(rows.items())
            ],
            "totals": {key: float(value) for key, value in totals.items()},
        }

    @staticmethod
    def build_scoreboard(period_start: date, period_end: date, cash_flow_panel: Dict, dre_matrix: Dict, *, import_batches: int, confirmed_matches: int) -> Dict:
        current = cash_flow_panel["current"]
        overdue = cash_flow_panel["overdue"]
        totals = dre_matrix["totals"]
        return {
            "period_label": FinancialDashboardAnalytics.format_period_label(period_start, period_end),
            "receivables_overdue": overdue["receivable"],
            "payables_overdue": overdue["payable"],
            "current_balance": current["balance"],
            "projected_final_without_limits": current["final_without_limits"],
            "projected_final_with_limits": current["final_with_limits"],
            "dre_budget_result": totals["budget"],
            "dre_competence_result": totals["competence"],
            "dre_due_result": totals["due"],
            "dre_liquidation_result": totals["liquidation"],
            "import_batches": import_batches,
            "confirmed_matches": confirmed_matches,
        }

    @staticmethod
    def build_quick_actions() -> List[Dict[str, str]]:
        return [
            {"label": "Lançamentos", "href": "/financial/entries"},
            {"label": "Lançamento Direto", "href": "/financial/entries/direct"},
            {"label": "Agendamentos", "href": "/financial/schedules"},
            {"label": "Borderôs", "href": "/financial/borderos"},
            {"label": "Relatório de Agendamento", "href": "/financial/reports/agendamento"},
            {"label": "Extrato Bancário", "href": "/financial/reports/extrato-bancario"},
            {"label": "DRE", "href": "/financial/reports/demonstrativo-resultados"},
            {"label": "Fluxo de Caixa", "href": "/financial/reports/fluxo-caixa"},
            {"label": "Orçamento Matricial", "href": "/financial/budget"},
            {"label": "Cadastros", "href": "/financial/catalogs"},
        ]

    @staticmethod
    def sum_due_entries(entries: Iterable[FinancialEntry], period_start: date, period_end: date, movement_nature: str) -> Dict:
        total = Decimal("0")
        count = 0
        for entry in entries:
            if not FinancialDashboardAnalytics.affects_due(entry):
                continue
            if entry.movement_nature != movement_nature or not entry.due_date:
                continue
            if period_start <= entry.due_date <= period_end:
                total += FinancialDashboardAnalytics.entry_amount(entry)
                count += 1
        return {"amount": total, "count": count}

    @staticmethod
    def sum_overdue_entries(entries: Iterable[FinancialEntry], movement_nature: str) -> Dict:
        today = date.today()
        total = Decimal("0")
        count = 0
        for entry in entries:
            if not FinancialDashboardAnalytics.affects_due(entry):
                continue
            if entry.movement_nature != movement_nature or not entry.due_date:
                continue
            if entry.due_date >= today or entry.status not in FinancialDashboardAnalytics._OPEN_ENTRY_STATUSES:
                continue
            total += FinancialDashboardAnalytics.entry_amount(entry)
            count += 1
        return {"amount": total, "count": count}

    @staticmethod
    def sum_liquidations(
        *,
        settlements: Iterable[FinancialSettlement],
        entries_by_id: Dict[int, FinancialEntry],
        period_start: date,
        period_end: date,
    ) -> Dict[str, Decimal]:
        totals = {"credit": Decimal("0"), "debit": Decimal("0")}
        for settlement in settlements:
            if not (period_start <= settlement.settlement_date <= period_end):
                continue
            entry = entries_by_id.get(settlement.financial_entry_id)
            if not entry or not FinancialDashboardAnalytics.affects_liquidation(entry):
                continue
            totals[entry.movement_nature] += FinancialDashboardAnalytics.settlement_amount(settlement)
        return totals

    @staticmethod
    def calculate_current_balance(
        *,
        settlements: Iterable[FinancialSettlement],
        entries_by_id: Dict[int, FinancialEntry],
        as_of_date: date,
    ) -> Decimal:
        total = Decimal("0")
        for settlement in settlements:
            if settlement.settlement_date > as_of_date:
                continue
            entry = entries_by_id.get(settlement.financial_entry_id)
            if not entry or FinancialDashboardAnalytics.is_transfer_entry(entry):
                continue
            amount = FinancialDashboardAnalytics.settlement_amount(settlement)
            total += amount if entry.movement_nature == "credit" else -amount
        return total

    @staticmethod
    def calculate_overdraft_limit(company_id: int) -> Decimal:
        total = Decimal("0")
        accounts = FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == company_id,
            FinancialBankAccount.deleted_at.is_(None),
            FinancialBankAccount.is_active.is_(True),
        ).all()
        for account in accounts:
            total += FinancialDashboardAnalytics.extract_decimal_from_mapping(
                account.metadata_json or {},
                FinancialDashboardAnalytics._OVERDRAFT_LIMIT_KEYS,
            )
        return total

    @staticmethod
    def next_period(period_start: date, period_end: date) -> Tuple[date, date]:
        next_start = period_end + timedelta(days=1)
        full_month = period_start.day == 1 and period_end.day == monthrange(period_end.year, period_end.month)[1]
        if full_month:
            next_end = next_start.replace(day=monthrange(next_start.year, next_start.month)[1])
            return next_start, next_end
        return next_start, next_start + timedelta(days=(period_end - period_start).days)

    @staticmethod
    def chart_account_name(company_id: int, chart_account_id: Optional[int]) -> str:
        if not chart_account_id:
            return "Sem conta contábil"
        item = FinancialChartAccount.query.filter(
            FinancialChartAccount.id == chart_account_id,
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).first()
        return item.name if item else f"Conta #{chart_account_id}"

    @staticmethod
    def format_period_label(period_start: date, period_end: date) -> str:
        return f"{period_start.strftime('%d/%m/%Y')} até {period_end.strftime('%d/%m/%Y')}"

    @staticmethod
    def entry_amount(entry: FinancialEntry) -> Decimal:
        return Decimal(entry.original_amount or 0)

    @staticmethod
    def settlement_amount(settlement: FinancialSettlement) -> Decimal:
        return Decimal(settlement.net_amount or 0)

    @staticmethod
    def entry_sign(entry: FinancialEntry) -> Decimal:
        return Decimal("1") if entry.movement_nature == "credit" else Decimal("-1")

    @staticmethod
    def is_transfer_entry(entry: FinancialEntry) -> bool:
        metadata = entry.metadata_json or {}
        return bool(metadata.get("is_transfer")) or entry.entry_type == "transfer"

    @staticmethod
    def is_non_financial_entry(entry: FinancialEntry) -> bool:
        metadata = entry.metadata_json or {}
        return bool(metadata.get("non_financial")) or bool(metadata.get("competence_only")) or entry.entry_type == "adjustment"

    @staticmethod
    def affects_competence(entry: FinancialEntry) -> bool:
        return not FinancialDashboardAnalytics.is_transfer_entry(entry)

    @staticmethod
    def affects_due(entry: FinancialEntry) -> bool:
        return not FinancialDashboardAnalytics.is_transfer_entry(entry) and not FinancialDashboardAnalytics.is_non_financial_entry(entry)

    @staticmethod
    def affects_liquidation(entry: FinancialEntry) -> bool:
        return not FinancialDashboardAnalytics.is_transfer_entry(entry) and not FinancialDashboardAnalytics.is_non_financial_entry(entry)

    @staticmethod
    def extract_decimal_from_mapping(payload: Dict, keys: Sequence[str]) -> Decimal:
        for key in keys:
            if key not in payload:
                continue
            try:
                value = payload.get(key)
                if value in (None, "", False):
                    continue
                return Decimal(str(value))
            except Exception:
                continue
        return Decimal("0")

    @staticmethod
    def load_budget_totals(*, company_id: int, period_start: date, period_end: date) -> Dict[str, Decimal]:
        versions = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
            FinancialBudgetVersion.status == "active",
            FinancialBudgetVersion.period_start <= period_end,
            FinancialBudgetVersion.period_end >= period_start,
        ).all()
        if not versions:
            return {}

        totals: Dict[str, Decimal] = {}
        version_ids = [item.id for item in versions]
        rows = (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.deleted_at.is_(None),
                FinancialBudgetLine.budget_version_id.in_(version_ids),
                FinancialBudgetLine.is_active.is_(True),
            )
            .order_by(FinancialBudgetLine.id.asc())
            .all()
        )
        for row in rows:
            row_name = FinancialDashboardAnalytics.chart_account_name(company_id, row.chart_account_id)
            sign = Decimal("1") if row.movement_nature == "credit" else Decimal("-1")
            line_total = Decimal(str(row.planned_amount or 0))
            if line_total > 0:
                totals.setdefault(row_name, Decimal("0"))
                totals[row_name] += line_total * sign
                continue
            for amount in row.amounts.filter(FinancialBudgetAmount.deleted_at.is_(None)).all():
                if period_start <= amount.period_month <= period_end:
                    totals.setdefault(row_name, Decimal("0"))
                    totals[row_name] += Decimal(amount.budget_amount or 0) * sign
        return totals
