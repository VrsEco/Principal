from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialCorrectionIndex,
    FinancialDiscountRule,
    FinancialSchedule,
    FinancialTitleAdjustment,
)
from services.financial_title_adjustment_allocation_service import FinancialTitleAdjustmentAllocationService
from services.financial_title_balance_service import FinancialTitleBalanceService


class FinancialTitleAdjustmentService:
    """Motor central de ajustes financeiros dos Títulos.

    Responsável por simular e materializar juros, multa, correção monetária e
    desconto como ajustes autônomos do título, preservando company_id em todas
    as consultas e mantendo a rastreabilidade das regras usadas no cálculo.
    """

    NON_GENERATABLE_STATUSES = {"draft", "cancelled"}

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _money(value: Any) -> Decimal:
        return FinancialTitleAdjustmentService._decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
    def _periods_between(*, due_date: Optional[date], reference_date: date, period: str) -> Decimal:
        if not due_date:
            return Decimal("0")
        overdue_days = max((reference_date - due_date).days, 0)
        if overdue_days <= 0:
            return Decimal("0")
        return Decimal(str(overdue_days / 30)) if str(period or "daily").lower() == "monthly" else Decimal(overdue_days)

    @staticmethod
    def _due_date(schedule: FinancialSchedule) -> Optional[date]:
        return getattr(schedule, "next_due_date", None) or getattr(schedule, "first_due_date", None) or getattr(schedule, "start_date", None)

    @staticmethod
    def _rule_snapshot(rule: Any, *, rule_kind: str) -> Dict[str, Any]:
        if not rule:
            return {}
        metadata = dict(getattr(rule, "metadata_json", None) or {})
        return {
            "rule_kind": rule_kind,
            "rule_id": getattr(rule, "id", None),
            "code": getattr(rule, "code", None),
            "name": getattr(rule, "name", None),
            "metadata_json": metadata,
        }

    @staticmethod
    def _get_active_correction_rule(*, company_id: int, correction_index_id: Optional[int]) -> Optional[FinancialCorrectionIndex]:
        if not correction_index_id:
            return None
        return FinancialCorrectionIndex.query.filter(
            FinancialCorrectionIndex.id == int(correction_index_id),
            FinancialCorrectionIndex.company_id == company_id,
            FinancialCorrectionIndex.deleted_at.is_(None),
            FinancialCorrectionIndex.is_active.is_(True),
        ).first()

    @staticmethod
    def _get_active_discount_rule(*, company_id: int, discount_rule_id: Optional[int]) -> Optional[FinancialDiscountRule]:
        if not discount_rule_id:
            return None
        return FinancialDiscountRule.query.filter(
            FinancialDiscountRule.id == int(discount_rule_id),
            FinancialDiscountRule.company_id == company_id,
            FinancialDiscountRule.deleted_at.is_(None),
            FinancialDiscountRule.is_active.is_(True),
        ).first()

    @staticmethod
    def _build_adjustment_payload(
        *,
        schedule: FinancialSchedule,
        adjustment_type: str,
        amount: Decimal,
        base_amount: Decimal,
        calculation_date: date,
        competence_date: date,
        due_date_reference: Optional[date],
        rule_snapshot: Dict[str, Any],
        metadata_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        generated_amount = FinancialTitleAdjustmentService._money(amount)
        return {
            "company_id": schedule.company_id,
            "financial_schedule_id": schedule.id,
            "adjustment_type": adjustment_type,
            "status": "open" if generated_amount > 0 else "settled",
            "calculation_date": calculation_date,
            "competence_date": competence_date,
            "due_date_reference": due_date_reference,
            "base_amount": FinancialTitleAdjustmentService._money(base_amount),
            "generated_amount": generated_amount,
            "settled_amount": Decimal("0.00"),
            "open_amount": generated_amount,
            "rule_snapshot_json": rule_snapshot,
            "metadata_json": metadata_json,
        }

    @staticmethod
    def simulate_for_schedule(
        *,
        schedule: FinancialSchedule,
        reference_date: Optional[date] = None,
        base_amount: Optional[Any] = None,
    ) -> Dict[str, Any]:
        calculation_date = reference_date or date.today()
        due_date = FinancialTitleAdjustmentService._due_date(schedule)
        metadata = dict(getattr(schedule, "metadata_json", None) or {})
        balance = FinancialTitleBalanceService.calculate_for_schedule(
            schedule=schedule,
            reference_date=calculation_date,
        )
        resolved_base = FinancialTitleAdjustmentService._money(
            base_amount if base_amount is not None else balance.get("principal_open") or getattr(schedule, "template_amount", 0)
        )

        correction_rule = FinancialTitleAdjustmentService._get_active_correction_rule(
            company_id=schedule.company_id,
            correction_index_id=metadata.get("correction_index_id"),
        )
        discount_rule = FinancialTitleAdjustmentService._get_active_discount_rule(
            company_id=schedule.company_id,
            discount_rule_id=metadata.get("discount_rule_id"),
        )

        adjustments: List[Dict[str, Any]] = []
        if correction_rule and due_date:
            rule_metadata = dict(correction_rule.metadata_json or {})
            interest_rate = FinancialTitleAdjustmentService._decimal(rule_metadata.get("interest_rate"))
            penalty_rate = FinancialTitleAdjustmentService._decimal(rule_metadata.get("penalty_rate"))
            penalty_limit_rate = FinancialTitleAdjustmentService._decimal(rule_metadata.get("penalty_limit_rate"))
            monetary_correction_rate = FinancialTitleAdjustmentService._decimal(
                rule_metadata.get("monetary_correction_rate") or rule_metadata.get("correction_rate")
            )
            interest_period = str(rule_metadata.get("interest_period") or "daily").lower()
            penalty_period = str(rule_metadata.get("penalty_period") or "daily").lower()
            interest_periods = FinancialTitleAdjustmentService._periods_between(
                due_date=due_date,
                reference_date=calculation_date,
                period=interest_period,
            )
            penalty_periods = FinancialTitleAdjustmentService._periods_between(
                due_date=due_date,
                reference_date=calculation_date,
                period=penalty_period,
            )
            correction_snapshot = FinancialTitleAdjustmentService._rule_snapshot(
                correction_rule,
                rule_kind="correction_index",
            )
            if monetary_correction_rate > 0 and interest_periods > 0:
                amount = resolved_base * (monetary_correction_rate / Decimal("100")) * interest_periods
                adjustments.append(FinancialTitleAdjustmentService._build_adjustment_payload(
                    schedule=schedule,
                    adjustment_type="monetary_correction",
                    amount=amount,
                    base_amount=resolved_base,
                    calculation_date=calculation_date,
                    competence_date=calculation_date,
                    due_date_reference=due_date,
                    rule_snapshot=correction_snapshot,
                    metadata_json={"source": "simulate_for_schedule", "rate": str(monetary_correction_rate), "periods": str(interest_periods)},
                ))
            if interest_rate > 0 and interest_periods > 0:
                amount = resolved_base * (interest_rate / Decimal("100")) * interest_periods
                adjustments.append(FinancialTitleAdjustmentService._build_adjustment_payload(
                    schedule=schedule,
                    adjustment_type="interest",
                    amount=amount,
                    base_amount=resolved_base,
                    calculation_date=calculation_date,
                    competence_date=calculation_date,
                    due_date_reference=due_date,
                    rule_snapshot=correction_snapshot,
                    metadata_json={"source": "simulate_for_schedule", "rate": str(interest_rate), "period": interest_period, "periods": str(interest_periods)},
                ))
            effective_penalty_rate = penalty_rate
            if penalty_limit_rate > 0:
                effective_penalty_rate = min(effective_penalty_rate, penalty_limit_rate)
            if effective_penalty_rate > 0 and penalty_periods > 0:
                amount = resolved_base * (effective_penalty_rate / Decimal("100"))
                adjustments.append(FinancialTitleAdjustmentService._build_adjustment_payload(
                    schedule=schedule,
                    adjustment_type="fine",
                    amount=amount,
                    base_amount=resolved_base,
                    calculation_date=calculation_date,
                    competence_date=calculation_date,
                    due_date_reference=due_date,
                    rule_snapshot=correction_snapshot,
                    metadata_json={"source": "simulate_for_schedule", "rate": str(effective_penalty_rate), "period": penalty_period, "periods": str(penalty_periods)},
                ))

        discount_override = FinancialTitleAdjustmentService._money(metadata.get("discount_amount_override"))
        discount_amount = Decimal("0.00")
        discount_snapshot = {}
        if discount_override > 0:
            discount_amount = discount_override
            discount_snapshot = {"rule_kind": "metadata_override", "field": "discount_amount_override"}
        elif discount_rule:
            discount_metadata = dict(discount_rule.metadata_json or {})
            discount_type = str(discount_metadata.get("discount_type") or "").strip().lower()
            discount_value = FinancialTitleAdjustmentService._decimal(discount_metadata.get("value"))
            if discount_value > 0:
                discount_amount = (
                    resolved_base * (discount_value / Decimal("100"))
                    if discount_type == "percentage"
                    else discount_value
                )
                discount_snapshot = FinancialTitleAdjustmentService._rule_snapshot(discount_rule, rule_kind="discount_rule")
        if discount_amount > 0:
            adjustments.append(FinancialTitleAdjustmentService._build_adjustment_payload(
                schedule=schedule,
                adjustment_type="discount",
                amount=discount_amount,
                base_amount=resolved_base,
                calculation_date=calculation_date,
                competence_date=calculation_date,
                due_date_reference=due_date,
                rule_snapshot=discount_snapshot,
                metadata_json={"source": "simulate_for_schedule"},
            ))

        totals = {
            "monetary_correction": Decimal("0.00"),
            "interest": Decimal("0.00"),
            "fine": Decimal("0.00"),
            "discount": Decimal("0.00"),
        }
        for item in adjustments:
            totals[item["adjustment_type"]] = totals.get(item["adjustment_type"], Decimal("0.00")) + item["generated_amount"]
        total_positive = totals["monetary_correction"] + totals["interest"] + totals["fine"]
        total_net = total_positive - totals["discount"]

        return {
            "financial_schedule_id": schedule.id,
            "company_id": schedule.company_id,
            "calculation_date": calculation_date.isoformat(),
            "competence_date": calculation_date.isoformat(),
            "due_date_reference": due_date.isoformat() if due_date else None,
            "base_amount": float(resolved_base),
            "principal_open": balance.get("principal_open"),
            "adjustments": [
                {
                    **item,
                    "base_amount": float(item["base_amount"]),
                    "generated_amount": float(item["generated_amount"]),
                    "settled_amount": float(item["settled_amount"]),
                    "open_amount": float(item["open_amount"]),
                    "calculation_date": item["calculation_date"].isoformat(),
                    "competence_date": item["competence_date"].isoformat(),
                    "due_date_reference": item["due_date_reference"].isoformat() if item["due_date_reference"] else None,
                }
                for item in adjustments
            ],
            "totals": {
                "monetary_correction": float(FinancialTitleAdjustmentService._money(totals["monetary_correction"])),
                "interest": float(FinancialTitleAdjustmentService._money(totals["interest"])),
                "fine": float(FinancialTitleAdjustmentService._money(totals["fine"])),
                "discount": float(FinancialTitleAdjustmentService._money(totals["discount"])),
                "positive_adjustments": float(FinancialTitleAdjustmentService._money(total_positive)),
                "net_adjustments": float(FinancialTitleAdjustmentService._money(total_net)),
            },
        }

    @staticmethod
    def simulate_title_adjustments(
        *,
        company_id: int,
        schedule_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        reference_date: Optional[date] = None,
        base_amount: Optional[Any] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialTitleAdjustmentService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título financeiro não encontrado no escopo da empresa."
        return FinancialTitleAdjustmentService.simulate_for_schedule(
            schedule=schedule,
            reference_date=reference_date,
            base_amount=base_amount,
        ), None

    @staticmethod
    def _find_existing_adjustment(
        *,
        company_id: int,
        schedule_id: int,
        adjustment_type: str,
        calculation_date: date,
    ) -> Optional[FinancialTitleAdjustment]:
        return FinancialTitleAdjustment.query.filter(
            FinancialTitleAdjustment.company_id == company_id,
            FinancialTitleAdjustment.financial_schedule_id == schedule_id,
            FinancialTitleAdjustment.adjustment_type == adjustment_type,
            FinancialTitleAdjustment.calculation_date == calculation_date,
            FinancialTitleAdjustment.deleted_at.is_(None),
            FinancialTitleAdjustment.status.in_(["open", "partial"]),
        ).first()

    @staticmethod
    def materialize_title_adjustments(
        *,
        company_id: int,
        schedule_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        reference_date: Optional[date] = None,
        base_amount: Optional[Any] = None,
        inherit_allocations: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialTitleAdjustmentService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título financeiro não encontrado no escopo da empresa."
        if str(getattr(schedule, "status", "") or "") in FinancialTitleAdjustmentService.NON_GENERATABLE_STATUSES:
            return None, "Título financeiro não está apto para geração de ajustes."

        simulation = FinancialTitleAdjustmentService.simulate_for_schedule(
            schedule=schedule,
            reference_date=reference_date,
            base_amount=base_amount,
        )
        persisted: List[FinancialTitleAdjustment] = []
        try:
            for item in simulation.get("adjustments", []):
                amount = FinancialTitleAdjustmentService._money(item.get("generated_amount"))
                if amount <= 0:
                    continue
                calculation_date = date.fromisoformat(str(item["calculation_date"]))
                existing = FinancialTitleAdjustmentService._find_existing_adjustment(
                    company_id=company_id,
                    schedule_id=schedule_id,
                    adjustment_type=str(item["adjustment_type"]),
                    calculation_date=calculation_date,
                )
                payload = {
                    "company_id": company_id,
                    "financial_schedule_id": schedule_id,
                    "adjustment_type": item["adjustment_type"],
                    "status": item.get("status") or "open",
                    "calculation_date": calculation_date,
                    "competence_date": date.fromisoformat(str(item["competence_date"])),
                    "due_date_reference": date.fromisoformat(str(item["due_date_reference"])) if item.get("due_date_reference") else None,
                    "base_amount": FinancialTitleAdjustmentService._money(item.get("base_amount")),
                    "generated_amount": amount,
                    "settled_amount": FinancialTitleAdjustmentService._money(item.get("settled_amount")),
                    "open_amount": amount,
                    "rule_snapshot_json": dict(item.get("rule_snapshot_json") or {}),
                    "metadata_json": {
                        **dict(item.get("metadata_json") or {}),
                        "source": "financial_title_adjustment_service",
                        "simulation_base_amount": simulation.get("base_amount"),
                    },
                }
                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                    adjustment = existing
                else:
                    adjustment = FinancialTitleAdjustment(**payload)
                    db.session.add(adjustment)
                db.session.flush()
                if inherit_allocations:
                    for allocation in FinancialTitleAdjustmentAllocationService.build_default_allocations(
                        adjustment=adjustment,
                        schedule=schedule,
                    ):
                        db.session.add(allocation)
                persisted.append(adjustment)
            db.session.commit()
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            db.session.rollback()
            return None, f"Erro ao gerar ajustes do título financeiro: {str(exc)}"

        return {
            "financial_schedule_id": schedule_id,
            "company_id": company_id,
            "simulation": simulation,
            "adjustments": [item.to_dict() if hasattr(item, "to_dict") else dict(item.__dict__) for item in persisted],
            "count": len(persisted),
        }, None
