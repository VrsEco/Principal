from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from models.financial import (
    FinancialCorrectionIndex,
    FinancialDiscountRule,
    FinancialSchedule,
    FinancialTitleAdjustment,
    FinancialTitleAdjustmentAllocation,
)


class FinancialTitleAdjustmentAllocationService:
    """Serviço de domínio para herdar o rateio principal nos ajustes do título."""

    CORRECTION_ADJUSTMENT_TYPES = {"monetary_correction", "interest", "fine", "manual_adjustment"}
    DISCOUNT_ADJUSTMENT_TYPES = {"discount", "writeoff"}

    @staticmethod
    def _resolve_adjustment_chart_account_id(
        *,
        adjustment: FinancialTitleAdjustment,
        schedule: FinancialSchedule,
    ) -> Optional[int]:
        adjustment_type = str(getattr(adjustment, "adjustment_type", "") or "").strip().lower()
        if adjustment_type in FinancialTitleAdjustmentAllocationService.DISCOUNT_ADJUSTMENT_TYPES:
            model = FinancialDiscountRule
            metadata_key = "discount_rule_id"
        elif adjustment_type in FinancialTitleAdjustmentAllocationService.CORRECTION_ADJUSTMENT_TYPES:
            model = FinancialCorrectionIndex
            metadata_key = "correction_index_id"
        else:
            return None

        rule_snapshot = dict(getattr(adjustment, "rule_snapshot_json", None) or {})
        schedule_metadata = dict(getattr(schedule, "metadata_json", None) or {})
        source_id = rule_snapshot.get("rule_id") or schedule_metadata.get(metadata_key)
        if source_id in ("", None):
            return None
        try:
            normalized_source_id = int(source_id)
        except (TypeError, ValueError):
            return None

        source = model.query.filter(
            model.id == normalized_source_id,
            model.company_id == adjustment.company_id,
            model.deleted_at.is_(None),
            model.is_active.is_(True),
        ).first()
        if not source:
            return None

        chart_account_id = dict(getattr(source, "metadata_json", None) or {}).get("chart_account_id")
        if chart_account_id in ("", None):
            return None
        try:
            return int(chart_account_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def build_default_allocations(
        *,
        adjustment: FinancialTitleAdjustment,
        schedule: Optional[FinancialSchedule] = None,
    ) -> List[FinancialTitleAdjustmentAllocation]:
        schedule = schedule or getattr(adjustment, "schedule", None)
        if not schedule:
            return []
        if adjustment.company_id != schedule.company_id:
            raise ValueError("Título e ajuste financeiro fora do mesmo escopo de empresa.")

        resolved_chart_account_id = FinancialTitleAdjustmentAllocationService._resolve_adjustment_chart_account_id(
            adjustment=adjustment,
            schedule=schedule,
        )
        dimensions = {
            "chart_account_id": resolved_chart_account_id or getattr(schedule, "chart_account_id", None),
            "cost_center_id": getattr(schedule, "cost_center_id", None),
            "budget_document_id": getattr(schedule, "budget_document_id", None),
            "activity_id": getattr(schedule, "activity_id", None),
            "process_instance_id": getattr(schedule, "process_instance_id", None),
            "routine_id": getattr(schedule, "routine_id", None),
        }
        if not any(value is not None for value in dimensions.values()):
            return []

        amount = Decimal(str(getattr(adjustment, "generated_amount", 0) or 0)).quantize(Decimal("0.01"))
        metadata = {
            "inheritance_source": "financial_schedule",
            "inheritance_mode": "adjustment_rule_defaults" if resolved_chart_account_id else "principal_defaults",
            "inherited_from_schedule_id": getattr(schedule, "id", None),
            "chart_account_source": "adjustment_rule" if resolved_chart_account_id else "financial_schedule",
        }

        allocation = FinancialTitleAdjustmentAllocation(
            company_id=adjustment.company_id,
            financial_title_adjustment_id=adjustment.id,
            percentage=Decimal("100.0000"),
            amount=amount,
            metadata_json=metadata,
            **dimensions,
        )
        return [allocation]
