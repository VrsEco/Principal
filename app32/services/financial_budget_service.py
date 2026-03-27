from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

from models import (
    db,
    FinancialBudgetAmount,
    FinancialBudgetLine,
    FinancialBudgetVersion,
    FinancialChartAccount,
    FinancialCostCenter,
    FinancialEntry,
    FinancialSettlement,
)
from schemas.financial_budget import (
    FinancialBudgetMatrixUpsertInput,
    FinancialBudgetVersionInput,
    FinancialBudgetVersionUpdateInput,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService


class FinancialBudgetService:
    @staticmethod
    def list_versions(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetVersion.period_start.desc(), FinancialBudgetVersion.id.desc())
            .all()
        )
        return [item.to_dict() for item in items], None

    @staticmethod
    def create_version(*, payload: Dict, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        data = FinancialBudgetVersionInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        existing = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.company_id == data.company_id,
            FinancialBudgetVersion.code == data.code,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if existing:
            return None, f"Já existe versão orçamentária com código {data.code} para esta empresa."

        item = FinancialBudgetVersion(**data.model_dump())
        db.session.add(item)
        if item.status == "active":
            FinancialBudgetService._deactivate_other_versions(item.company_id, exclude_version_id=None)
        try:
            db.session.commit()
            return item.to_dict(), None
        except Exception:
            db.session.rollback()
            return None, "Não foi possível criar a versão orçamentária."

    @staticmethod
    def get_version(
        *,
        company_id: int,
        version_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == version_id,
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."
        return version.to_dict(), None

    @staticmethod
    def update_version(
        *,
        company_id: int,
        version_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == version_id,
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

        data = FinancialBudgetVersionUpdateInput.model_validate(payload)
        merged = data.model_dump(exclude_unset=True)
        period_start = merged.get("period_start", version.period_start)
        period_end = merged.get("period_end", version.period_end)
        if period_end < period_start:
            return None, "period_end deve ser maior ou igual a period_start."

        if merged.get("code") and merged["code"] != version.code:
            existing = FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.code == merged["code"],
                FinancialBudgetVersion.deleted_at.is_(None),
                FinancialBudgetVersion.id != version_id,
            ).first()
            if existing:
                return None, f"Já existe versão orçamentária com código {merged['code']} para esta empresa."

        for key, value in merged.items():
            setattr(version, key, value)
        if merged.get("approved_by_user_id") and version.status == "active" and not version.approved_at:
            version.approved_at = datetime.utcnow()
        if version.status == "active":
            FinancialBudgetService._deactivate_other_versions(company_id, exclude_version_id=version.id)
        try:
            db.session.commit()
            return version.to_dict(), None
        except Exception:
            db.session.rollback()
            return None, "Não foi possível atualizar a versão orçamentária."

    @staticmethod
    def delete_version(
        *,
        company_id: int,
        version_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == version_id,
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

        now = datetime.utcnow()
        version.deleted_at = now
        for line in version.lines.filter(FinancialBudgetLine.deleted_at.is_(None)).all():
            line.deleted_at = now
            for amount in line.amounts.filter(FinancialBudgetAmount.deleted_at.is_(None)).all():
                amount.deleted_at = now
        try:
            db.session.commit()
            return {"message": "Versão orçamentária removida com sucesso."}, None
        except Exception:
            db.session.rollback()
            return None, "Não foi possível remover a versão orçamentária."

    @staticmethod
    def get_matrix(
        *,
        company_id: int,
        version_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == version_id,
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

        lines = (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.budget_version_id == version_id,
                FinancialBudgetLine.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetLine.line_order.asc(), FinancialBudgetLine.id.asc())
            .all()
        )

        months = list(FinancialBudgetService._iter_months(version.period_start, version.period_end))
        payload_lines = []
        for line in lines:
            amount_index = {
                amount.period_month.isoformat(): amount
                for amount in line.amounts.filter(FinancialBudgetAmount.deleted_at.is_(None)).all()
            }
            actual_index = FinancialBudgetService._calculate_actuals_for_line(
                company_id=company_id,
                line=line,
                months=months,
            )
            payload_lines.append(
                {
                    **line.to_dict(),
                    "chart_account_name": FinancialBudgetService._chart_account_name(line.chart_account_id, company_id),
                    "cost_center_name": FinancialBudgetService._cost_center_name(line.cost_center_id, company_id),
                    "amounts": [
                        {
                            "period_month": month.isoformat(),
                            "budget_amount": float(amount_index.get(month.isoformat()).budget_amount or 0) if amount_index.get(month.isoformat()) else 0.0,
                            "actual_amount": float(actual_index.get(month.isoformat()) or 0),
                            "variance_amount": float((actual_index.get(month.isoformat()) or 0) - (amount_index.get(month.isoformat()).budget_amount if amount_index.get(month.isoformat()) else 0)),
                            "notes": amount_index.get(month.isoformat()).notes if amount_index.get(month.isoformat()) else None,
                        }
                        for month in months
                    ],
                }
            )

        return {
            "version": version.to_dict(),
            "months": [month.isoformat() for month in months],
            "lines": payload_lines,
        }, None

    @staticmethod
    def upsert_matrix(*, payload: Dict, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        data = FinancialBudgetMatrixUpsertInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == data.version_id,
            FinancialBudgetVersion.company_id == data.company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

        persisted_lines = []
        for row in data.lines:
            reference_error = FinancialCatalogService.validate_reference_ids(
                company_id=data.company_id,
                chart_account_id=row.chart_account_id,
                cost_center_id=row.cost_center_id,
            )
            if reference_error:
                return None, reference_error

            line = FinancialBudgetService._resolve_line(version.id, data.company_id, row.id, row.line_code)
            if not line:
                line = FinancialBudgetLine(company_id=data.company_id, budget_version_id=version.id)
                db.session.add(line)

            for key, value in row.model_dump(exclude={"amounts"}).items():
                setattr(line, key, value)
            if row.amounts:
                line.planned_amount = sum((amount_input.budget_amount for amount_input in row.amounts), Decimal("0"))
            db.session.flush()
            FinancialBudgetService._sync_amounts(line, row.amounts, version)
            persisted_lines.append(line.id)

        try:
            db.session.commit()
            result, error = FinancialBudgetService.get_matrix(
                company_id=data.company_id,
                version_id=version.id,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                return None, error
            result["updated_line_ids"] = persisted_lines
            return result, None
        except Exception:
            db.session.rollback()
            return None, "Não foi possível salvar a matriz orçamentária."

    @staticmethod
    def list_options(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        chart_accounts = (
            FinancialChartAccount.query.filter(
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
                FinancialChartAccount.is_active.is_(True),
            )
            .order_by(FinancialChartAccount.name.asc())
            .all()
        )
        cost_centers = (
            FinancialCostCenter.query.filter(
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
                FinancialCostCenter.is_active.is_(True),
            )
            .order_by(FinancialCostCenter.name.asc())
            .all()
        )

        return {
            "chart_accounts": [{"id": item.id, "name": item.name, "code": item.code} for item in chart_accounts],
            "cost_centers": [{"id": item.id, "name": item.name, "code": item.code} for item in cost_centers],
        }, None

    @staticmethod
    def _resolve_line(version_id: int, company_id: int, line_id: Optional[int], line_code: str) -> Optional[FinancialBudgetLine]:
        query = FinancialBudgetLine.query.filter(
            FinancialBudgetLine.company_id == company_id,
            FinancialBudgetLine.budget_version_id == version_id,
            FinancialBudgetLine.deleted_at.is_(None),
        )
        if line_id:
            return query.filter(FinancialBudgetLine.id == line_id).first()
        return query.filter(FinancialBudgetLine.line_code == line_code).first()

    @staticmethod
    def _sync_amounts(line: FinancialBudgetLine, amounts: List, version: FinancialBudgetVersion) -> None:
        existing = OrderedDict(
            (item.period_month.isoformat(), item)
            for item in line.amounts.filter(FinancialBudgetAmount.deleted_at.is_(None)).all()
        )
        for amount_input in amounts:
            if amount_input.period_month < version.period_start or amount_input.period_month > version.period_end:
                continue
            key = amount_input.period_month.isoformat()
            item = existing.get(key)
            if not item:
                item = FinancialBudgetAmount(
                    company_id=line.company_id,
                    budget_line_id=line.id,
                    period_month=amount_input.period_month,
                )
                db.session.add(item)
            item.budget_amount = amount_input.budget_amount
            item.notes = amount_input.notes
            item.metadata_json = amount_input.metadata_json

    @staticmethod
    def _iter_months(start_date: date, end_date: date):
        cursor = start_date.replace(day=1)
        limit = end_date.replace(day=1)
        while cursor <= limit:
            yield cursor
            year = cursor.year + (1 if cursor.month == 12 else 0)
            month = 1 if cursor.month == 12 else cursor.month + 1
            cursor = cursor.replace(year=year, month=month, day=1)

    @staticmethod
    def _chart_account_name(chart_account_id: Optional[int], company_id: int) -> Optional[str]:
        if not chart_account_id:
            return None
        item = FinancialChartAccount.query.filter(
            FinancialChartAccount.id == chart_account_id,
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).first()
        return item.name if item else None

    @staticmethod
    def _cost_center_name(cost_center_id: Optional[int], company_id: int) -> Optional[str]:
        if not cost_center_id:
            return None
        item = FinancialCostCenter.query.filter(
            FinancialCostCenter.id == cost_center_id,
            FinancialCostCenter.company_id == company_id,
            FinancialCostCenter.deleted_at.is_(None),
        ).first()
        return item.name if item else None

    @staticmethod
    def _deactivate_other_versions(company_id: int, exclude_version_id: Optional[int]) -> None:
        query = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
            FinancialBudgetVersion.status == "active",
        )
        if exclude_version_id:
            query = query.filter(FinancialBudgetVersion.id != exclude_version_id)
        for item in query.all():
            item.status = "draft"

    @staticmethod
    def _calculate_actuals_for_line(*, company_id: int, line: FinancialBudgetLine, months: List[date]) -> Dict[str, float]:
        if line.budget_view == "cash":
            return FinancialBudgetService._calculate_cash_actuals(company_id=company_id, line=line, months=months)
        return FinancialBudgetService._calculate_entry_actuals(company_id=company_id, line=line, months=months)

    @staticmethod
    def _calculate_entry_actuals(*, company_id: int, line: FinancialBudgetLine, months: List[date]) -> Dict[str, float]:
        if not months:
            return {}
        start_date, end_date = months[0], months[-1]
        date_field = FinancialEntry.competence_date if line.budget_view == "competence" else FinancialEntry.due_date
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.entry_type != "transfer",
            FinancialEntry.movement_nature == line.movement_nature,
            date_field >= start_date,
            date_field <= end_date,
        )
        if line.budget_view == "due":
            query = query.filter(FinancialEntry.entry_type != "adjustment")
        if line.chart_account_id:
            query = query.filter(FinancialEntry.chart_account_id == line.chart_account_id)
        if line.cost_center_id:
            query = query.filter(FinancialEntry.cost_center_id == line.cost_center_id)
        if line.activity_id:
            query = query.filter(FinancialEntry.activity_id == line.activity_id)
        if line.process_instance_id:
            query = query.filter(FinancialEntry.process_instance_id == line.process_instance_id)
        if line.routine_id:
            query = query.filter(FinancialEntry.routine_id == line.routine_id)

        totals: Dict[str, float] = {month.isoformat(): 0.0 for month in months}
        for item in query.all():
            target_date = item.competence_date if line.budget_view == "competence" else item.due_date
            if not target_date:
                continue
            month_key = target_date.replace(day=1).isoformat()
            if month_key in totals:
                totals[month_key] += float(item.original_amount or 0)
        return totals

    @staticmethod
    def _calculate_cash_actuals(*, company_id: int, line: FinancialBudgetLine, months: List[date]) -> Dict[str, float]:
        if not months:
            return {}
        start_date, end_date = months[0], months[-1]
        query = (
            db.session.query(FinancialSettlement, FinancialEntry)
            .join(FinancialEntry, FinancialEntry.id == FinancialSettlement.financial_entry_id)
            .filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                FinancialSettlement.settlement_date >= start_date,
                FinancialSettlement.settlement_date <= end_date,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
                FinancialEntry.entry_type != "transfer",
                FinancialEntry.entry_type != "adjustment",
                FinancialEntry.movement_nature == line.movement_nature,
            )
        )
        if line.chart_account_id:
            query = query.filter(FinancialEntry.chart_account_id == line.chart_account_id)
        if line.cost_center_id:
            query = query.filter(FinancialEntry.cost_center_id == line.cost_center_id)
        if line.activity_id:
            query = query.filter(FinancialEntry.activity_id == line.activity_id)
        if line.process_instance_id:
            query = query.filter(FinancialEntry.process_instance_id == line.process_instance_id)
        if line.routine_id:
            query = query.filter(FinancialEntry.routine_id == line.routine_id)

        totals: Dict[str, float] = {month.isoformat(): 0.0 for month in months}
        for settlement, _entry in query.all():
            month_key = settlement.settlement_date.replace(day=1).isoformat()
            if month_key in totals:
                totals[month_key] += float(settlement.net_amount or 0)
        return totals
