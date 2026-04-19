from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from models.financial import FinancialCorrectionIndex, FinancialDiscountRule


class FinancialTitleAmountService:
    """Serviço de domínio para calcular o valor atualizado de um Título Financeiro.

    Centraliza a regra de valor base, correção financeira e desconto para que
    relatórios, geração de baixa/lançamento e futuras rotinas usem a mesma fonte.
    """

    @staticmethod
    def calculate(
        *,
        company_id: int,
        template_amount: Any,
        metadata_json: Optional[Dict[str, Any]],
        due_date: Optional[date],
        reference_date: Optional[date] = None,
        correction_index_model: Any = None,
        discount_rule_model: Any = None,
    ) -> Dict[str, float]:
        template_decimal = Decimal(str(template_amount or 0))
        metadata = dict(metadata_json or {})
        correction_amount = Decimal("0")
        discount_amount = Decimal("0")
        base_date = reference_date or date.today()
        correction_index_model = correction_index_model or FinancialCorrectionIndex
        discount_rule_model = discount_rule_model or FinancialDiscountRule

        correction_index_id = metadata.get("correction_index_id")
        if correction_index_id and due_date:
            overdue_days = max((base_date - due_date).days, 0)
            if overdue_days > 0:
                correction = correction_index_model.query.filter(
                    correction_index_model.id == int(correction_index_id),
                    correction_index_model.company_id == company_id,
                    correction_index_model.deleted_at.is_(None),
                    correction_index_model.is_active.is_(True),
                ).first()
                if correction:
                    correction_metadata = dict(correction.metadata_json or {})
                    interest_rate = Decimal(str(correction_metadata.get("interest_rate") or 0))
                    penalty_rate = Decimal(str(correction_metadata.get("penalty_rate") or 0))
                    penalty_limit_rate = Decimal(str(correction_metadata.get("penalty_limit_rate") or 0))
                    interest_period = str(correction_metadata.get("interest_period") or "daily").strip().lower()
                    periods = Decimal(str(overdue_days / 30)) if interest_period == "monthly" else Decimal(overdue_days)
                    interest_amount = (template_decimal * (interest_rate / Decimal("100")) * periods) if interest_rate > 0 else Decimal("0")
                    effective_penalty_rate = penalty_rate
                    if penalty_limit_rate > 0:
                        effective_penalty_rate = min(effective_penalty_rate, penalty_limit_rate)
                    penalty_amount = (template_decimal * (effective_penalty_rate / Decimal("100"))) if effective_penalty_rate > 0 else Decimal("0")
                    correction_amount = interest_amount + penalty_amount

        discount_override = Decimal(str(metadata.get("discount_amount_override") or 0))
        if discount_override > 0:
            discount_amount = discount_override
        else:
            discount_rule_id = metadata.get("discount_rule_id")
            if discount_rule_id:
                discount_rule = discount_rule_model.query.filter(
                    discount_rule_model.id == int(discount_rule_id),
                    discount_rule_model.company_id == company_id,
                    discount_rule_model.deleted_at.is_(None),
                    discount_rule_model.is_active.is_(True),
                ).first()
                if discount_rule:
                    discount_metadata = dict(discount_rule.metadata_json or {})
                    discount_type = str(discount_metadata.get("discount_type") or "").strip().lower()
                    discount_value = Decimal(str(discount_metadata.get("value") or 0))
                    if discount_value > 0:
                        discount_amount = (
                            template_decimal * (discount_value / Decimal("100"))
                            if discount_type == "percentage"
                            else discount_value
                        )

        updated_amount = template_decimal + correction_amount - discount_amount
        return {
            "template_amount": float(template_decimal),
            "correction_amount": float(correction_amount.quantize(Decimal("0.01"))),
            "discount_amount": float(discount_amount.quantize(Decimal("0.01"))),
            "updated_amount": float(updated_amount.quantize(Decimal("0.01"))),
        }
