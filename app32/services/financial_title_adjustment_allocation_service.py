from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from models.financial import (
    FinancialSchedule,
    FinancialTitleAdjustment,
    FinancialTitleAdjustmentAllocation,
)


class FinancialTitleAdjustmentAllocationService:
    """Serviço de domínio para herdar o rateio principal nos ajustes do título."""

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

        dimensions = {
            "chart_account_id": getattr(schedule, "chart_account_id", None),
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
            "inheritance_mode": "principal_defaults",
            "inherited_from_schedule_id": getattr(schedule, "id", None),
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
