from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

from models.financial import FinancialSchedule
from models.financial_budget import FinancialBudgetDocument
from services.financial_service import FinancialService


_DECIMAL_ZERO = Decimal("0")
_DECIMAL_TOLERANCE = Decimal("0.01")


class FinancialBudgetSchedulePolicy:
    CAPACITY_EXCEEDED_MESSAGE = "A soma das parcelas ultrapassa o valor executado da NF/equivalente."

    @staticmethod
    def get_document_capacity(
        *,
        company_id: int,
        budget_document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        exclude_schedule_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        document = FinancialBudgetDocument.query.filter(
            FinancialBudgetDocument.id == budget_document_id,
            FinancialBudgetDocument.company_id == company_id,
            FinancialBudgetDocument.deleted_at.is_(None),
        ).first()
        if not document:
            return None, "NF/equivalente orçamentária não encontrada no escopo da empresa."

        schedules = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.budget_document_id == budget_document_id,
            FinancialSchedule.deleted_at.is_(None),
        ).all()
        scheduled_total = sum(
            (
                Decimal(str(item.template_amount or 0))
                for item in schedules
                if exclude_schedule_id is None or int(getattr(item, "id", 0) or 0) != int(exclude_schedule_id)
            ),
            _DECIMAL_ZERO,
        )
        document_total = Decimal(str(document.document_amount or 0))
        return {
            "document": document,
            "scheduled_total": scheduled_total,
            "document_total": document_total,
            "available_to_schedule": document_total - scheduled_total,
        }, None

    @staticmethod
    def would_exceed_document_capacity(
        *,
        scheduled_total: Any,
        requested_amount: Any,
        document_total: Any,
    ) -> bool:
        effective_scheduled_total = Decimal(str(scheduled_total or 0))
        effective_requested_amount = Decimal(str(requested_amount or 0))
        effective_document_total = Decimal(str(document_total or 0))
        return effective_scheduled_total + effective_requested_amount > effective_document_total + _DECIMAL_TOLERANCE

    @staticmethod
    def validate_document_schedule_amount(
        *,
        company_id: int,
        budget_document_id: Optional[int],
        requested_amount: Any,
        allowed_company_ids: Optional[Sequence[int]] = None,
        exclude_schedule_id: Optional[int] = None,
    ) -> Optional[str]:
        if not budget_document_id:
            return None

        capacity, error = FinancialBudgetSchedulePolicy.get_document_capacity(
            company_id=company_id,
            budget_document_id=int(budget_document_id),
            allowed_company_ids=allowed_company_ids,
            exclude_schedule_id=exclude_schedule_id,
        )
        if error:
            return error
        assert capacity is not None

        if FinancialBudgetSchedulePolicy.would_exceed_document_capacity(
            scheduled_total=capacity["scheduled_total"],
            requested_amount=requested_amount,
            document_total=capacity["document_total"],
        ):
            return FinancialBudgetSchedulePolicy.CAPACITY_EXCEEDED_MESSAGE
        return None
