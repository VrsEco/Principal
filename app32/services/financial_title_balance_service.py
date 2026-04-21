from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from financial_domain import (
    TITLE_ADJUSTMENT_OPEN_STATUSES,
    build_title_operational_state_metadata,
    resolve_title_settlement_state,
    title_state_enters_transactional_views,
    title_state_has_open_balance,
)
from models import db
from models.financial import (
    FinancialEntry,
    FinancialSchedule,
    FinancialSettlement,
    FinancialSettlementComponent,
    FinancialTitleAdjustment,
)


class FinancialTitleBalanceService:
    """Serviço oficial para saldo de Títulos Financeiros.

    A partir desta camada, o saldo operacional do título deixa de ser inferido
    em telas/relatórios e passa a expor sempre a tríade obrigatória:
    principal em aberto, ajustes em aberto e total exigível.
    """

    POSITIVE_ADJUSTMENT_TYPES = {"monetary_correction", "interest", "fine", "manual_adjustment"}
    DISCOUNT_ADJUSTMENT_TYPES = {"discount", "writeoff"}
    POSITIVE_COMPONENT_TYPES = {"monetary_correction", "interest", "fine", "manual_adjustment"}
    DISCOUNT_COMPONENT_TYPES = {"discount"}

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _money(value: Any) -> Decimal:
        return FinancialTitleBalanceService._decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _float(value: Any) -> float:
        return float(FinancialTitleBalanceService._money(value))

    @staticmethod
    def _signed(amount: Decimal, movement_nature: Optional[str]) -> float:
        absolute_amount = abs(FinancialTitleBalanceService._money(amount))
        signed_amount = -absolute_amount if movement_nature == "debit" else absolute_amount
        return float(signed_amount)

    @staticmethod
    def _ensure_company_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        if allowed_company_ids is None:
            return None
        normalized = {int(cid) for cid in allowed_company_ids if cid is not None}
        if not normalized:
            return "Nenhuma empresa autorizada encontrada para a operação financeira."
        if int(company_id) not in normalized:
            return "A operação financeira está fora do escopo da empresa autorizada."
        return None

    @staticmethod
    def _is_active_settlement(settlement: Any) -> bool:
        return getattr(settlement, "deleted_at", None) is None and getattr(settlement, "settlement_status", None) != "cancelled"

    @staticmethod
    def _component_amounts_by_settlement(components: Iterable[Any]) -> Dict[int, Dict[str, Decimal]]:
        grouped: Dict[int, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for component in components:
            settlement_id = getattr(component, "financial_settlement_id", None)
            if settlement_id is None:
                continue
            component_type = str(getattr(component, "component_type", "") or "").strip()
            grouped[int(settlement_id)][component_type] += FinancialTitleBalanceService._money(
                getattr(component, "amount", 0)
            )
        return grouped

    @staticmethod
    def _adjustment_component_amounts_by_origin(components: Iterable[Any]) -> Dict[int, Decimal]:
        grouped: Dict[int, Decimal] = defaultdict(Decimal)
        for component in components:
            origin_id = getattr(component, "origin_adjustment_id", None)
            if origin_id is None:
                continue
            component_type = str(getattr(component, "component_type", "") or "").strip()
            if component_type in FinancialTitleBalanceService.POSITIVE_COMPONENT_TYPES:
                grouped[int(origin_id)] += FinancialTitleBalanceService._money(getattr(component, "amount", 0))
        return grouped

    @staticmethod
    def calculate_from_records(
        *,
        schedule: Any,
        entries: Optional[Iterable[Any]] = None,
        settlements: Optional[Iterable[Any]] = None,
        components: Optional[Iterable[Any]] = None,
        adjustments: Optional[Iterable[Any]] = None,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        entries = list(entries or [])
        settlements = [item for item in list(settlements or []) if FinancialTitleBalanceService._is_active_settlement(item)]
        active_settlement_ids = {
            int(getattr(item, "id", 0))
            for item in settlements
            if getattr(item, "id", None) is not None
        }
        components = [
            item
            for item in list(components or [])
            if getattr(item, "financial_settlement_id", None) is None
            or int(getattr(item, "financial_settlement_id", 0) or 0) in active_settlement_ids
        ]
        adjustments = list(adjustments or [])

        principal_amount = FinancialTitleBalanceService._money(getattr(schedule, "template_amount", 0))
        if principal_amount == 0 and entries:
            principal_amount = sum(
                (FinancialTitleBalanceService._money(getattr(entry, "original_amount", 0)) for entry in entries),
                Decimal("0"),
            )

        component_amounts = FinancialTitleBalanceService._component_amounts_by_settlement(components)
        principal_settled = Decimal("0")
        settlement_total_amount = Decimal("0")
        adjustments_settled_by_components = Decimal("0")
        discounts_applied_by_components = Decimal("0")

        for settlement in settlements:
            settlement_total_amount += FinancialTitleBalanceService._money(
                getattr(settlement, "net_amount", None)
                or getattr(settlement, "gross_amount", None)
                or Decimal("0")
            )
            settlement_id = getattr(settlement, "id", None)
            per_type = component_amounts.get(int(settlement_id), {}) if settlement_id is not None else {}
            if per_type:
                principal_settled += per_type.get("principal", Decimal("0"))
                adjustments_settled_by_components += sum(
                    (per_type.get(component_type, Decimal("0")) for component_type in FinancialTitleBalanceService.POSITIVE_COMPONENT_TYPES),
                    Decimal("0"),
                )
                discounts_applied_by_components += sum(
                    (per_type.get(component_type, Decimal("0")) for component_type in FinancialTitleBalanceService.DISCOUNT_COMPONENT_TYPES),
                    Decimal("0"),
                )
            else:
                principal_settled += FinancialTitleBalanceService._money(getattr(settlement, "principal_amount", 0))
                adjustments_settled_by_components += sum(
                    (
                        FinancialTitleBalanceService._money(getattr(settlement, field_name, 0))
                        for field_name in ("interest_amount", "penalty_amount", "fee_amount", "other_adjustments_amount")
                    ),
                    Decimal("0"),
                )
                discounts_applied_by_components += FinancialTitleBalanceService._money(getattr(settlement, "discount_amount", 0))

        principal_open = max(principal_amount - principal_settled, Decimal("0"))

        component_settled_by_origin = FinancialTitleBalanceService._adjustment_component_amounts_by_origin(components)
        adjustments_generated = Decimal("0")
        adjustments_settled = Decimal("0")
        adjustments_open = Decimal("0")
        discounts_open = Decimal("0")

        for adjustment in adjustments:
            if getattr(adjustment, "deleted_at", None) is not None:
                continue
            status = str(getattr(adjustment, "status", "") or "").strip()
            if status == "cancelled":
                continue
            adjustment_type = str(getattr(adjustment, "adjustment_type", "") or "").strip()
            generated = FinancialTitleBalanceService._money(getattr(adjustment, "generated_amount", 0))
            stored_settled = FinancialTitleBalanceService._money(getattr(adjustment, "settled_amount", 0))
            component_settled = component_settled_by_origin.get(int(getattr(adjustment, "id", 0) or 0), Decimal("0"))
            settled = max(stored_settled, component_settled)
            open_amount = max(generated - settled, Decimal("0"))
            stored_open = FinancialTitleBalanceService._money(getattr(adjustment, "open_amount", open_amount))
            if status in TITLE_ADJUSTMENT_OPEN_STATUSES:
                open_amount = stored_open if stored_open > 0 else open_amount
            else:
                open_amount = Decimal("0")

            if adjustment_type in FinancialTitleBalanceService.DISCOUNT_ADJUSTMENT_TYPES:
                discounts_open += open_amount
                continue
            if adjustment_type in FinancialTitleBalanceService.POSITIVE_ADJUSTMENT_TYPES:
                adjustments_generated += generated
                adjustments_settled += settled
                adjustments_open += open_amount

        total_open = max(principal_open + adjustments_open - discounts_open, Decimal("0"))
        editable_open = {
            "principal": FinancialTitleBalanceService._float(principal_open),
            "financial_correction": FinancialTitleBalanceService._float(adjustments_open),
            "discount": FinancialTitleBalanceService._float(discounts_open),
            "gross_amount": FinancialTitleBalanceService._float(max(principal_open + adjustments_open - discounts_open, Decimal("0"))),
            "total_open": FinancialTitleBalanceService._float(total_open),
        }
        editable_rules = {
            "principal_max": editable_open["principal"],
            "allows_free_financial_correction": True,
            "allows_free_discount": True,
            "requires_principal_within_open_balance": True,
        }
        settlement_state = resolve_title_settlement_state(
            principal_amount=principal_amount,
            principal_settled=principal_settled,
            adjustments_settled=adjustments_settled,
            discounts_applied=discounts_applied_by_components,
            total_open=total_open,
        )

        movement_nature = getattr(schedule, "movement_nature", None)
        operational_state = build_title_operational_state_metadata(
            schedule_status=getattr(schedule, "status", None),
            settlement_state=settlement_state,
            entry_type=getattr(schedule, "entry_type", None),
            metadata_json=getattr(schedule, "metadata_json", None),
        )
        result = {
            "financial_schedule_id": getattr(schedule, "id", None),
            "company_id": getattr(schedule, "company_id", None),
            "schedule_code": getattr(schedule, "schedule_code", None),
            "status": getattr(schedule, "status", None),
            "reference_date": (reference_date or date.today()).isoformat(),
            "principal_amount": FinancialTitleBalanceService._float(principal_amount),
            "principal_settled": FinancialTitleBalanceService._float(principal_settled),
            "settlement_total_amount": FinancialTitleBalanceService._float(settlement_total_amount),
            "principal_open": FinancialTitleBalanceService._float(principal_open),
            "adjustments_generated": FinancialTitleBalanceService._float(adjustments_generated),
            "adjustments_settled": FinancialTitleBalanceService._float(adjustments_settled),
            "adjustments_open": FinancialTitleBalanceService._float(adjustments_open),
            "discounts_open": FinancialTitleBalanceService._float(discounts_open),
            "discounts_applied": FinancialTitleBalanceService._float(discounts_applied_by_components),
            "total_open": FinancialTitleBalanceService._float(total_open),
            "total_due": FinancialTitleBalanceService._float(total_open),
            "signed_principal_amount": FinancialTitleBalanceService._signed(principal_amount, movement_nature),
            "signed_principal_settled": FinancialTitleBalanceService._signed(principal_settled, movement_nature),
            "signed_principal_open": FinancialTitleBalanceService._signed(principal_open, movement_nature),
            "signed_adjustments_open": FinancialTitleBalanceService._signed(adjustments_open, movement_nature),
            "signed_total_open": FinancialTitleBalanceService._signed(total_open, movement_nature),
            "editable_open": editable_open,
            "editable_rules": editable_rules,
            "entry_count": len(entries),
            "settlement_count": len(settlements),
            "settlement_state": settlement_state,
            "operational_state": operational_state["code"],
            "operational_state_label": operational_state["label"],
            "has_open_balance": title_state_has_open_balance(operational_state["code"]) and FinancialTitleBalanceService._float(total_open) > 0,
            "enters_transactional_views": title_state_enters_transactional_views(operational_state["code"]),
            "include_in_accounting_reports": operational_state["include_in_accounting_reports"],
            "include_in_projected_reports": operational_state["include_in_projected_reports"],
        }
        return result

    @staticmethod
    def calculate_for_schedule(
        *,
        schedule: FinancialSchedule,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        entries = (
            FinancialEntry.query.filter(
                FinancialEntry.company_id == schedule.company_id,
                db.or_(
                    FinancialEntry.financial_schedule_id == schedule.id,
                    FinancialEntry.external_reference == f"financial_schedule:{schedule.id}",
                ),
                FinancialEntry.deleted_at.is_(None),
            )
            .order_by(FinancialEntry.id.asc())
            .all()
        )
        entry_ids = [int(entry.id) for entry in entries if getattr(entry, "id", None) is not None]
        settlements: List[FinancialSettlement] = []
        components: List[FinancialSettlementComponent] = []
        if entry_ids:
            settlements = (
                FinancialSettlement.query.filter(
                    FinancialSettlement.company_id == schedule.company_id,
                    FinancialSettlement.financial_entry_id.in_(entry_ids),
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                )
                .order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc())
                .all()
            )
            settlement_ids = [int(item.id) for item in settlements if getattr(item, "id", None) is not None]
            if settlement_ids:
                components = (
                    FinancialSettlementComponent.query.filter(
                        FinancialSettlementComponent.company_id == schedule.company_id,
                        FinancialSettlementComponent.financial_settlement_id.in_(settlement_ids),
                    )
                    .order_by(FinancialSettlementComponent.id.asc())
                    .all()
                )

        schedule_components = (
            FinancialSettlementComponent.query.filter(
                FinancialSettlementComponent.company_id == schedule.company_id,
                FinancialSettlementComponent.financial_schedule_id == schedule.id,
            )
            .order_by(FinancialSettlementComponent.id.asc())
            .all()
        )
        known_component_ids = {getattr(item, "id", None) for item in components}
        components.extend([item for item in schedule_components if getattr(item, "id", None) not in known_component_ids])

        adjustments = (
            FinancialTitleAdjustment.query.filter(
                FinancialTitleAdjustment.company_id == schedule.company_id,
                FinancialTitleAdjustment.financial_schedule_id == schedule.id,
                FinancialTitleAdjustment.deleted_at.is_(None),
                FinancialTitleAdjustment.status != "cancelled",
            )
            .order_by(FinancialTitleAdjustment.calculation_date.asc(), FinancialTitleAdjustment.id.asc())
            .all()
        )
        return FinancialTitleBalanceService.calculate_from_records(
            schedule=schedule,
            entries=entries,
            settlements=settlements,
            components=components,
            adjustments=adjustments,
            reference_date=reference_date,
        )

    @staticmethod
    def get_title_balance(
        *,
        company_id: int,
        schedule_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        reference_date: Optional[date] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialTitleBalanceService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título financeiro não encontrado no escopo da empresa."

        return FinancialTitleBalanceService.calculate_for_schedule(
            schedule=schedule,
            reference_date=reference_date,
        ), None
