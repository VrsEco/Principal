from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialSchedule, FinancialTitleAdjustment
from services.financial_title_balance_service import FinancialTitleBalanceService


class FinancialSettlementCompositionService:
    """Serviço de composição assistida de Baixas de Títulos Financeiros.

    Centraliza a simulação e a efetivação da baixa com principal e ajustes
    separados, garantindo que a composição explícita respeite os saldos oficiais
    do título e dos ajustes autônomos.
    """

    POSITIVE_ADJUSTMENT_COMPONENTS = {"monetary_correction", "interest", "fine", "manual_adjustment"}
    SETTLEMENT_COMPONENTS = {"principal", "monetary_correction", "interest", "fine", "discount", "manual_adjustment"}

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _money(value: Any) -> Decimal:
        return FinancialSettlementCompositionService._decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
    def _fetch_schedule(*, company_id: int, schedule_id: int) -> Optional[FinancialSchedule]:
        return FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _due_date(schedule: FinancialSchedule) -> Optional[date]:
        return getattr(schedule, "next_due_date", None) or getattr(schedule, "first_due_date", None) or getattr(schedule, "start_date", None)

    @staticmethod
    def _list_open_adjustments(*, company_id: int, schedule_id: int) -> List[FinancialTitleAdjustment]:
        return FinancialTitleAdjustment.query.filter(
            FinancialTitleAdjustment.company_id == company_id,
            FinancialTitleAdjustment.financial_schedule_id == schedule_id,
            FinancialTitleAdjustment.deleted_at.is_(None),
            FinancialTitleAdjustment.status.in_(["open", "partial"]),
            FinancialTitleAdjustment.open_amount > 0,
        ).order_by(FinancialTitleAdjustment.calculation_date.asc(), FinancialTitleAdjustment.id.asc()).all()

    @staticmethod
    def _open_adjustments_by_type(adjustments: Sequence[FinancialTitleAdjustment]) -> Dict[str, Decimal]:
        buckets: Dict[str, Decimal] = {}
        for adjustment in adjustments:
            adjustment_type = str(getattr(adjustment, "adjustment_type", "") or "").strip()
            if adjustment_type == "writeoff":
                adjustment_type = "discount"
            buckets[adjustment_type] = buckets.get(adjustment_type, Decimal("0.00")) + FinancialSettlementCompositionService._money(
                getattr(adjustment, "open_amount", 0)
            )
        return buckets

    @staticmethod
    def _requested_amounts(payload: Dict[str, Any], *, balance: Dict[str, Any], open_by_type: Dict[str, Decimal]) -> Dict[str, Decimal]:
        composition = dict(payload.get("composition") or {})
        explicit = any(key in composition for key in FinancialSettlementCompositionService.SETTLEMENT_COMPONENTS)
        if explicit:
            return {
                component_type: FinancialSettlementCompositionService._money(composition.get(component_type))
                for component_type in FinancialSettlementCompositionService.SETTLEMENT_COMPONENTS
            }

        gross_amount = FinancialSettlementCompositionService._money(
            payload.get("gross_amount") or payload.get("net_amount") or payload.get("amount")
        )
        remaining = gross_amount
        amounts = {component_type: Decimal("0.00") for component_type in FinancialSettlementCompositionService.SETTLEMENT_COMPONENTS}
        for component_type in ("monetary_correction", "interest", "fine", "manual_adjustment"):
            if remaining <= 0:
                break
            open_amount = open_by_type.get(component_type, Decimal("0.00"))
            applied = min(open_amount, remaining)
            amounts[component_type] = applied
            remaining -= applied
        principal_open = FinancialSettlementCompositionService._money(balance.get("principal_open"))
        amounts["principal"] = min(principal_open, max(remaining, Decimal("0.00")))
        return amounts

    @staticmethod
    def _gross_from_amounts(amounts: Dict[str, Decimal]) -> Decimal:
        positive = sum((amounts.get(component_type, Decimal("0.00")) for component_type in FinancialSettlementCompositionService.SETTLEMENT_COMPONENTS if component_type != "discount"), Decimal("0.00"))
        return FinancialSettlementCompositionService._money(positive - amounts.get("discount", Decimal("0.00")))

    @staticmethod
    def _validate_amounts(*, amounts: Dict[str, Decimal], balance: Dict[str, Any], open_by_type: Dict[str, Decimal]) -> List[str]:
        errors: List[str] = []
        principal_open = FinancialSettlementCompositionService._money(balance.get("principal_open"))
        if amounts.get("principal", Decimal("0.00")) > principal_open:
            errors.append("Valor de principal da baixa excede o principal em aberto do título.")
        for component_type in FinancialSettlementCompositionService.POSITIVE_ADJUSTMENT_COMPONENTS:
            amount = amounts.get(component_type, Decimal("0.00"))
            if amount <= 0:
                continue
            if amount > open_by_type.get(component_type, Decimal("0.00")):
                errors.append(f"Valor de {component_type} excede o ajuste em aberto disponível.")
        positive_total = sum((value for key, value in amounts.items() if key != "discount"), Decimal("0.00"))
        if amounts.get("discount", Decimal("0.00")) > positive_total:
            errors.append("Desconto informado não pode superar a soma dos componentes positivos da baixa.")
        if FinancialSettlementCompositionService._gross_from_amounts(amounts) <= 0:
            errors.append("Valor bruto da baixa deve ser maior que zero.")
        return errors

    @staticmethod
    def _build_component_payloads(
        *,
        amounts: Dict[str, Decimal],
        adjustments: Sequence[FinancialTitleAdjustment],
        schedule: FinancialSchedule,
        settlement_date: date,
    ) -> List[Dict[str, Any]]:
        components: List[Dict[str, Any]] = []
        due_date = FinancialSettlementCompositionService._due_date(schedule)
        principal_amount = amounts.get("principal", Decimal("0.00"))
        if principal_amount > 0:
            components.append({
                "component_type": "principal",
                "amount": principal_amount,
                "competence_date": getattr(schedule, "competence_date", None) or settlement_date,
                "due_date": due_date,
                "source": "user",
                "metadata_json": {"source_context": "assisted_settlement_composition"},
            })

        adjustments_by_type: Dict[str, List[FinancialTitleAdjustment]] = {}
        for adjustment in adjustments:
            adjustment_type = str(getattr(adjustment, "adjustment_type", "") or "").strip()
            if adjustment_type == "writeoff":
                adjustment_type = "discount"
            adjustments_by_type.setdefault(adjustment_type, []).append(adjustment)

        for component_type in ("monetary_correction", "interest", "fine", "manual_adjustment", "discount"):
            remaining = amounts.get(component_type, Decimal("0.00"))
            if remaining <= 0:
                continue
            if component_type == "discount":
                components.append({
                    "component_type": "discount",
                    "amount": remaining,
                    "competence_date": settlement_date,
                    "due_date": settlement_date,
                    "source": "user",
                    "metadata_json": {"source_context": "assisted_settlement_composition"},
                })
                continue
            for adjustment in adjustments_by_type.get(component_type, []):
                if remaining <= 0:
                    break
                open_amount = FinancialSettlementCompositionService._money(getattr(adjustment, "open_amount", 0))
                applied = min(open_amount, remaining)
                if applied <= 0:
                    continue
                components.append({
                    "component_type": component_type,
                    "amount": applied,
                    "competence_date": settlement_date,
                    "due_date": settlement_date,
                    "source": "user",
                    "origin_adjustment_id": getattr(adjustment, "id", None),
                    "metadata_json": {"source_context": "assisted_settlement_composition"},
                })
                remaining -= applied
        return components

    @staticmethod
    def _aggregate_settlement_fields(amounts: Dict[str, Decimal]) -> Dict[str, Decimal]:
        return {
            "principal_amount": amounts.get("principal", Decimal("0.00")),
            "interest_amount": amounts.get("interest", Decimal("0.00")),
            "penalty_amount": amounts.get("fine", Decimal("0.00")),
            "discount_amount": amounts.get("discount", Decimal("0.00")),
            "fee_amount": Decimal("0.00"),
            "other_adjustments_amount": amounts.get("monetary_correction", Decimal("0.00")) + amounts.get("manual_adjustment", Decimal("0.00")),
        }

    @staticmethod
    def simulate_settlement(
        *,
        company_id: int,
        schedule_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialSettlementCompositionService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        schedule = FinancialSettlementCompositionService._fetch_schedule(company_id=company_id, schedule_id=schedule_id)
        if not schedule:
            return None, "Título financeiro não encontrado no escopo da empresa."
        settlement_date = payload.get("settlement_date") or date.today()
        if isinstance(settlement_date, str):
            try:
                settlement_date = date.fromisoformat(settlement_date)
            except ValueError:
                return None, "Data da baixa inválida. Use YYYY-MM-DD."

        balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule, reference_date=settlement_date)
        adjustments = FinancialSettlementCompositionService._list_open_adjustments(company_id=company_id, schedule_id=schedule_id)
        open_by_type = FinancialSettlementCompositionService._open_adjustments_by_type(adjustments)
        amounts = FinancialSettlementCompositionService._requested_amounts(payload, balance=balance, open_by_type=open_by_type)
        validation_errors = FinancialSettlementCompositionService._validate_amounts(amounts=amounts, balance=balance, open_by_type=open_by_type)
        gross_amount = FinancialSettlementCompositionService._gross_from_amounts(amounts)
        principal_after = max(FinancialSettlementCompositionService._money(balance.get("principal_open")) - amounts.get("principal", Decimal("0.00")), Decimal("0.00"))
        adjustments_after = max(FinancialSettlementCompositionService._money(balance.get("adjustments_open")) - sum((amounts.get(item, Decimal("0.00")) for item in FinancialSettlementCompositionService.POSITIVE_ADJUSTMENT_COMPONENTS), Decimal("0.00")), Decimal("0.00"))
        discount = amounts.get("discount", Decimal("0.00"))
        total_after = max(principal_after + adjustments_after - discount, Decimal("0.00"))

        components = FinancialSettlementCompositionService._build_component_payloads(
            amounts=amounts,
            adjustments=adjustments,
            schedule=schedule,
            settlement_date=settlement_date,
        )
        aggregate_fields = FinancialSettlementCompositionService._aggregate_settlement_fields(amounts)
        return {
            "financial_schedule_id": schedule_id,
            "company_id": company_id,
            "settlement_date": settlement_date.isoformat(),
            "before": {
                "principal_open": balance.get("principal_open"),
                "adjustments_open": balance.get("adjustments_open"),
                "total_due": balance.get("total_open"),
            },
            "available_adjustments": {key: float(value) for key, value in open_by_type.items()},
            "composition": {
                **{key: float(FinancialSettlementCompositionService._money(value)) for key, value in amounts.items()},
                "gross_amount": float(gross_amount),
            },
            "settlement_payload": {
                **{key: float(value) for key, value in aggregate_fields.items()},
                "gross_amount": float(gross_amount),
                "net_amount": float(gross_amount),
                "settlement_components": [
                    {
                        **component,
                        "amount": float(component["amount"]),
                        "competence_date": component["competence_date"].isoformat() if component.get("competence_date") else None,
                        "due_date": component["due_date"].isoformat() if component.get("due_date") else None,
                    }
                    for component in components
                ],
            },
            "after": {
                "principal_open": float(FinancialSettlementCompositionService._money(principal_after)),
                "adjustments_open": float(FinancialSettlementCompositionService._money(adjustments_after)),
                "total_open": float(FinancialSettlementCompositionService._money(total_after)),
            },
            "valid": not validation_errors,
            "errors": validation_errors,
        }, None

    @staticmethod
    def _apply_adjustment_settlement(*, company_id: int, components: Sequence[Dict[str, Any]]) -> None:
        for component in components:
            origin_id = component.get("origin_adjustment_id")
            if not origin_id:
                continue
            adjustment = FinancialTitleAdjustment.query.filter(
                FinancialTitleAdjustment.id == int(origin_id),
                FinancialTitleAdjustment.company_id == company_id,
                FinancialTitleAdjustment.deleted_at.is_(None),
            ).first()
            if not adjustment:
                continue
            amount = FinancialSettlementCompositionService._money(component.get("amount"))
            adjustment.settled_amount = FinancialSettlementCompositionService._money(getattr(adjustment, "settled_amount", 0)) + amount
            adjustment.open_amount = max(FinancialSettlementCompositionService._money(getattr(adjustment, "generated_amount", 0)) - adjustment.settled_amount, Decimal("0.00"))
            adjustment.status = "settled" if adjustment.open_amount == 0 else "partial"

    @staticmethod
    def create_assisted_settlement(
        *,
        company_id: int,
        schedule_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        simulation, error = FinancialSettlementCompositionService.simulate_settlement(
            company_id=company_id,
            schedule_id=schedule_id,
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        if not simulation or not simulation.get("valid"):
            return None, "; ".join(simulation.get("errors") or ["Composição da baixa inválida."])

        settlement_payload = dict(payload or {})
        settlement_payload.pop("composition", None)
        settlement_payload.setdefault("settlement_type", "manual")
        settlement_payload["settlement_date"] = simulation["settlement_date"]
        settlement_payload.update(simulation["settlement_payload"])
        settlement_payload["settlement_components"] = simulation["settlement_payload"]["settlement_components"]
        metadata = dict(settlement_payload.get("metadata_json") or {})
        metadata["assisted_composition"] = simulation["composition"]
        settlement_payload["metadata_json"] = metadata

        from services.financial_schedule_service import FinancialScheduleService

        result, settlement_error = FinancialScheduleService.create_settlement_from_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            payload=settlement_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if settlement_error:
            return None, settlement_error

        try:
            FinancialSettlementCompositionService._apply_adjustment_settlement(
                company_id=company_id,
                components=simulation["settlement_payload"]["settlement_components"],
            )
            db.session.commit()
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            db.session.rollback()
            return None, f"Baixa criada, mas houve erro ao atualizar ajustes do título: {str(exc)}"

        schedule = FinancialSettlementCompositionService._fetch_schedule(company_id=company_id, schedule_id=schedule_id)
        balances_after = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule) if schedule else None
        return {
            **dict(result or {}),
            "simulation": simulation,
            "title_balances": balances_after,
        }, None
