import logging
import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import current_app
from financial_domain import (
    FINANCIAL_TITLE_MEMORY_VERSION,
    SETTLEMENT_CORRECTION_COMPONENT_TYPES,
    build_financial_settlement_contract_payload,
    build_title_operational_state_metadata,
    resolve_title_settlement_state,
)
from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialCorrectionIndex,
    FinancialCounterparty,
    FinancialDiscountRule,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSchedule,
    FinancialSettlement,
    FinancialSettlementComponent,
    FinancialTitleAdjustment,
    FinancialTitleAdjustmentAllocation,
    FinancialTitleCalculationLog,
)
from models.financial_budget import FinancialBudgetContract, FinancialBudgetDocument, FinancialBudgetLine
from models.process import ProcessInstance, ProcessRoutine
from models.routine import Routine
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from schemas.financial import (
    FinancialAllocationBatchInput,
    FinancialAllocationInput,
    FinancialEntryCreateInput,
    FinancialEntryUpdateInput,
    FinancialSettlementInput,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_title_amount_service import FinancialTitleAmountService
from services.financial_title_balance_service import FinancialTitleBalanceService
from utils.permissions import is_administrator

logger = logging.getLogger(__name__)


class FinancialService:
    """Serviço determinístico do núcleo financeiro."""

    CORRECTION_COMPONENT_TYPES = set(SETTLEMENT_CORRECTION_COMPONENT_TYPES) | {"financial_correction"}
    DISCOUNT_COMPONENT_TYPES = {"discount"}

    @staticmethod
    def _money_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")

    @staticmethod
    def _money_float(value: Any) -> float:
        return float(FinancialService._money_decimal(value))

    @staticmethod
    def _is_direct_entry_linked_entry(entry: Optional[FinancialEntry], schedule: Optional[FinancialSchedule] = None) -> bool:
        if entry is None:
            return False
        entry_metadata = dict(getattr(entry, "metadata_json", {}) or {})
        if entry_metadata.get("direct_entry"):
            return True
        if schedule is not None:
            schedule_metadata = dict(getattr(schedule, "metadata_json", {}) or {})
            if schedule_metadata.get("direct_entry"):
                return True
        return False

    @staticmethod
    def _requires_whole_entry_delete(entry: Optional[FinancialEntry], schedule: Optional[FinancialSchedule] = None) -> bool:
        if entry is None:
            return False
        entry_metadata = dict(getattr(entry, "metadata_json", {}) or {})
        if str(entry_metadata.get("generate_target") or "").strip().lower() == "entry":
            return True
        return FinancialService._is_direct_entry_linked_entry(entry, schedule)

    @staticmethod
    def _resolve_linked_schedule(entry: Optional[FinancialEntry], company_id: int) -> Optional[FinancialSchedule]:
        if entry is None:
            return None
        schedule_id = getattr(entry, "financial_schedule_id", None)
        if not schedule_id:
            external_reference = str(getattr(entry, "external_reference", "") or "").strip()
            if external_reference.startswith("financial_schedule:"):
                raw_schedule_id = external_reference.split(":", 1)[1].strip()
                if raw_schedule_id.isdigit():
                    schedule_id = int(raw_schedule_id)
        if not schedule_id:
            return None
        return FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _normalize_component_kind(component_type: Optional[str]) -> str:
        normalized = str(component_type or "").strip().lower()
        if normalized in FinancialService.CORRECTION_COMPONENT_TYPES:
            return "financial_correction"
        if normalized in FinancialService.DISCOUNT_COMPONENT_TYPES:
            return "discount"
        return "principal"

    @staticmethod
    def _resolve_entry_principal_basis_amount(
        entry: Optional[FinancialEntry],
        *,
        schedule: Optional[FinancialSchedule] = None,
    ) -> Decimal:
        if entry is None:
            return FinancialService._money_decimal(getattr(schedule, "template_amount", None))

        metadata = dict(getattr(entry, "metadata_json", {}) or {})
        principal_amount = FinancialService._money_decimal(metadata.get("schedule_template_amount"))
        if principal_amount > Decimal("0"):
            return principal_amount

        schedule_amount = FinancialService._money_decimal(getattr(schedule, "template_amount", None))
        if schedule_amount > Decimal("0"):
            return schedule_amount

        return FinancialService._money_decimal(getattr(entry, "original_amount", None))

    @staticmethod
    def _resolve_schedule_adjustment_chart_account_id(
        *,
        schedule: Optional[FinancialSchedule],
        component_kind: str,
    ) -> Optional[int]:
        if schedule is None:
            return None

        metadata = dict(getattr(schedule, "metadata_json", {}) or {})
        normalized_kind = FinancialService._normalize_component_kind(component_kind)
        if normalized_kind == "discount":
            rule_id = metadata.get("discount_rule_id")
            if not rule_id:
                return None
            try:
                rule = FinancialDiscountRule.query.filter(
                    FinancialDiscountRule.company_id == schedule.company_id,
                    FinancialDiscountRule.id == int(rule_id),
                    FinancialDiscountRule.deleted_at.is_(None),
                ).first()
            except Exception:
                rule = None
            if rule is None:
                return None
            return rule.metadata_json.get("chart_account_id")

        rule_id = metadata.get("correction_index_id")
        if not rule_id:
            return None
        try:
            rule = FinancialCorrectionIndex.query.filter(
                FinancialCorrectionIndex.company_id == schedule.company_id,
                FinancialCorrectionIndex.id == int(rule_id),
                FinancialCorrectionIndex.deleted_at.is_(None),
            ).first()
        except Exception:
            rule = None
        if rule is None:
            return None
        return rule.metadata_json.get("chart_account_id")

    @staticmethod
    def _build_proportional_allocation_items(
        *,
        allocation_rows: Sequence[Dict[str, Any]],
        total_amount: float,
        total_basis: float,
        default_competence_date: Optional[Any] = None,
        default_due_date: Optional[Any] = None,
        component_kind: str,
        source: str,
        origin_adjustment_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if total_amount <= 0 or total_basis <= 0 or not allocation_rows:
            return []

        items: List[Dict[str, Any]] = []
        distributed_total = 0.0
        for index, row in enumerate(allocation_rows, start=1):
            basis_amount = abs(FinancialService._money_float(row.get("basis_amount")))
            proportional_amount = round((basis_amount / total_basis) * total_amount, 2)
            if index == len(allocation_rows):
                proportional_amount = round(total_amount - distributed_total, 2)
            distributed_total = round(distributed_total + proportional_amount, 2)
            row_metadata = dict(row.get("metadata_json") or {})
            items.append(
                {
                    "allocation_id": row.get("allocation_id"),
                    "chart_account_id": row.get("chart_account_id"),
                    "cost_center_id": row.get("cost_center_id"),
                    "activity_id": row.get("activity_id"),
                    "process_instance_id": row.get("process_instance_id"),
                    "routine_id": row.get("routine_id"),
                    "allocation_type": row.get("allocation_type"),
                    "percentage": row.get("percentage"),
                    "source_allocated_amount": round(basis_amount, 2),
                    "settled_allocated_amount": proportional_amount,
                    "notes": row.get("notes"),
                    "competence_date": default_competence_date,
                    "due_date": default_due_date,
                    "metadata_json": {
                        **row_metadata,
                        "component_kind": component_kind,
                        "source": source,
                        "origin_adjustment_id": origin_adjustment_id,
                    },
                }
            )
        return items

    @staticmethod
    def _build_settlement_component_payloads_for_breakdown(
        *,
        settlement: FinancialSettlement,
        component_kind: str,
        component_amount: Any = None,
        component_payloads: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        normalized_kind = FinancialService._normalize_component_kind(component_kind)
        normalized_payloads: List[Dict[str, Any]] = []
        for payload in component_payloads or []:
            item = dict(payload or {})
            if FinancialService._normalize_component_kind(item.get("component_type")) != normalized_kind:
                continue
            amount = abs(FinancialService._money_float(item.get("amount")))
            if amount <= 0:
                continue
            normalized_payloads.append(
                {
                    "amount": amount,
                    "competence_date": item.get("competence_date"),
                    "due_date": item.get("due_date"),
                    "origin_adjustment_id": item.get("origin_adjustment_id"),
                    "metadata_json": dict(item.get("metadata_json") or {}),
                }
            )

        if normalized_payloads:
            return normalized_payloads

        fallback_amount = abs(FinancialService._money_float(component_amount))
        if fallback_amount <= 0:
            return []
        settlement_date = getattr(settlement, "settlement_date", None)
        default_competence_date = settlement_date if normalized_kind in {"financial_correction", "discount"} else None
        default_due_date = settlement_date if normalized_kind in {"financial_correction", "discount"} else None
        return [
            {
                "amount": fallback_amount,
                "competence_date": default_competence_date,
                "due_date": default_due_date,
                "origin_adjustment_id": None,
                "metadata_json": {},
            }
        ]

    @staticmethod
    def _build_serialized_settlement_component_payloads(
        *,
        settlement: FinancialSettlement,
        settlement_components: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        normalized_components = [dict(item or {}) for item in (settlement_components or []) if item is not None]
        if normalized_components:
            return normalized_components

        settlement_date = getattr(settlement, "settlement_date", None)
        payloads: List[Dict[str, Any]] = []
        amount_map = (
            ("principal", getattr(settlement, "principal_amount", None)),
            ("interest", getattr(settlement, "interest_amount", None)),
            ("fine", getattr(settlement, "penalty_amount", None)),
            ("discount", getattr(settlement, "discount_amount", None)),
            ("manual_adjustment", FinancialService._money_decimal(getattr(settlement, "fee_amount", None)) + FinancialService._money_decimal(getattr(settlement, "other_adjustments_amount", None))),
        )
        for component_type, raw_amount in amount_map:
            amount = abs(FinancialService._money_float(raw_amount))
            if amount <= 0:
                continue
            normalized_kind = FinancialService._normalize_component_kind(component_type)
            payloads.append(
                {
                    "component_type": component_type,
                    "amount": amount,
                    "competence_date": settlement_date if normalized_kind in {"financial_correction", "discount"} else None,
                    "due_date": settlement_date if normalized_kind in {"financial_correction", "discount"} else None,
                    "origin_adjustment_id": None,
                    "metadata_json": {},
                }
            )
        return payloads

    @staticmethod
    def _rebuild_settlement_allocation_breakdown(
        *,
        settlement: FinancialSettlement,
        entry: Optional[FinancialEntry],
        schedule: Optional[FinancialSchedule],
        settlement_components: Optional[Sequence[Dict[str, Any]]] = None,
        existing_breakdown: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if settlement is None or entry is None:
            return dict(existing_breakdown or {}) or None

        component_payloads = FinancialService._build_serialized_settlement_component_payloads(
            settlement=settlement,
            settlement_components=settlement_components,
        )
        rebuilt_breakdown = dict(existing_breakdown or {})

        principal_breakdown = FinancialService._build_principal_allocation_breakdown(
            entry=entry,
            settlement=settlement,
        )
        if principal_breakdown.get("items"):
            rebuilt_breakdown["principal"] = principal_breakdown

        correction_breakdown = FinancialService._build_schedule_component_allocation_breakdown(
            schedule=schedule,
            settlement=settlement,
            component_kind="financial_correction",
            component_payloads=component_payloads,
        )
        if correction_breakdown.get("items"):
            rebuilt_breakdown["financial_correction"] = correction_breakdown

        discount_breakdown = FinancialService._build_schedule_component_allocation_breakdown(
            schedule=schedule,
            settlement=settlement,
            component_kind="discount",
            component_payloads=component_payloads,
        )
        if discount_breakdown.get("items"):
            rebuilt_breakdown["discount"] = discount_breakdown

        return rebuilt_breakdown or None

    @staticmethod
    def _build_settlement_actor_payload(
        settlement: FinancialSettlement,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = dict(metadata_json or getattr(settlement, "metadata_json", {}) or {})
        audit = dict(metadata.get("audit") or {})
        actor_metadata = dict(audit.get("actor") or metadata.get("actor") or {})
        actor_payload = {
            "user_id": actor_metadata.get("user_id", getattr(settlement, "created_by_user_id", None)),
            "employee_id": actor_metadata.get("employee_id", getattr(settlement, "created_by_employee_id", None)),
            "agent": actor_metadata.get("agent", getattr(settlement, "created_by_agent", None)),
            "user_name": actor_metadata.get("user_name") or actor_metadata.get("name") or metadata.get("actor_name"),
            "channel": audit.get("channel") or metadata.get("source_channel") or "app32",
        }
        return {key: value for key, value in actor_payload.items() if value not in (None, "", [], {})}

    @staticmethod
    def _build_settlement_component_audit_payload(
        *,
        component_payloads: Optional[Sequence[Dict[str, Any]]],
        current_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        totals_by_type: Dict[str, float] = {}
        sources: List[str] = []
        origin_adjustment_ids: List[int] = []

        for component_payload in component_payloads or []:
            component = dict(component_payload or {})
            component_type = str(component.get("component_type") or "unknown").strip().lower()
            amount = FinancialService._money_float(component.get("amount"))
            totals_by_type[component_type] = round(totals_by_type.get(component_type, 0.0) + amount, 2)
            source = str(component.get("source") or "system").strip().lower() or "system"
            if source and source not in sources:
                sources.append(source)
            origin_adjustment_id = component.get("origin_adjustment_id")
            if origin_adjustment_id is not None:
                try:
                    normalized_origin_adjustment_id = int(origin_adjustment_id)
                except (TypeError, ValueError):
                    normalized_origin_adjustment_id = None
                if normalized_origin_adjustment_id is not None and normalized_origin_adjustment_id not in origin_adjustment_ids:
                    origin_adjustment_ids.append(normalized_origin_adjustment_id)
            items.append(
                {
                    "component_type": component_type,
                    "amount": amount,
                    "competence_date": component.get("competence_date").isoformat() if hasattr(component.get("competence_date"), "isoformat") else component.get("competence_date"),
                    "due_date": component.get("due_date").isoformat() if hasattr(component.get("due_date"), "isoformat") else component.get("due_date"),
                    "source": source,
                    "origin_adjustment_id": origin_adjustment_id,
                    "metadata_json": dict(component.get("metadata_json") or {}),
                }
            )

        normalized_current = dict(current_block or {})
        if not items:
            fallback_components = [
                ("principal", normalized_current.get("principal_settled")),
                ("financial_correction", normalized_current.get("financial_correction")),
                ("discount", normalized_current.get("discount")),
            ]
            for component_type, raw_amount in fallback_components:
                amount = FinancialService._money_float(raw_amount)
                if amount <= 0:
                    continue
                totals_by_type[component_type] = round(totals_by_type.get(component_type, 0.0) + amount, 2)
                items.append(
                    {
                        "component_type": component_type,
                        "amount": amount,
                        "competence_date": None,
                        "due_date": None,
                        "source": "snapshot",
                        "origin_adjustment_id": None,
                        "metadata_json": {},
                    }
                )
                if "snapshot" not in sources:
                    sources.append("snapshot")

        gross_amount = FinancialService._money_float(normalized_current.get("gross_amount"))
        if gross_amount <= 0:
            gross_amount = max(
                totals_by_type.get("principal", 0.0)
                + sum(
                    amount
                    for component_type, amount in totals_by_type.items()
                    if component_type not in {"principal", "discount"}
                )
                - totals_by_type.get("discount", 0.0),
                0.0,
            )

        return {
            "count": len(items),
            "gross_amount": round(gross_amount, 2),
            "principal": round(totals_by_type.get("principal", 0.0), 2),
            "financial_correction": round(
                sum(
                    amount
                    for component_type, amount in totals_by_type.items()
                    if component_type in set(SETTLEMENT_CORRECTION_COMPONENT_TYPES) or component_type == "financial_correction"
                ),
                2,
            ),
            "discount": round(totals_by_type.get("discount", 0.0), 2),
            "by_type": totals_by_type,
            "sources": sources,
            "origin_adjustment_ids": origin_adjustment_ids,
            "items": items,
        }

    @staticmethod
    def _build_settlement_evidence_payload(
        *,
        entry: FinancialEntry,
        settlement: FinancialSettlement,
        metadata_json: Optional[Dict[str, Any]] = None,
        component_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = dict(metadata_json or getattr(settlement, "metadata_json", {}) or {})
        attachments = list(metadata.get("attachments") or [])
        bank_account_name = None
        bank_account_id = getattr(settlement, "bank_account_id", None)
        if bank_account_id is not None:
            try:
                bank_account = FinancialBankAccount.query.filter(
                    FinancialBankAccount.company_id == settlement.company_id,
                    FinancialBankAccount.id == bank_account_id,
                    FinancialBankAccount.deleted_at.is_(None),
                ).first()
                bank_account_name = getattr(bank_account, "name", None)
            except Exception:
                bank_account_name = None

        evidence_payload = {
            "settlement_code": getattr(settlement, "settlement_code", None),
            "settlement_date": settlement.settlement_date.isoformat() if getattr(settlement, "settlement_date", None) else None,
            "bank_account_id": bank_account_id,
            "bank_account_name": bank_account_name,
            "entry_id": getattr(entry, "id", None),
            "entry_code": getattr(entry, "entry_code", None),
            "entry_status_before_commit": getattr(entry, "status", None),
            "external_reference": getattr(settlement, "external_reference", None),
            "notes": getattr(settlement, "notes", None),
            "history": metadata.get("history") or getattr(settlement, "notes", None),
            "payment_method": {
                "id": metadata.get("payment_method_id"),
                "label": metadata.get("payment_method_label"),
            },
            "attachments_count": len(attachments),
            "attachments": [
                {
                    "id": attachment.get("id"),
                    "name": attachment.get("name"),
                    "content_type": attachment.get("content_type"),
                    "size": attachment.get("size"),
                }
                for attachment in attachments
            ],
            "component_count": int((component_summary or {}).get("count", 0) or 0),
            "gross_amount": FinancialService._money_float(getattr(settlement, "gross_amount", None) or getattr(settlement, "net_amount", None) or 0),
        }
        if not evidence_payload["payment_method"]["id"] and not evidence_payload["payment_method"]["label"]:
            evidence_payload.pop("payment_method", None)
        return {key: value for key, value in evidence_payload.items() if value not in (None, "")}

    @staticmethod
    def get_signed_amount(amount: Decimal | float | int | None, movement_nature: str | None) -> float:
        normalized_amount = Decimal(str(amount or 0))
        absolute_amount = abs(normalized_amount)
        signed_amount = -absolute_amount if movement_nature == "debit" else absolute_amount
        return float(signed_amount)

    @staticmethod
    def get_amount_direction(movement_nature: str | None) -> str:
        return "outflow" if movement_nature == "debit" else "inflow"

    @staticmethod
    def enrich_amount_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        movement_nature = payload.get("movement_nature")
        signed_amount = FinancialService.get_signed_amount(payload.get("original_amount"), movement_nature)
        payload["signed_amount"] = signed_amount
        payload["amount_direction"] = FinancialService.get_amount_direction(movement_nature)
        payload["display_variant"] = "negative" if signed_amount < 0 else "positive"
        payload["is_reconciled"] = False
        return payload

    @staticmethod
    def _has_reconciled_settlement(settlements: Sequence[FinancialSettlement]) -> bool:
        for settlement in settlements or []:
            if getattr(settlement, "deleted_at", None) is not None:
                continue
            if str(getattr(settlement, "settlement_status", "") or "").strip().lower() == "cancelled":
                continue
            if str(getattr(settlement, "reconciliation_status", "") or "").strip().lower() in {"matched", "reconciled"}:
                return True
        return False

    @staticmethod
    def is_entry_reconciled(
        entry: FinancialEntry,
        *,
        settlements: Optional[Sequence[FinancialSettlement]] = None,
    ) -> bool:
        active_settlements = list(settlements or [])
        if not active_settlements:
            active_settlements = (
                FinancialSettlement.query.filter(
                    FinancialSettlement.company_id == entry.company_id,
                    FinancialSettlement.financial_entry_id == entry.id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                ).all()
            )
        if not FinancialService._has_reconciled_settlement(active_settlements):
            return False

        settled_principal = sum(
            FinancialService._money_decimal(getattr(settlement, "principal_amount", None))
            for settlement in active_settlements
            if getattr(settlement, "deleted_at", None) is None
            and str(getattr(settlement, "settlement_status", "") or "").strip().lower() != "cancelled"
        )
        original_amount = FinancialService._money_decimal(getattr(entry, "original_amount", None))
        remaining_amount = original_amount - settled_principal
        return remaining_amount <= Decimal("0.01")

    @staticmethod
    def set_entry_reconciliation_state(
        *,
        entry: FinancialEntry,
        reconciled: bool,
        actor_reason: Optional[str] = None,
    ) -> None:
        metadata = dict(entry.metadata_json or {})
        metadata.pop("reconciled", None)
        metadata["reconciliation_updated_reason"] = actor_reason
        entry.metadata_json = metadata

    @staticmethod
    def serialize_entry(entry: FinancialEntry, *, include_children: bool = True) -> Dict[str, Any]:
        payload = FinancialService.enrich_amount_payload(entry.to_dict())
        payload["attachments"] = list(dict(payload.get("metadata_json") or {}).get("attachments") or [])
        if not include_children:
            return payload

        payload["allocations"] = [
            allocation.to_dict()
            for allocation in FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.company_id == entry.company_id,
                FinancialEntryAllocation.financial_entry_id == entry.id,
                FinancialEntryAllocation.deleted_at.is_(None),
            )
            .order_by(FinancialEntryAllocation.id.asc())
            .all()
        ]
        settlements = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
            )
            .order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc())
            .all()
        )
        payload["is_reconciled"] = FinancialService.is_entry_reconciled(entry, settlements=settlements)
        schedule = None
        if getattr(entry, "financial_schedule_id", None):
            schedule = FinancialSchedule.query.filter(
                FinancialSchedule.id == entry.financial_schedule_id,
                FinancialSchedule.company_id == entry.company_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()
        payload["settlements"] = FinancialService.serialize_settlement_list(
            settlements,
            include_components=True,
            entry_by_id={entry.id: entry},
            schedule_by_id={schedule.id: schedule} if schedule else None,
        )
        return payload

    @staticmethod
    def serialize_settlement(
        settlement: FinancialSettlement,
        *,
        include_components: bool = True,
        entry: Optional[FinancialEntry] = None,
        schedule: Optional[FinancialSchedule] = None,
        settlement_components: Optional[Sequence[FinancialSettlementComponent]] = None,
    ) -> Dict[str, Any]:
        if settlement is None:
            return {}

        payload = settlement.to_dict() if hasattr(settlement, "to_dict") else dict(settlement or {})
        if entry is None and getattr(settlement, "financial_entry_id", None):
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == settlement.financial_entry_id,
                FinancialEntry.company_id == settlement.company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
        if schedule is None and entry is not None and getattr(entry, "financial_schedule_id", None):
            schedule = FinancialSchedule.query.filter(
                FinancialSchedule.id == entry.financial_schedule_id,
                FinancialSchedule.company_id == entry.company_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()

        serialized_components: List[Dict[str, Any]] = []
        if include_components:
            components = settlement_components
            if components is None and getattr(settlement, "id", None) is not None:
                components = (
                    FinancialSettlementComponent.query.filter(
                        FinancialSettlementComponent.company_id == settlement.company_id,
                        FinancialSettlementComponent.financial_settlement_id == settlement.id,
                    )
                    .order_by(FinancialSettlementComponent.id.asc())
                    .all()
                )
            serialized_components = [
                component.to_dict() if hasattr(component, "to_dict") else dict(component or {})
                for component in (components or [])
            ]

        existing_breakdown = dict((payload.get("metadata_json") or {}).get("settlement_allocation_breakdown") or {})
        rebuilt_breakdown = FinancialService._rebuild_settlement_allocation_breakdown(
            settlement=settlement,
            entry=entry,
            schedule=schedule,
            settlement_components=serialized_components,
            existing_breakdown=existing_breakdown,
        )
        if rebuilt_breakdown:
            payload["metadata_json"] = {
                **dict(payload.get("metadata_json") or {}),
                "settlement_allocation_breakdown": rebuilt_breakdown,
            }

        entry_payload = None
        if entry is not None:
            entry_payload = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry or {})

        schedule_payload = None
        if schedule is not None:
            schedule_payload = schedule.to_dict() if hasattr(schedule, "to_dict") else dict(schedule or {})

        return build_financial_settlement_contract_payload(
            payload,
            entry_payload=entry_payload,
            schedule_payload=schedule_payload,
            settlement_components=serialized_components,
        )

    @staticmethod
    def serialize_settlement_list(
        settlements: Sequence[FinancialSettlement],
        *,
        include_components: bool = True,
        entry_by_id: Optional[Dict[int, FinancialEntry]] = None,
        schedule_by_id: Optional[Dict[int, FinancialSchedule]] = None,
    ) -> List[Dict[str, Any]]:
        if not settlements:
            return []

        normalized_settlements = [item for item in settlements if item is not None]
        if not normalized_settlements:
            return []

        settlement_ids = [int(item.id) for item in normalized_settlements if getattr(item, "id", None) is not None]
        company_ids = {int(item.company_id) for item in normalized_settlements if getattr(item, "company_id", None) is not None}
        entry_ids = {int(item.financial_entry_id) for item in normalized_settlements if getattr(item, "financial_entry_id", None) is not None}

        resolved_entries = dict(entry_by_id or {})
        missing_entry_ids = [entry_id for entry_id in entry_ids if entry_id not in resolved_entries]
        if missing_entry_ids:
            for entry in FinancialEntry.query.filter(
                FinancialEntry.company_id.in_(company_ids),
                FinancialEntry.id.in_(missing_entry_ids),
                FinancialEntry.deleted_at.is_(None),
            ).all():
                resolved_entries[int(entry.id)] = entry

        resolved_schedules = dict(schedule_by_id or {})
        schedule_ids = {
            int(entry.financial_schedule_id)
            for entry in resolved_entries.values()
            if getattr(entry, "financial_schedule_id", None) is not None and int(entry.financial_schedule_id) not in resolved_schedules
        }
        if schedule_ids:
            for schedule in FinancialSchedule.query.filter(
                FinancialSchedule.company_id.in_(company_ids),
                FinancialSchedule.id.in_(schedule_ids),
                FinancialSchedule.deleted_at.is_(None),
            ).all():
                resolved_schedules[int(schedule.id)] = schedule

        components_by_settlement: Dict[int, List[FinancialSettlementComponent]] = {}
        if include_components and settlement_ids:
            components = (
                FinancialSettlementComponent.query.filter(
                    FinancialSettlementComponent.company_id.in_(company_ids),
                    FinancialSettlementComponent.financial_settlement_id.in_(settlement_ids),
                )
                .order_by(
                    FinancialSettlementComponent.financial_settlement_id.asc(),
                    FinancialSettlementComponent.id.asc(),
                )
                .all()
            )
            for component in components:
                settlement_id = int(getattr(component, "financial_settlement_id", 0) or 0)
                components_by_settlement.setdefault(settlement_id, []).append(component)

        return [
            FinancialService.serialize_settlement(
                settlement,
                include_components=include_components,
                entry=resolved_entries.get(int(getattr(settlement, "financial_entry_id", 0) or 0)),
                schedule=resolved_schedules.get(
                    int(getattr(resolved_entries.get(int(getattr(settlement, "financial_entry_id", 0) or 0)), "financial_schedule_id", 0) or 0)
                ),
                settlement_components=components_by_settlement.get(int(getattr(settlement, "id", 0) or 0)),
            )
            for settlement in normalized_settlements
        ]

    @staticmethod
    def serialize_entry_list(entries: Sequence[FinancialEntry]) -> List[Dict[str, Any]]:
        serialized_items = [FinancialService.enrich_amount_payload(entry.to_dict()) for entry in entries]
        if not serialized_items:
            return []

        entry_ids = [int(item["id"]) for item in serialized_items]
        company_ids = {int(item["company_id"]) for item in serialized_items if item.get("company_id") is not None}

        settlements = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id.in_(company_ids),
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .order_by(
                FinancialSettlement.financial_entry_id.asc(),
                FinancialSettlement.settlement_date.desc(),
                FinancialSettlement.id.desc(),
            )
            .all()
        )

        settlement_summary_by_entry: Dict[int, Dict[str, Any]] = {}
        related_bank_account_ids = {
            int(item["bank_account_id"])
            for item in serialized_items
            if item.get("bank_account_id") is not None
        }
        related_counterparty_ids = {
            int(item["counterparty_id"])
            for item in serialized_items
            if item.get("counterparty_id") is not None
        }

        for settlement in settlements:
            if settlement.bank_account_id is not None:
                related_bank_account_ids.add(int(settlement.bank_account_id))
            summary = settlement_summary_by_entry.setdefault(
                int(settlement.financial_entry_id),
                {
                    "settled_principal_amount": 0.0,
                    "settled_net_amount": 0.0,
                    "settlement_count": 0,
                    "latest_settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                    "latest_settlement_code": settlement.settlement_code,
                    "latest_settlement_bank_account_id": settlement.bank_account_id,
                },
            )
            summary["settled_principal_amount"] += float(settlement.principal_amount or 0)
            summary["settled_net_amount"] += float(getattr(settlement, "gross_amount", None) or settlement.net_amount or 0)
            summary["settlement_count"] += 1
            if str(getattr(settlement, "reconciliation_status", "") or "").strip().lower() in {"matched", "reconciled"}:
                summary["has_reconciled_settlement"] = True

        bank_accounts = {
            item.id: item
            for item in FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id.in_(company_ids),
                FinancialBankAccount.id.in_(related_bank_account_ids or {-1}),
                FinancialBankAccount.deleted_at.is_(None),
            ).all()
        }
        counterparties = {
            item.id: item
            for item in FinancialCounterparty.query.filter(
                FinancialCounterparty.company_id.in_(company_ids),
                FinancialCounterparty.id.in_(related_counterparty_ids or {-1}),
                FinancialCounterparty.deleted_at.is_(None),
            ).all()
        }

        for item in serialized_items:
            entry_id = int(item["id"])
            counterparty = counterparties.get(item.get("counterparty_id"))
            entry_bank_account = bank_accounts.get(item.get("bank_account_id"))
            settlement_summary = settlement_summary_by_entry.get(entry_id, {})
            settlement_bank_account = bank_accounts.get(settlement_summary.get("latest_settlement_bank_account_id"))
            external_reference = str(item.get("external_reference") or "")
            schedule_id = None
            if external_reference.startswith("financial_schedule:"):
                raw_schedule_id = external_reference.split(":", 1)[1].strip()
                if raw_schedule_id.isdigit():
                    schedule_id = int(raw_schedule_id)

            item["display_code"] = str(entry_id)
            item["schedule_id"] = schedule_id
            item["schedule_url"] = f"/financial/schedules/{schedule_id}" if schedule_id else None
            item["counterparty_name"] = counterparty.name if counterparty else None
            item["entry_bank_account_name"] = entry_bank_account.name if entry_bank_account else None
            item["settlement_bank_account_name"] = (
                settlement_bank_account.name if settlement_bank_account else None
            )
            item["bank_account_name"] = (
                item["settlement_bank_account_name"]
                or item["entry_bank_account_name"]
            )
            item["settled_principal_amount"] = float(settlement_summary.get("settled_principal_amount", 0) or 0)
            item["settled_amount"] = float(settlement_summary.get("settled_net_amount", 0) or 0)
            item["settled_signed_amount"] = FinancialService.get_signed_amount(
                item["settled_amount"],
                item.get("movement_nature"),
            )
            item["latest_settlement_date"] = settlement_summary.get("latest_settlement_date")
            item["latest_settlement_code"] = settlement_summary.get("latest_settlement_code")
            item["settlement_count"] = int(settlement_summary.get("settlement_count", 0) or 0)
            item["is_reconciled"] = bool(
                settlement_summary.get("has_reconciled_settlement")
                and (
                    FinancialService._money_decimal(item.get("original_amount"))
                    - FinancialService._money_decimal(item.get("settled_principal_amount"))
                ) <= Decimal("0.01")
            )

        return serialized_items

    @staticmethod
    def list_entries(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        status: Optional[str] = None,
        entry_type: Optional[str] = None,
        movement_nature: Optional[str] = None,
        origin_type: Optional[str] = None,
        activity_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        competence_date_from: Optional[date] = None,
        competence_date_to: Optional[date] = None,
        settlement_date_from: Optional[date] = None,
        settlement_date_to: Optional[date] = None,
        counterparty_id: Optional[int] = None,
        counterparty_query: Optional[str] = None,
        bank_query: Optional[str] = None,
        bank_account_id: Optional[int] = None,
        bank_account_query: Optional[str] = None,
        document_number: Optional[str] = None,
        settlement_code: Optional[str] = None,
        description_query: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        )

        if status:
            query = query.filter(FinancialEntry.status == status)
        if entry_type:
            query = query.filter(FinancialEntry.entry_type == entry_type)
        if movement_nature:
            query = query.filter(FinancialEntry.movement_nature == movement_nature)
        if origin_type:
            query = query.filter(FinancialEntry.origin_type == origin_type)
        if activity_id:
            query = query.filter(FinancialEntry.activity_id == activity_id)
        if process_instance_id:
            query = query.filter(FinancialEntry.process_instance_id == process_instance_id)
        if due_date_from:
            query = query.filter(FinancialEntry.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialEntry.due_date <= due_date_to)
        if competence_date_from:
            query = query.filter(FinancialEntry.competence_date >= competence_date_from)
        if competence_date_to:
            query = query.filter(FinancialEntry.competence_date <= competence_date_to)
        if counterparty_id:
            query = query.filter(FinancialEntry.counterparty_id == counterparty_id)
        if document_number:
            document_pattern = f"%{document_number.strip()}%"
            query = query.filter(
                or_(
                    FinancialEntry.document_number.ilike(document_pattern),
                    FinancialEntry.entry_code.ilike(document_pattern),
                )
            )
        if description_query:
            description_pattern = f"%{description_query.strip()}%"
            query = query.filter(
                or_(
                    FinancialEntry.description.ilike(description_pattern),
                    FinancialEntry.memo.ilike(description_pattern),
                )
            )
        if counterparty_query:
            counterparty_pattern = f"%{counterparty_query.strip()}%"
            counterparty_match = (
                db.session.query(FinancialCounterparty.id)
                .filter(
                    FinancialCounterparty.company_id == company_id,
                    FinancialCounterparty.id == FinancialEntry.counterparty_id,
                    FinancialCounterparty.deleted_at.is_(None),
                    or_(
                        FinancialCounterparty.name.ilike(counterparty_pattern),
                        FinancialCounterparty.legal_name.ilike(counterparty_pattern),
                        FinancialCounterparty.document_number.ilike(counterparty_pattern),
                    ),
                )
                .exists()
            )
            query = query.filter(counterparty_match)
        if bank_account_id:
            entry_bank_exact_match = FinancialEntry.bank_account_id == bank_account_id
            settlement_bank_exact_match = (
                db.session.query(FinancialSettlement.id)
                .filter(
                    FinancialSettlement.company_id == company_id,
                    FinancialSettlement.financial_entry_id == FinancialEntry.id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                    FinancialSettlement.bank_account_id == bank_account_id,
                )
                .exists()
            )
            query = query.filter(or_(entry_bank_exact_match, settlement_bank_exact_match))
        if bank_query or bank_account_query:
            bank_terms = [term.strip() for term in (bank_query, bank_account_query) if str(term or "").strip()]
            bank_filters = []
            for term in bank_terms:
                pattern = f"%{term}%"
                bank_filters.extend(
                    [
                        FinancialBankAccount.name.ilike(pattern),
                        FinancialBankAccount.bank_name.ilike(pattern),
                        FinancialBankAccount.account_number.ilike(pattern),
                        FinancialBankAccount.branch_number.ilike(pattern),
                    ]
                )
            entry_bank_match = (
                db.session.query(FinancialBankAccount.id)
                .filter(
                    FinancialBankAccount.company_id == company_id,
                    FinancialBankAccount.id == FinancialEntry.bank_account_id,
                    FinancialBankAccount.deleted_at.is_(None),
                    or_(*bank_filters),
                )
                .exists()
            )
            settlement_bank_match = (
                db.session.query(FinancialSettlement.id)
                .join(
                    FinancialBankAccount,
                    FinancialBankAccount.id == FinancialSettlement.bank_account_id,
                )
                .filter(
                    FinancialSettlement.company_id == company_id,
                    FinancialSettlement.financial_entry_id == FinancialEntry.id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                    FinancialBankAccount.company_id == company_id,
                    FinancialBankAccount.deleted_at.is_(None),
                    or_(*bank_filters),
                )
                .exists()
            )
            query = query.filter(or_(entry_bank_match, settlement_bank_match))
        if settlement_date_from or settlement_date_to or settlement_code:
            settlement_filters = [
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id == FinancialEntry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            ]
            if settlement_date_from:
                settlement_filters.append(FinancialSettlement.settlement_date >= settlement_date_from)
            if settlement_date_to:
                settlement_filters.append(FinancialSettlement.settlement_date <= settlement_date_to)
            if settlement_code:
                settlement_filters.append(FinancialSettlement.settlement_code.ilike(f"%{settlement_code.strip()}%"))
            settlement_match = db.session.query(FinancialSettlement.id).filter(*settlement_filters).exists()
            query = query.filter(settlement_match)

        entries = query.order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).all()
        return FinancialService.serialize_entry_list(entries), None

    @staticmethod
    def get_entry(
        *,
        entry_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        return FinancialService.serialize_entry(entry), None

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
    def _validate_operational_links(company_id: int, activity_id: Optional[int], process_instance_id: Optional[int], routine_id: Optional[int]) -> Optional[str]:
        if activity_id:
            activity = ProcessRoutine.query.filter(
                ProcessRoutine.id == activity_id,
                ProcessRoutine.company_id == company_id,
            ).first()
            if not activity:
                return "Atividade associada não encontrada no escopo da empresa."

        if process_instance_id:
            instance = ProcessInstance.query.filter(
                ProcessInstance.id == process_instance_id,
                ProcessInstance.company_id == company_id,
            ).first()
            if not instance:
                return "Instância associada não encontrada no escopo da empresa."

        if routine_id:
            routine = Routine.query.filter(
                Routine.id == routine_id,
                Routine.company_id == company_id,
            ).first()
            if not routine:
                return "Rotina associada não encontrada no escopo da empresa."

        return None

    @staticmethod
    def _merge_budget_metadata(
        metadata_json: Optional[Dict[str, Any]],
        budget_links: Optional[Dict[str, Optional[int]]],
    ) -> Dict[str, Any]:
        metadata = dict(metadata_json or {})
        for key in ("budget_line_id", "budget_contract_id", "budget_document_id"):
            value = (budget_links or {}).get(key)
            if value is None:
                metadata.pop(key, None)
                continue
            metadata[key] = value
        return metadata

    @staticmethod
    def _resolve_budget_links(
        *,
        company_id: int,
        budget_line_id: Optional[int],
        budget_contract_id: Optional[int],
        budget_document_id: Optional[int],
    ) -> Tuple[Optional[Dict[str, Optional[int]]], Optional[str]]:
        def _get_line(line_id: Optional[int]) -> Optional[FinancialBudgetLine]:
            if not line_id:
                return None
            return FinancialBudgetLine.query.filter(
                FinancialBudgetLine.id == int(line_id),
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.deleted_at.is_(None),
            ).first()

        def _get_contract(contract_id: Optional[int]) -> Optional[FinancialBudgetContract]:
            if not contract_id:
                return None
            return FinancialBudgetContract.query.filter(
                FinancialBudgetContract.id == int(contract_id),
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.deleted_at.is_(None),
            ).first()

        def _get_document(document_id: Optional[int]) -> Optional[FinancialBudgetDocument]:
            if not document_id:
                return None
            return FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.id == int(document_id),
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
            ).first()

        line = _get_line(budget_line_id)
        if budget_line_id and not line:
            return None, "Verba orçamentária não encontrada no escopo da empresa."

        contract = _get_contract(budget_contract_id)
        if budget_contract_id and not contract:
            return None, "Contrato orçamentário não encontrado no escopo da empresa."
        if contract:
            if line and contract.budget_line_id != line.id:
                return None, "Contrato orçamentário não pertence à verba informada."
            if not line:
                line = _get_line(contract.budget_line_id)
                if not line:
                    return None, "Verba orçamentária vinculada ao contrato não encontrada no escopo da empresa."

        document = _get_document(budget_document_id)
        if budget_document_id and not document:
            return None, "NF/equivalente orçamentária não encontrada no escopo da empresa."
        if document:
            if contract and document.budget_contract_id != contract.id:
                return None, "NF/equivalente não pertence ao contrato informado."
            if not contract:
                contract = _get_contract(document.budget_contract_id)
                if not contract:
                    return None, "Contrato orçamentário vinculado à NF/equivalente não encontrado no escopo da empresa."
            if line and contract.budget_line_id != line.id:
                return None, "NF/equivalente não pertence à verba informada."
            if not line:
                line = _get_line(contract.budget_line_id)
                if not line:
                    return None, "Verba orçamentária vinculada à NF/equivalente não encontrada no escopo da empresa."

        return {
            "budget_line_id": line.id if line else None,
            "budget_contract_id": contract.id if contract else None,
            "budget_document_id": document.id if document else None,
        }, None

    @staticmethod
    def create_entry(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialEntry], Optional[str]]:
        try:
            data = FinancialEntryCreateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para lançamento financeiro: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        link_error = FinancialService._validate_operational_links(
            company_id=data.company_id,
            activity_id=data.activity_id,
            process_instance_id=data.process_instance_id,
            routine_id=data.routine_id,
        )
        if link_error:
            return None, link_error

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            counterparty_id=data.counterparty_id,
        )
        if reference_error:
            return None, reference_error

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=data.company_id,
            budget_line_id=getattr(data, "budget_line_id", None),
            budget_contract_id=getattr(data, "budget_contract_id", None),
            budget_document_id=getattr(data, "budget_document_id", None),
        )
        if budget_error:
            return None, budget_error

        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.entry_code == data.entry_code,
        ).first()
        if existing:
            return None, f"Já existe lançamento com código {data.entry_code} para esta empresa."

        try:
            normalized = data.model_dump()
            normalized.update(budget_links or {})
            normalized["metadata_json"] = FinancialService._merge_budget_metadata(
                normalized.get("metadata_json"),
                budget_links,
            )
            entry = FinancialEntry(**normalized)
            db.session.add(entry)
            db.session.commit()
            return entry, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar lançamento financeiro")
            return None, f"Erro ao criar lançamento financeiro: {str(exc)}"

    @staticmethod
    def update_entry(
        *,
        entry_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialEntry], Optional[str]]:
        try:
            data = FinancialEntryUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização do lançamento: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=company_id, entry=entry)
        if active_bordero:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}."

        merged = data.model_dump(exclude_unset=True)
        if "entry_code" in merged:
            if merged["entry_code"] != entry.entry_code:
                return None, "O código do lançamento não pode ser alterado após a criação."
            merged.pop("entry_code", None)
        unlock_reconciliation = bool(merged.pop("unlock_reconciliation", False))
        requested_reconciled_state = merged.pop("reconciled", None)
        unlock_reason = merged.pop("reconciliation_unlock_reason", None)

        if FinancialService.is_entry_reconciled(entry):
            if unlock_reconciliation or requested_reconciled_state is False:
                if not is_administrator(company_id):
                    return None, (
                        "Lançamento conciliado exige demarcação por usuário com hierarquia administrativa."
                    )
                FinancialService.set_entry_reconciliation_state(
                    entry=entry,
                    reconciled=False,
                    actor_reason=unlock_reason or "Demarcação manual de conciliação.",
                )
            else:
                return None, (
                    "Lançamento conciliado está protegido. "
                    "Para alterar, um administrador deve demarcar a opção de conciliado."
                )

        activity_id = merged.get("activity_id", entry.activity_id)
        process_instance_id = merged.get("process_instance_id", entry.process_instance_id)
        routine_id = merged.get("routine_id", entry.routine_id)

        link_error = FinancialService._validate_operational_links(
            company_id=company_id,
            activity_id=activity_id,
            process_instance_id=process_instance_id,
            routine_id=routine_id,
        )
        if link_error:
            return None, link_error

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=merged.get("bank_account_id", entry.bank_account_id),
            chart_account_id=merged.get("chart_account_id", entry.chart_account_id),
            cost_center_id=merged.get("cost_center_id", entry.cost_center_id),
            counterparty_id=merged.get("counterparty_id", entry.counterparty_id),
        )
        if reference_error:
            return None, reference_error

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=company_id,
            budget_line_id=merged.get("budget_line_id", getattr(entry, "budget_line_id", None)),
            budget_contract_id=merged.get("budget_contract_id", getattr(entry, "budget_contract_id", None)),
            budget_document_id=merged.get("budget_document_id", getattr(entry, "budget_document_id", None)),
        )
        if budget_error:
            return None, budget_error

        try:
            merged.update(budget_links or {})
            merged["metadata_json"] = FinancialService._merge_budget_metadata(
                merged.get("metadata_json", entry.metadata_json),
                budget_links,
            )
            for key, value in merged.items():
                setattr(entry, key, value)
            if requested_reconciled_state is True:
                FinancialService.set_entry_reconciliation_state(
                    entry=entry,
                    reconciled=True,
                    actor_reason=unlock_reason or "Marcação manual de conciliação.",
                )
            db.session.commit()
            return entry, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar lançamento financeiro %s", entry_id)
            return None, f"Erro ao atualizar lançamento financeiro: {str(exc)}"

    @staticmethod
    def _build_principal_allocation_breakdown(
        *,
        entry: FinancialEntry,
        settlement: FinancialSettlement,
    ) -> Dict[str, Any]:
        try:
            allocations = (
                FinancialEntryAllocation.query.filter(
                    FinancialEntryAllocation.company_id == entry.company_id,
                    FinancialEntryAllocation.financial_entry_id == entry.id,
                    FinancialEntryAllocation.deleted_at.is_(None),
                )
                .order_by(FinancialEntryAllocation.id.asc())
                .all()
            )
        except Exception:
            allocations = []

        principal_amount = FinancialService._money_float(getattr(settlement, "principal_amount", None))
        entry_principal_amount = abs(FinancialService._money_float(FinancialService._resolve_entry_principal_basis_amount(entry)))
        if principal_amount <= 0 or entry_principal_amount <= 0 or not allocations:
            return {"component_kind": "principal", "items": [], "total_allocated_amount": 0.0}

        principal_allocations: List[Dict[str, Any]] = []
        for allocation in allocations:
            allocation_payload = allocation.to_dict() if hasattr(allocation, "to_dict") else dict(allocation or {})
            allocation_metadata = dict(allocation_payload.get("metadata_json") or {})
            adjustment_kind = str(allocation_metadata.get("adjustment_kind") or "").strip().lower()
            if adjustment_kind in {"correction", "discount"}:
                continue
            raw_amount = allocation_payload.get("allocated_amount")
            if raw_amount in (None, ""):
                percentage = FinancialService._money_float(allocation_payload.get("percentage"))
                raw_amount = round(entry_principal_amount * (percentage / 100.0), 2)
            base_amount = abs(FinancialService._money_float(raw_amount))
            if base_amount <= 0:
                continue
            principal_allocations.append(
                {
                    "allocation_id": allocation_payload.get("id"),
                    "chart_account_id": allocation_payload.get("chart_account_id"),
                    "cost_center_id": allocation_payload.get("cost_center_id"),
                    "activity_id": allocation_payload.get("activity_id"),
                    "process_instance_id": allocation_payload.get("process_instance_id"),
                    "routine_id": allocation_payload.get("routine_id"),
                    "allocation_type": allocation_payload.get("allocation_type"),
                    "percentage": allocation_payload.get("percentage"),
                    "basis_amount": base_amount,
                    "notes": allocation_payload.get("notes"),
                    "metadata_json": allocation_metadata,
                }
            )

        total_basis = round(sum(abs(FinancialService._money_float(item.get("basis_amount"))) for item in principal_allocations), 2)
        if total_basis <= 0 or not principal_allocations:
            return {"component_kind": "principal", "items": [], "total_allocated_amount": 0.0}

        items: List[Dict[str, Any]] = []
        distributed_total = 0.0
        for index, allocation_payload in enumerate(principal_allocations, start=1):
            base_amount = abs(FinancialService._money_float(allocation_payload.get("basis_amount")))
            proportional_amount = round((base_amount / total_basis) * principal_amount, 2) if total_basis > 0 else 0.0
            if index == len(principal_allocations):
                proportional_amount = round(principal_amount - distributed_total, 2)
            distributed_total = round(distributed_total + proportional_amount, 2)
            items.append(
                {
                    "allocation_id": allocation_payload.get("allocation_id"),
                    "chart_account_id": allocation_payload.get("chart_account_id"),
                    "cost_center_id": allocation_payload.get("cost_center_id"),
                    "activity_id": allocation_payload.get("activity_id"),
                    "process_instance_id": allocation_payload.get("process_instance_id"),
                    "routine_id": allocation_payload.get("routine_id"),
                    "allocation_type": allocation_payload.get("allocation_type"),
                    "percentage": allocation_payload.get("percentage"),
                    "entry_allocated_amount": round(base_amount, 2),
                    "settled_allocated_amount": proportional_amount,
                    "notes": allocation_payload.get("notes"),
                    "metadata_json": {
                        **dict(allocation_payload.get("metadata_json") or {}),
                        "component_kind": "principal",
                        "source_allocation_id": allocation_payload.get("allocation_id"),
                    },
                }
            )

        return {
            "component_kind": "principal",
            "basis_entry_amount": round(total_basis, 2),
            "basis_settlement_principal_amount": round(principal_amount, 2),
            "total_allocated_amount": round(distributed_total, 2),
            "items": items,
        }

    @staticmethod
    def _build_schedule_component_allocation_breakdown(
        *,
        schedule: Optional[FinancialSchedule],
        settlement: FinancialSettlement,
        component_kind: str,
        component_amount: Any = None,
        component_payloads: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        normalized_kind = str(component_kind or "").strip().lower()
        normalized_payloads = FinancialService._build_settlement_component_payloads_for_breakdown(
            settlement=settlement,
            component_kind=normalized_kind,
            component_amount=component_amount,
            component_payloads=component_payloads,
        )
        if not normalized_payloads:
            return {"component_kind": normalized_kind, "items": [], "total_allocated_amount": 0.0}

        schedule_metadata = dict(getattr(schedule, "metadata_json", {}) or {})
        items: List[Dict[str, Any]] = []
        total_allocated = 0.0
        for payload in normalized_payloads:
            amount = abs(FinancialService._money_float(payload.get("amount")))
            if amount <= 0:
                continue

            competence_date = payload.get("competence_date")
            due_date = payload.get("due_date")
            competence_date_iso = competence_date.isoformat() if hasattr(competence_date, "isoformat") else competence_date
            due_date_iso = due_date.isoformat() if hasattr(due_date, "isoformat") else due_date
            origin_adjustment_id = payload.get("origin_adjustment_id")

            adjustment_allocations: List[Dict[str, Any]] = []
            if origin_adjustment_id is not None and schedule is not None:
                try:
                    persisted_adjustment_allocations = (
                        FinancialTitleAdjustmentAllocation.query.filter(
                            FinancialTitleAdjustmentAllocation.company_id == schedule.company_id,
                            FinancialTitleAdjustmentAllocation.financial_title_adjustment_id == int(origin_adjustment_id),
                        )
                        .order_by(FinancialTitleAdjustmentAllocation.id.asc())
                        .all()
                    )
                except Exception:
                    persisted_adjustment_allocations = []
                for allocation in persisted_adjustment_allocations or []:
                    allocation_payload = allocation.to_dict() if hasattr(allocation, "to_dict") else dict(allocation or {})
                    basis_amount = abs(FinancialService._money_float(allocation_payload.get("amount")))
                    if basis_amount <= 0:
                        continue
                    adjustment_allocations.append(
                        {
                            "allocation_id": allocation_payload.get("id"),
                            "chart_account_id": allocation_payload.get("chart_account_id"),
                            "cost_center_id": allocation_payload.get("cost_center_id"),
                            "activity_id": allocation_payload.get("activity_id"),
                            "process_instance_id": allocation_payload.get("process_instance_id"),
                            "routine_id": allocation_payload.get("routine_id"),
                            "allocation_type": "amount",
                            "percentage": allocation_payload.get("percentage"),
                            "basis_amount": basis_amount,
                            "notes": None,
                            "metadata_json": allocation_payload.get("metadata_json") or {},
                        }
                    )

            if adjustment_allocations:
                total_basis = round(sum(abs(FinancialService._money_float(item.get("basis_amount"))) for item in adjustment_allocations), 2)
                items.extend(
                    FinancialService._build_proportional_allocation_items(
                        allocation_rows=adjustment_allocations,
                        total_amount=amount,
                        total_basis=total_basis,
                        default_competence_date=competence_date_iso,
                        default_due_date=due_date_iso,
                        component_kind=normalized_kind,
                        source="adjustment_allocations",
                        origin_adjustment_id=origin_adjustment_id,
                    )
                )
                total_allocated = round(total_allocated + amount, 2)
                continue

            legacy_allocations: List[Dict[str, Any]] = []
            for raw_item in list(schedule_metadata.get("allocations") or []):
                item = dict(raw_item or {})
                item_metadata = dict(item.get("metadata_json") or {})
                adjustment_kind = str(item_metadata.get("adjustment_kind") or "principal").strip().lower()
                if normalized_kind == "financial_correction" and adjustment_kind != "correction":
                    continue
                if normalized_kind == "discount" and adjustment_kind != "discount":
                    continue
                basis_amount = abs(FinancialService._money_float(item.get("allocated_amount")))
                if basis_amount <= 0:
                    continue
                legacy_allocations.append(
                    {
                        "chart_account_id": item.get("chart_account_id"),
                        "cost_center_id": item.get("cost_center_id"),
                        "allocation_type": item.get("allocation_type"),
                        "percentage": item.get("percentage"),
                        "basis_amount": basis_amount,
                        "notes": item.get("notes"),
                        "metadata_json": item_metadata,
                    }
                )

            if legacy_allocations:
                total_basis = round(sum(abs(FinancialService._money_float(item.get("basis_amount"))) for item in legacy_allocations), 2)
                items.extend(
                    FinancialService._build_proportional_allocation_items(
                        allocation_rows=legacy_allocations,
                        total_amount=amount,
                        total_basis=total_basis,
                        default_competence_date=competence_date_iso,
                        default_due_date=due_date_iso,
                        component_kind=normalized_kind,
                        source="legacy_schedule_allocations",
                        origin_adjustment_id=origin_adjustment_id,
                    )
                )
                total_allocated = round(total_allocated + amount, 2)
                continue

            payload_metadata = dict(payload.get("metadata_json") or {})
            fallback_chart_account_id = None
            if normalized_kind == "financial_correction" and payload_metadata.get("correction_index_id") and schedule is not None:
                try:
                    correction_rule = FinancialCorrectionIndex.query.filter(
                        FinancialCorrectionIndex.company_id == schedule.company_id,
                        FinancialCorrectionIndex.id == int(payload_metadata.get("correction_index_id")),
                        FinancialCorrectionIndex.deleted_at.is_(None),
                    ).first()
                except Exception:
                    correction_rule = None
                fallback_chart_account_id = (correction_rule.metadata_json or {}).get("chart_account_id") if correction_rule else None
            if not fallback_chart_account_id:
                fallback_chart_account_id = FinancialService._resolve_schedule_adjustment_chart_account_id(
                    schedule=schedule,
                    component_kind=normalized_kind,
                )
            items.append(
                {
                    "chart_account_id": fallback_chart_account_id,
                    "cost_center_id": getattr(schedule, "cost_center_id", None) if schedule is not None else None,
                    "allocation_type": "amount",
                    "percentage": None,
                    "source_allocated_amount": round(amount, 2),
                    "settled_allocated_amount": round(amount, 2),
                    "notes": None,
                    "competence_date": competence_date_iso,
                    "due_date": due_date_iso,
                    "metadata_json": {
                        **payload_metadata,
                        "component_kind": normalized_kind,
                        "source": "adjustment_rule_fallback",
                        "origin_adjustment_id": origin_adjustment_id,
                    },
                }
            )
            total_allocated = round(total_allocated + amount, 2)

        return {
            "component_kind": normalized_kind,
            "basis_schedule_id": getattr(schedule, "id", None),
            "basis_component_amount": round(sum(abs(FinancialService._money_float(item.get("amount"))) for item in normalized_payloads), 2),
            "total_allocated_amount": round(total_allocated, 2),
            "items": items,
        }

    @staticmethod
    def replace_allocations(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        ignore_bordero_lock: bool = False,
    ) -> Tuple[Optional[List[FinancialEntryAllocation]], Optional[str]]:
        try:
            data = FinancialAllocationBatchInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para rateio: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == data.financial_entry_id,
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado para rateio."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=data.company_id, entry=entry)
        if active_bordero and not ignore_bordero_lock:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}."
        if active_bordero and ignore_bordero_lock:
            external_reference = str(getattr(entry, "external_reference", "") or "").strip()
            if not (getattr(entry, "financial_schedule_id", None) or external_reference.startswith("financial_schedule:")):
                return None, "Bypass do bloqueio de borderô em rateio exige lançamento vinculado a Título Financeiro."

        normalized_allocations: List[FinancialAllocationInput] = []
        for item in data.allocations:
            if item.company_id != data.company_id or item.financial_entry_id != data.financial_entry_id:
                return None, "Todos os rateios devem pertencer ao mesmo lançamento e empresa."
            link_error = FinancialService._validate_operational_links(
                company_id=data.company_id,
                activity_id=item.activity_id,
                process_instance_id=item.process_instance_id,
                routine_id=item.routine_id,
            )
            if link_error:
                return None, link_error
            normalized_allocations.append(item)

        percentage_total = Decimal("0")
        amount_total = Decimal("0")
        allocation_mode: Optional[str] = None

        for item in normalized_allocations:
            if allocation_mode is None:
                allocation_mode = item.allocation_type
            elif allocation_mode != item.allocation_type:
                return None, "Não é permitido misturar rateio por percentual e por valor no mesmo lançamento."

            if item.allocation_type == "percentage":
                percentage_total += item.percentage or Decimal("0")
            else:
                adjustment_kind = str((item.metadata_json or {}).get("adjustment_kind") or "").strip().lower()
                if adjustment_kind == "discount" and (item.allocated_amount or Decimal("0")) > 0:
                    return None, "Rateio de desconto deve possuir valor negativo."
                if adjustment_kind != "discount" and (item.allocated_amount or Decimal("0")) < 0:
                    return None, "Somente rateios de desconto podem possuir valor negativo."
                amount_total += item.allocated_amount or Decimal("0")

        if allocation_mode == "percentage" and percentage_total != Decimal("100"):
            return None, f"Rateio percentual inválido. Soma atual: {percentage_total}."

        principal_basis_amount = FinancialService._resolve_entry_principal_basis_amount(entry)
        if allocation_mode == "amount" and amount_total != (entry.original_amount or Decimal("0")) and amount_total != principal_basis_amount:
            return None, (
                "Rateio por valor inválido. "
                f"Soma atual: {amount_total}. Valor do lançamento: {entry.original_amount}. "
                f"Valor principal permitido: {principal_basis_amount}."
            )

        try:
            FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.financial_entry_id == entry.id,
                FinancialEntryAllocation.company_id == data.company_id,
            ).delete(synchronize_session=False)

            created: List[FinancialEntryAllocation] = []
            for item in normalized_allocations:
                allocation = FinancialEntryAllocation(**item.model_dump())
                db.session.add(allocation)
                created.append(allocation)

            db.session.commit()
            return created, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao substituir rateios do lançamento %s", entry.id)
            return None, f"Erro ao persistir rateio: {str(exc)}"


    @staticmethod
    def _build_title_settlement_snapshot(
        *,
        entry: FinancialEntry,
        settlement_data: FinancialSettlementInput,
        total_liquidated_before: Decimal,
    ) -> Optional[Dict[str, Any]]:
        schedule_id = getattr(entry, "financial_schedule_id", None)
        if not schedule_id:
            return None

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == entry.company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None

        due_date = schedule.next_due_date or schedule.first_due_date or schedule.start_date
        amount_totals = FinancialTitleAmountService.calculate(
            company_id=schedule.company_id,
            template_amount=schedule.template_amount,
            metadata_json=schedule.metadata_json,
            due_date=due_date,
            reference_date=settlement_data.settlement_date or date.today(),
        )
        balance_before = FinancialTitleBalanceService.calculate_for_schedule(
            schedule=schedule,
            reference_date=settlement_data.settlement_date or date.today(),
        )
        principal_basis_amount = FinancialService._resolve_entry_principal_basis_amount(
            entry,
            schedule=schedule,
        )
        settled_before = FinancialService._money_decimal(balance_before.get("principal_settled") or total_liquidated_before or 0)
        principal_open_before = FinancialService._money_decimal(balance_before.get("principal_open"))
        adjustments_open_before = FinancialService._money_decimal(balance_before.get("adjustments_open"))
        discounts_open_before = FinancialService._money_decimal(balance_before.get("discounts_open"))
        total_open_before = FinancialService._money_decimal(balance_before.get("total_open"))

        if settlement_data.settlement_components:
            component_breakdown: Dict[str, Decimal] = {}
            for component in settlement_data.settlement_components:
                component_type = str(getattr(component, "component_type", "") or "").strip().lower()
                component_breakdown[component_type] = component_breakdown.get(component_type, Decimal("0.00")) + FinancialService._money_decimal(
                    getattr(component, "amount", 0)
                )
            principal_now = FinancialService._money_decimal(component_breakdown.get("principal"))
            correction_now = sum(
                (component_breakdown.get(component_type, Decimal("0.00")) for component_type in SETTLEMENT_CORRECTION_COMPONENT_TYPES),
                Decimal("0.00"),
            )
            discount_now = FinancialService._money_decimal(component_breakdown.get("discount"))
        else:
            principal_now = FinancialService._money_decimal(settlement_data.principal_amount)
            correction_now = (
                FinancialService._money_decimal(settlement_data.interest_amount)
                + FinancialService._money_decimal(settlement_data.penalty_amount)
                + FinancialService._money_decimal(settlement_data.fee_amount)
                + FinancialService._money_decimal(settlement_data.other_adjustments_amount)
            )
            discount_now = FinancialService._money_decimal(settlement_data.discount_amount)

        gross_now = FinancialService._money_decimal((settlement_data.gross_amount or settlement_data.net_amount or Decimal("0")))
        if gross_now <= Decimal("0.00"):
            gross_now = max(principal_now + correction_now - discount_now, Decimal("0.00"))

        settled_after = settled_before + principal_now
        open_after = max(principal_basis_amount - settled_after, Decimal("0.00"))
        adjustments_open_after = max(adjustments_open_before - correction_now, Decimal("0.00"))
        discounts_open_after = max(discounts_open_before - discount_now, Decimal("0.00"))
        total_open_after = max(open_after + adjustments_open_after - discounts_open_after, Decimal("0.00"))

        settlement_state_before = resolve_title_settlement_state(
            principal_amount=balance_before.get("principal_amount") or principal_basis_amount or 0,
            principal_settled=balance_before.get("principal_settled") or total_liquidated_before or 0,
            adjustments_settled=balance_before.get("adjustments_settled") or 0,
            discounts_applied=balance_before.get("discounts_applied") or 0,
            total_open=total_open_before,
        )
        settlement_state_after = resolve_title_settlement_state(
            principal_amount=balance_before.get("principal_amount") or principal_basis_amount or 0,
            principal_settled=settled_after,
            adjustments_settled=FinancialService._money_decimal(balance_before.get("adjustments_settled")) + correction_now,
            discounts_applied=FinancialService._money_decimal(balance_before.get("discounts_applied")) + discount_now,
            total_open=total_open_after,
        )
        operational_state_before = build_title_operational_state_metadata(
            schedule_status=schedule.status,
            settlement_state=settlement_state_before,
            entry_type=schedule.entry_type,
            metadata_json=schedule.metadata_json,
        )
        operational_state_after = build_title_operational_state_metadata(
            schedule_status=schedule.status,
            settlement_state=settlement_state_after,
            entry_type=schedule.entry_type,
            metadata_json=schedule.metadata_json,
        )
        editable_before = {
            "principal": FinancialService._money_float(principal_open_before),
            "financial_correction": FinancialService._money_float(adjustments_open_before),
            "discount": FinancialService._money_float(discounts_open_before),
            "gross_amount": FinancialService._money_float(total_open_before),
            "total_open": FinancialService._money_float(total_open_before),
        }
        editable_after = {
            "principal": FinancialService._money_float(open_after),
            "financial_correction": FinancialService._money_float(adjustments_open_after),
            "discount": FinancialService._money_float(discounts_open_after),
            "gross_amount": FinancialService._money_float(total_open_after),
            "total_open": FinancialService._money_float(total_open_after),
        }
        editable_rules = {
            "principal_max": editable_before["principal"],
            "allows_free_financial_correction": True,
            "allows_free_discount": True,
            "requires_principal_within_open_balance": True,
        }
        return {
            "contract_version": FINANCIAL_TITLE_MEMORY_VERSION,
            "financial_schedule_id": schedule.id,
            "schedule_code": schedule.schedule_code,
            "calculation_date": (settlement_data.settlement_date or date.today()).isoformat(),
            "competence_date": schedule.competence_date.isoformat() if schedule.competence_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "template_amount": FinancialService._money_float(principal_basis_amount),
            "correction_amount": amount_totals.get("correction_amount"),
            "discount_amount": amount_totals.get("discount_amount"),
            "updated_amount": amount_totals.get("updated_amount"),
            "settled_principal_before": FinancialService._money_float(settled_before),
            "settled_principal_current": FinancialService._money_float(principal_now),
            "settled_principal_after": FinancialService._money_float(settled_after),
            "open_principal_after": FinancialService._money_float(open_after),
            "principal_open_before": FinancialService._money_float(principal_open_before),
            "adjustments_open_before": FinancialService._money_float(adjustments_open_before),
            "discounts_open_before": FinancialService._money_float(discounts_open_before),
            "total_open_before": FinancialService._money_float(total_open_before),
            "adjustments_open_after": FinancialService._money_float(adjustments_open_after),
            "discounts_open_after": FinancialService._money_float(discounts_open_after),
            "total_open_after": FinancialService._money_float(total_open_after),
            "principal_only_total_after": FinancialService._money_float(open_after),
            "title": {
                "id": schedule.id,
                "code": schedule.schedule_code,
                "status": schedule.status,
                "entry_type": schedule.entry_type,
                "movement_nature": schedule.movement_nature,
                "description": schedule.description or schedule.name,
            },
            "entry": {
                "id": getattr(entry, "id", None),
                "code": getattr(entry, "entry_code", None),
                "status": getattr(entry, "status", None),
                "movement_nature": getattr(entry, "movement_nature", None),
            },
            "before": {
                "principal": FinancialService._money_float(principal_open_before),
                "financial_correction": FinancialService._money_float(adjustments_open_before),
                "discount": FinancialService._money_float(discounts_open_before),
                "gross_amount": FinancialService._money_float(total_open_before),
                "principal_open": FinancialService._money_float(principal_open_before),
                "adjustments_open": FinancialService._money_float(adjustments_open_before),
                "discounts_open": FinancialService._money_float(discounts_open_before),
                "total_open": FinancialService._money_float(total_open_before),
                "principal_settled": FinancialService._money_float(settled_before),
                "settlement_state": settlement_state_before,
                "operational_state": operational_state_before,
                "editable_open": editable_before,
                "editable_rules": editable_rules,
            },
            "current": {
                "principal": FinancialService._money_float(principal_now),
                "principal_settled": FinancialService._money_float(principal_now),
                "financial_correction": FinancialService._money_float(correction_now),
                "discount": FinancialService._money_float(discount_now),
                "gross_amount": FinancialService._money_float(gross_now),
            },
            "after": {
                "principal": FinancialService._money_float(open_after),
                "financial_correction": FinancialService._money_float(adjustments_open_after),
                "discount": FinancialService._money_float(discounts_open_after),
                "gross_amount": FinancialService._money_float(total_open_after),
                "principal_open": FinancialService._money_float(open_after),
                "adjustments_open": FinancialService._money_float(adjustments_open_after),
                "discounts_open": FinancialService._money_float(discounts_open_after),
                "total_open": FinancialService._money_float(total_open_after),
                "ledger_total_open": FinancialService._money_float(total_open_after),
                "principal_settled": FinancialService._money_float(settled_after),
                "settlement_state": settlement_state_after,
                "operational_state": operational_state_after,
                "editable_open": editable_after,
            },
        }


    @staticmethod
    def _build_title_calculation_log_payload(
        *,
        entry: FinancialEntry,
        settlement: FinancialSettlement,
        snapshot: Dict[str, Any],
        component_payloads: Optional[Sequence[Dict[str, Any]]] = None,
        event_type: str = "settlement_posted",
        source: str = "create_settlement",
        calculation_date: Optional[date] = None,
        metadata_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        before_block = dict(snapshot.get("before") or {})
        current_block = dict(snapshot.get("current") or {})
        after_block = dict(snapshot.get("after") or {})

        principal_before = Decimal(
            str(
                before_block.get("principal")
                or before_block.get("principal_open")
                or snapshot.get("principal_open_before")
                or 0
            )
        )
        if principal_before <= 0:
            principal_before = Decimal(str(snapshot.get("open_principal_after") or 0)) + Decimal(
                str(snapshot.get("settled_principal_current") or 0)
            )
        principal_settled_now = Decimal(str(snapshot.get("settled_principal_current") or 0))
        principal_after = max(principal_before - principal_settled_now, Decimal("0"))
        adjustments_open_before = Decimal(
            str(
                before_block.get("financial_correction")
                or before_block.get("adjustments_open")
                or snapshot.get("adjustments_open_before")
                or 0
            )
        )
        discounts_open_before = Decimal(
            str(
                before_block.get("discount")
                or before_block.get("discounts_open")
                or snapshot.get("discounts_open_before")
                or 0
            )
        )
        adjustments_settled_now = Decimal(str(current_block.get("financial_correction") or 0))
        if adjustments_settled_now <= 0:
            adjustments_settled_now = (
                Decimal(str(getattr(settlement, "interest_amount", 0) or 0))
                + Decimal(str(getattr(settlement, "penalty_amount", 0) or 0))
                + Decimal(str(getattr(settlement, "fee_amount", 0) or 0))
                + Decimal(str(getattr(settlement, "other_adjustments_amount", 0) or 0))
            )
        discount_now = Decimal(str(current_block.get("discount") or getattr(settlement, "discount_amount", 0) or 0))
        adjustments_open_after = Decimal(
            str(
                after_block.get("financial_correction")
                or after_block.get("adjustments_open")
                or snapshot.get("adjustments_open_after")
                or 0
            )
        )
        if adjustments_open_after <= Decimal("0") and adjustments_open_before > Decimal("0"):
            adjustments_open_after = max(adjustments_open_before - adjustments_settled_now, Decimal("0"))
        discounts_open_after = Decimal(
            str(
                after_block.get("discount")
                or after_block.get("discounts_open")
                or snapshot.get("discounts_open_after")
                or 0
            )
        )
        if discounts_open_after <= Decimal("0") and discounts_open_before > Decimal("0"):
            discounts_open_after = max(discounts_open_before - discount_now, Decimal("0"))
        total_due_before = Decimal(
            str(
                before_block.get("gross_amount")
                or before_block.get("total_open")
                or snapshot.get("total_open_before")
                or 0
            )
        )
        if total_due_before <= 0:
            total_due_before = principal_before + adjustments_open_before - discounts_open_before
        total_due_after = Decimal(
            str(
                after_block.get("gross_amount")
                or after_block.get("total_open")
                or snapshot.get("principal_only_total_after")
                or snapshot.get("total_open_after")
                or 0
            )
        )
        if total_due_after <= 0 and (principal_after > Decimal("0") or adjustments_open_after > Decimal("0") or discounts_open_after > Decimal("0")):
            total_due_after = max(principal_after + adjustments_open_after - discounts_open_after, Decimal("0"))

        settlement_metadata = dict(getattr(settlement, "metadata_json", {}) or {})
        financial_correction_audit = dict(settlement_metadata.get("financial_correction_audit") or {})
        actor_payload = FinancialService._build_settlement_actor_payload(settlement, metadata_json=settlement_metadata)
        component_summary = FinancialService._build_settlement_component_audit_payload(
            component_payloads=component_payloads,
            current_block=current_block,
        )
        evidence_payload = FinancialService._build_settlement_evidence_payload(
            entry=entry,
            settlement=settlement,
            metadata_json=settlement_metadata,
            component_summary=component_summary,
        )
        tenant_scope = {
            "company_id": entry.company_id,
            "financial_schedule_id": int(snapshot["financial_schedule_id"]),
            "financial_entry_id": entry.id,
            "financial_settlement_id": getattr(settlement, "id", None),
            "schedule_company_id": snapshot.get("company_id") or entry.company_id,
            "entry_company_id": getattr(entry, "company_id", None),
            "settlement_company_id": getattr(settlement, "company_id", None),
            "scope_consistent": (
                int(snapshot.get("company_id") or entry.company_id) == int(entry.company_id)
                and int(getattr(settlement, "company_id", entry.company_id) or entry.company_id) == int(entry.company_id)
            ),
        }
        return {
            "company_id": entry.company_id,
            "financial_schedule_id": int(snapshot["financial_schedule_id"]),
            "financial_entry_id": entry.id,
            "financial_settlement_id": getattr(settlement, "id", None),
            "event_type": event_type,
            "calculation_date": calculation_date or settlement.settlement_date,
            "template_amount": Decimal(str(snapshot.get("template_amount") or 0)),
            "correction_amount": Decimal(str(snapshot.get("correction_amount") or 0)),
            "discount_amount": Decimal(str(snapshot.get("discount_amount") or 0)),
            "updated_amount": Decimal(str(snapshot.get("updated_amount") or 0)),
            "settled_principal_before": Decimal(str(snapshot.get("settled_principal_before") or 0)),
            "settled_principal_current": Decimal(str(snapshot.get("settled_principal_current") or 0)),
            "settled_principal_after": Decimal(str(snapshot.get("settled_principal_after") or 0)),
            "open_principal_after": Decimal(str(snapshot.get("open_principal_after") or 0)),
            "principal_before": principal_before.quantize(Decimal("0.01")),
            "adjustments_open_before": adjustments_open_before.quantize(Decimal("0.01")),
            "total_due_before": total_due_before.quantize(Decimal("0.01")),
            "principal_settled_now": principal_settled_now.quantize(Decimal("0.01")),
            "adjustments_settled_now": adjustments_settled_now.quantize(Decimal("0.01")),
            "discount_now": discount_now.quantize(Decimal("0.01")),
            "principal_after": principal_after.quantize(Decimal("0.01")),
            "adjustments_open_after": adjustments_open_after.quantize(Decimal("0.01")),
            "total_due_after": total_due_after.quantize(Decimal("0.01")),
            "snapshot_json": snapshot,
            "metadata_json": {
                "source": source,
                "settlement_code": settlement.settlement_code,
                "snapshot": snapshot,
                "ledger_version": FINANCIAL_TITLE_MEMORY_VERSION,
                "memory_contract_version": snapshot.get("contract_version") or FINANCIAL_TITLE_MEMORY_VERSION,
                "before": before_block,
                "current": current_block,
                "after": after_block,
                "actor": actor_payload,
                "evidence": evidence_payload,
                "component_summary": component_summary,
                "financial_correction_audit": financial_correction_audit,
                "tenant_scope": tenant_scope,
                "editable_before": before_block.get("editable_open") or snapshot.get("editable_before") or {},
                "editable_after": after_block.get("editable_open") or snapshot.get("editable_after") or {},
                "editable_rules": before_block.get("editable_rules") or snapshot.get("editable_rules") or {},
                **dict(metadata_overrides or {}),
            },
        }

    @staticmethod
    def _serialize_existing_settlement_component_payloads(
        *,
        settlement: FinancialSettlement,
        components: Optional[Sequence[FinancialSettlementComponent]] = None,
    ) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for component in components or []:
            payloads.append(
                {
                    "component_type": getattr(component, "component_type", None),
                    "amount": FinancialService._money_decimal(getattr(component, "amount", 0)),
                    "competence_date": getattr(component, "competence_date", None),
                    "due_date": getattr(component, "due_date", None),
                    "source": getattr(component, "source", None) or "system",
                    "origin_adjustment_id": getattr(component, "origin_adjustment_id", None),
                    "metadata_json": dict(getattr(component, "metadata_json", {}) or {}),
                }
            )
        if payloads:
            return payloads
        return FinancialService._build_serialized_settlement_component_payloads(settlement=settlement)

    @staticmethod
    def _build_title_balance_block(balance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        current = dict(balance or {})
        editable_open = dict(current.get("editable_open") or {})
        editable_rules = dict(current.get("editable_rules") or {})
        operational_state = {
            "code": current.get("operational_state"),
            "label": current.get("operational_state_label"),
            "include_in_accounting_reports": current.get("include_in_accounting_reports"),
            "include_in_projected_reports": current.get("include_in_projected_reports"),
        }
        operational_state = {key: value for key, value in operational_state.items() if value not in (None, "", [], {})}
        return {
            "principal": FinancialService._money_float(current.get("principal_open")),
            "financial_correction": FinancialService._money_float(current.get("adjustments_open")),
            "discount": FinancialService._money_float(current.get("discounts_open")),
            "gross_amount": FinancialService._money_float(current.get("total_open")),
            "principal_open": FinancialService._money_float(current.get("principal_open")),
            "adjustments_open": FinancialService._money_float(current.get("adjustments_open")),
            "discounts_open": FinancialService._money_float(current.get("discounts_open")),
            "total_open": FinancialService._money_float(current.get("total_open")),
            "principal_settled": FinancialService._money_float(current.get("principal_settled")),
            "settlement_state": current.get("settlement_state"),
            "operational_state": operational_state,
            "editable_open": editable_open or {
                "principal": FinancialService._money_float(current.get("principal_open")),
                "financial_correction": FinancialService._money_float(current.get("adjustments_open")),
                "discount": FinancialService._money_float(current.get("discounts_open")),
                "gross_amount": FinancialService._money_float(current.get("total_open")),
                "total_open": FinancialService._money_float(current.get("total_open")),
            },
            "editable_rules": editable_rules,
        }

    @staticmethod
    def _build_deleted_settlement_snapshot(
        *,
        entry: FinancialEntry,
        schedule: FinancialSchedule,
        settlement: FinancialSettlement,
        before_balance: Dict[str, Any],
        after_balance: Dict[str, Any],
        component_payloads: Optional[Sequence[Dict[str, Any]]] = None,
        deleted_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        principal_now = Decimal("0.00")
        correction_now = Decimal("0.00")
        discount_now = Decimal("0.00")
        for component_payload in component_payloads or []:
            normalized_kind = FinancialService._normalize_component_kind(component_payload.get("component_type"))
            amount = FinancialService._money_decimal(component_payload.get("amount"))
            if normalized_kind == "discount":
                discount_now += amount
            elif normalized_kind == "financial_correction":
                correction_now += amount
            else:
                principal_now += amount
        gross_now = max(principal_now + correction_now - discount_now, Decimal("0.00"))

        effective_deleted_at = deleted_at or datetime.utcnow()
        before_block = FinancialService._build_title_balance_block(before_balance)
        after_block = FinancialService._build_title_balance_block(after_balance)
        principal_basis_amount = FinancialService._resolve_entry_principal_basis_amount(
            entry,
            schedule=schedule,
        )
        due_date = schedule.next_due_date or schedule.first_due_date or schedule.start_date

        return {
            "contract_version": FINANCIAL_TITLE_MEMORY_VERSION,
            "financial_schedule_id": schedule.id,
            "schedule_code": schedule.schedule_code,
            "calculation_date": effective_deleted_at.date().isoformat(),
            "competence_date": schedule.competence_date.isoformat() if schedule.competence_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "template_amount": FinancialService._money_float(principal_basis_amount),
            "correction_amount": FinancialService._money_float(before_balance.get("adjustments_open")),
            "discount_amount": FinancialService._money_float(before_balance.get("discounts_open")),
            "updated_amount": FinancialService._money_float(before_balance.get("total_open")),
            "settled_principal_before": FinancialService._money_float(before_balance.get("principal_settled")),
            "settled_principal_current": FinancialService._money_float(principal_now),
            "settled_principal_after": FinancialService._money_float(after_balance.get("principal_settled")),
            "open_principal_after": FinancialService._money_float(after_balance.get("principal_open")),
            "principal_open_before": FinancialService._money_float(before_balance.get("principal_open")),
            "adjustments_open_before": FinancialService._money_float(before_balance.get("adjustments_open")),
            "discounts_open_before": FinancialService._money_float(before_balance.get("discounts_open")),
            "total_open_before": FinancialService._money_float(before_balance.get("total_open")),
            "adjustments_open_after": FinancialService._money_float(after_balance.get("adjustments_open")),
            "discounts_open_after": FinancialService._money_float(after_balance.get("discounts_open")),
            "total_open_after": FinancialService._money_float(after_balance.get("total_open")),
            "principal_only_total_after": FinancialService._money_float(after_balance.get("principal_open")),
            "title": {
                "id": getattr(schedule, "id", None),
                "code": getattr(schedule, "schedule_code", None),
                "status": getattr(schedule, "status", None),
                "entry_type": getattr(schedule, "entry_type", None),
                "movement_nature": getattr(schedule, "movement_nature", None),
                "description": getattr(schedule, "description", None) or getattr(schedule, "name", None),
            },
            "entry": {
                "id": getattr(entry, "id", None),
                "code": getattr(entry, "entry_code", None),
                "status": getattr(entry, "status", None),
                "movement_nature": getattr(entry, "movement_nature", None),
            },
            "before": before_block,
            "current": {
                "principal": FinancialService._money_float(principal_now),
                "principal_settled": FinancialService._money_float(principal_now),
                "financial_correction": FinancialService._money_float(correction_now),
                "discount": FinancialService._money_float(discount_now),
                "gross_amount": FinancialService._money_float(gross_now),
            },
            "after": after_block,
        }

    @staticmethod
    def _hide_superseded_calculation_logs(
        *,
        company_id: int,
        schedule_id: int,
        settlement_id: int,
        hidden_at: datetime,
    ) -> List[int]:
        if not settlement_id:
            return []
        logs = (
            FinancialTitleCalculationLog.query.filter(
                FinancialTitleCalculationLog.company_id == company_id,
                FinancialTitleCalculationLog.financial_schedule_id == schedule_id,
                FinancialTitleCalculationLog.financial_settlement_id == settlement_id,
            )
            .order_by(FinancialTitleCalculationLog.id.asc())
            .all()
        )
        hidden_ids: List[int] = []
        for log in logs or []:
            if str(getattr(log, "event_type", "") or "").strip().lower() == "settlement_deleted":
                continue
            metadata = dict(getattr(log, "metadata_json", {}) or {})
            metadata["hidden_from_memory"] = True
            metadata["hidden_reason"] = "settlement_deleted"
            metadata["hidden_at"] = hidden_at.isoformat()
            log.metadata_json = metadata
            if getattr(log, "id", None) is not None:
                hidden_ids.append(int(log.id))
        return hidden_ids

    @staticmethod
    def _recalculate_entry_status(
        *,
        entry: FinancialEntry,
        schedule: Optional[FinancialSchedule] = None,
    ) -> None:
        total_liquidated = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
            .filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .scalar()
        ) or Decimal("0")
        principal_basis_amount = FinancialService._resolve_entry_principal_basis_amount(
            entry,
            schedule=schedule,
        )
        if total_liquidated >= principal_basis_amount and principal_basis_amount > Decimal("0"):
            entry.status = "settled"
            return
        if total_liquidated > Decimal("0"):
            entry.status = "partially_settled"
            return
        if getattr(entry, "status", None) in {"partially_settled", "settled"}:
            entry.status = "posted"

    @staticmethod
    def _resolve_settlement_schedule_context(
        *,
        entry: FinancialEntry,
        title_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], Optional[date], Optional[date]]:
        schedule_id = getattr(entry, "financial_schedule_id", None)
        competence_date = None
        due_date = None

        snapshot = dict(title_snapshot or {})
        if not schedule_id and snapshot.get("financial_schedule_id") is not None:
            try:
                schedule_id = int(snapshot.get("financial_schedule_id"))
            except (TypeError, ValueError):
                schedule_id = None

        raw_competence = snapshot.get("competence_date")
        raw_due_date = snapshot.get("due_date")
        if raw_competence:
            try:
                competence_date = date.fromisoformat(str(raw_competence))
            except ValueError:
                competence_date = None
        if raw_due_date:
            try:
                due_date = date.fromisoformat(str(raw_due_date))
            except ValueError:
                due_date = None

        return schedule_id, competence_date, due_date

    @staticmethod
    def _build_settlement_component_payloads(
        *,
        entry: FinancialEntry,
        settlement_data: FinancialSettlementInput,
        title_snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        schedule_id, title_competence_date, title_due_date = FinancialService._resolve_settlement_schedule_context(
            entry=entry,
            title_snapshot=title_snapshot,
        )
        default_competence_date = settlement_data.settlement_date or title_competence_date or date.today()
        default_due_date = title_due_date or settlement_data.settlement_date

        if settlement_data.settlement_components:
            payloads: List[Dict[str, Any]] = []
            for component in settlement_data.settlement_components:
                component_due_date = component.due_date or default_due_date
                payloads.append(
                    {
                        "company_id": settlement_data.company_id,
                        "financial_schedule_id": schedule_id,
                        "component_type": component.component_type,
                        "amount": Decimal(str(component.amount or 0)).quantize(Decimal("0.01")),
                        "competence_date": component.competence_date or default_competence_date,
                        "due_date": component_due_date,
                        "source": component.source or "system",
                        "origin_adjustment_id": component.origin_adjustment_id,
                        "metadata_json": dict(component.metadata_json or {}),
                    }
                )
            return payloads

        amount_map = (
            ("principal", settlement_data.principal_amount, title_competence_date or default_competence_date, default_due_date),
            ("interest", settlement_data.interest_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("fine", settlement_data.penalty_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("discount", settlement_data.discount_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("manual_adjustment", settlement_data.fee_amount + settlement_data.other_adjustments_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
        )
        payloads = []
        for component_type, raw_amount, competence_date_value, due_date_value in amount_map:
            amount = Decimal(str(raw_amount or 0)).quantize(Decimal("0.01"))
            if amount <= Decimal("0"):
                continue
            payloads.append(
                {
                    "company_id": settlement_data.company_id,
                    "financial_schedule_id": schedule_id,
                    "component_type": component_type,
                    "amount": amount,
                    "competence_date": competence_date_value or default_competence_date,
                    "due_date": due_date_value,
                    "source": "system",
                    "origin_adjustment_id": None,
                    "metadata_json": {"source_context": "aggregated_settlement_fields"},
                }
            )
        return payloads


    @staticmethod
    def create_settlement(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        ignore_bordero_lock: bool = False,
    ) -> Tuple[Optional[FinancialSettlement], Optional[str]]:
        normalized_payload = dict(payload or {})
        company_id = normalized_payload.get("company_id")
        if company_id:
            normalized_payload["settlement_code"] = FinancialService._normalize_requested_settlement_code(
                company_id=int(company_id),
                requested_code=normalized_payload.get("settlement_code"),
            )

        try:
            data = FinancialSettlementInput(**normalized_payload)
        except Exception as exc:
            return None, f"Payload inválido para baixa: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == data.financial_entry_id,
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado para baixa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=data.company_id, entry=entry)
        if active_bordero and not ignore_bordero_lock:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}. Faça a baixa pelo borderô."
        if active_bordero and ignore_bordero_lock:
            bordero_metadata = dict(data.metadata_json or {})
            if not (
                bordero_metadata.get("reconcile_via_bordero")
                and bordero_metadata.get("bordero_id")
                and bordero_metadata.get("bordero_settlement_id")
            ):
                return None, "Bypass do bloqueio de borderô exige rastreabilidade completa da baixa do borderô."

        existing = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == data.company_id,
            FinancialSettlement.settlement_code == data.settlement_code,
        ).first()
        if existing:
            return None, f"Já existe baixa com código {data.settlement_code} para esta empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
        )
        if reference_error:
            return None, reference_error

        try:
            schedule_for_allocations = None
            if getattr(entry, "financial_schedule_id", None):
                try:
                    schedule_for_allocations = FinancialSchedule.query.filter(
                        FinancialSchedule.id == entry.financial_schedule_id,
                        FinancialSchedule.company_id == entry.company_id,
                        FinancialSchedule.deleted_at.is_(None),
                    ).first()
                except Exception:
                    schedule_for_allocations = None

            total_liquidated = (
                db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
                .filter(
                    FinancialSettlement.company_id == data.company_id,
                    FinancialSettlement.financial_entry_id == data.financial_entry_id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                )
                .scalar()
            ) or Decimal("0")

            if data.principal_amount < Decimal("0"):
                return None, "Baixa inválida: o valor principal não pode ser negativo."
            if (data.gross_amount or data.net_amount or Decimal("0")) <= Decimal("0"):
                return None, "Baixa inválida: o valor da baixa deve ser maior que zero."

            projected_total = Decimal(total_liquidated) + data.principal_amount
            principal_basis_amount = FinancialService._resolve_entry_principal_basis_amount(
                entry,
                schedule=schedule_for_allocations,
            )
            if projected_total > principal_basis_amount:
                return None, (
                    "Baixa principal excede o valor principal do lançamento. "
                    f"Baixado atual: {total_liquidated}. Principal: {principal_basis_amount}."
                )

            settlement_payload = data.model_dump(exclude={"settlement_components"})
            title_snapshot = FinancialService._build_title_settlement_snapshot(
                entry=entry,
                settlement_data=data,
                total_liquidated_before=Decimal(total_liquidated),
            )
            component_payloads = FinancialService._build_settlement_component_payloads(
                entry=entry,
                settlement_data=data,
                title_snapshot=title_snapshot,
            )
            if title_snapshot:
                settlement_payload["metadata_json"] = {
                    **dict(settlement_payload.get("metadata_json") or {}),
                    "financial_title_snapshot": title_snapshot,
                }
            if component_payloads:
                settlement_payload["metadata_json"] = {
                    **dict(settlement_payload.get("metadata_json") or {}),
                    "settlement_component_count": len(component_payloads),
                }

            settlement = FinancialSettlement(**settlement_payload)
            db.session.add(settlement)
            flush = getattr(db.session, "flush", None)
            if callable(flush):
                flush()
            for component_payload in component_payloads:
                db.session.add(
                    FinancialSettlementComponent(
                        financial_settlement_id=getattr(settlement, "id", None),
                        **component_payload,
                    )
                )
            principal_allocation_breakdown = FinancialService._build_principal_allocation_breakdown(
                entry=entry,
                settlement=settlement,
            )
            correction_amount = sum(
                FinancialService._money_float(component.get("amount"))
                for component in component_payloads
                if str(component.get("component_type") or "").strip().lower() in set(SETTLEMENT_CORRECTION_COMPONENT_TYPES)
            )
            discount_amount = sum(
                abs(FinancialService._money_float(component.get("amount")))
                for component in component_payloads
                if str(component.get("component_type") or "").strip().lower() == "discount"
            )
            correction_allocation_breakdown = FinancialService._build_schedule_component_allocation_breakdown(
                schedule=schedule_for_allocations,
                settlement=settlement,
                component_kind="financial_correction",
                component_amount=correction_amount,
                component_payloads=component_payloads,
            )
            discount_allocation_breakdown = FinancialService._build_schedule_component_allocation_breakdown(
                schedule=schedule_for_allocations,
                settlement=settlement,
                component_kind="discount",
                component_amount=discount_amount,
                component_payloads=component_payloads,
            )
            settlement_allocation_breakdown = {
                **dict((getattr(settlement, "metadata_json", {}) or {}).get("settlement_allocation_breakdown") or {}),
            }
            if principal_allocation_breakdown.get("items"):
                settlement_allocation_breakdown["principal"] = principal_allocation_breakdown
            if correction_allocation_breakdown.get("items"):
                settlement_allocation_breakdown["financial_correction"] = correction_allocation_breakdown
            if discount_allocation_breakdown.get("items"):
                settlement_allocation_breakdown["discount"] = discount_allocation_breakdown
            if settlement_allocation_breakdown:
                settlement.metadata_json = {
                    **dict(getattr(settlement, "metadata_json", {}) or {}),
                    "settlement_allocation_breakdown": settlement_allocation_breakdown,
                }

            if title_snapshot:
                db.session.add(
                    FinancialTitleCalculationLog(
                        **FinancialService._build_title_calculation_log_payload(
                            entry=entry,
                            settlement=settlement,
                            snapshot=title_snapshot,
                            component_payloads=component_payloads,
                        )
                    )
                )

            if projected_total == principal_basis_amount:
                entry.status = "settled"
            elif projected_total > Decimal("0"):
                entry.status = "partially_settled"

            db.session.commit()
            return settlement, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar baixa para lançamento %s", data.financial_entry_id)
            return None, f"Erro ao criar baixa: {str(exc)}"

    @staticmethod
    def delete_settlement(
        *,
        settlement_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        allow_bordero_child_delete: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Baixa financeira não encontrada no escopo da empresa."

        if str(settlement.reconciliation_status or "").strip().lower() in {"matched", "reconciled"}:
            return None, "Baixa conciliada/casada não pode ser excluída. Desfaça a conciliação antes de remover."

        try:
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == settlement.financial_entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            schedule = FinancialService._resolve_linked_schedule(entry, company_id)
            schedule_metadata = dict(getattr(schedule, "metadata_json", None) or {}) if schedule is not None else {}
            if schedule_metadata.get("managed_by_contract_billing"):
                return None, "Baixa gerida pelo faturamento contratual. Faça o estorno/reprocessamento no módulo de Contratos."
            bordero_child_metadata = dict(getattr(settlement, "metadata_json", {}) or {})
            bordero_child_delete_allowed = bool(
                allow_bordero_child_delete
                and bordero_child_metadata.get("reconcile_via_bordero")
                and bordero_child_metadata.get("bordero_settlement_id")
            )
            if FinancialService._requires_whole_entry_delete(entry, schedule) and not bordero_child_delete_allowed:
                return None, (
                    "Lançamento rápido não permite excluir apenas a baixa. "
                    "Exclua o lançamento rápido inteiro para remover baixa e título."
                )

            components = FinancialSettlementComponent.query.filter(
                FinancialSettlementComponent.company_id == company_id,
                FinancialSettlementComponent.financial_settlement_id == settlement.id,
            ).all()
            component_payloads = FinancialService._serialize_existing_settlement_component_payloads(
                settlement=settlement,
                components=components,
            )
            reference_date = getattr(settlement, "settlement_date", None) or date.today()
            before_balance = (
                FinancialTitleBalanceService.calculate_for_schedule(
                    schedule=schedule,
                    reference_date=reference_date,
                )
                if schedule is not None
                else None
            )

            deleted_at = datetime.utcnow()
            settlement.deleted_at = deleted_at
            settlement.metadata_json = {
                **dict(getattr(settlement, "metadata_json", {}) or {}),
                "deleted_at": deleted_at.isoformat(),
                "deleted_via": "financial_service.delete_settlement",
            }

            for component in components:
                origin_id = getattr(component, "origin_adjustment_id", None)
                if not origin_id:
                    continue
                adjustment = FinancialTitleAdjustment.query.filter(
                    FinancialTitleAdjustment.id == origin_id,
                    FinancialTitleAdjustment.company_id == company_id,
                    FinancialTitleAdjustment.deleted_at.is_(None),
                ).first()
                if not adjustment:
                    continue
                amount = FinancialService._money_decimal(getattr(component, "amount", 0))
                adjustment.settled_amount = max(
                    FinancialService._money_decimal(getattr(adjustment, "settled_amount", 0)) - amount,
                    Decimal("0.00"),
                )
                adjustment.open_amount = max(
                    FinancialService._money_decimal(getattr(adjustment, "generated_amount", 0))
                    - FinancialService._money_decimal(getattr(adjustment, "settled_amount", 0)),
                    Decimal("0.00"),
                )
                adjustment.status = "open" if adjustment.open_amount > 0 else "settled"

            if schedule is not None and entry is not None:
                hidden_log_ids = FinancialService._hide_superseded_calculation_logs(
                    company_id=company_id,
                    schedule_id=schedule.id,
                    settlement_id=settlement.id,
                    hidden_at=deleted_at,
                )
                after_balance = FinancialTitleBalanceService.calculate_for_schedule(
                    schedule=schedule,
                    reference_date=reference_date,
                )
                deletion_snapshot = FinancialService._build_deleted_settlement_snapshot(
                    entry=entry,
                    schedule=schedule,
                    settlement=settlement,
                    before_balance=before_balance or {},
                    after_balance=after_balance or {},
                    component_payloads=component_payloads,
                    deleted_at=deleted_at,
                )
                db.session.add(
                    FinancialTitleCalculationLog(
                        **FinancialService._build_title_calculation_log_payload(
                            entry=entry,
                            settlement=settlement,
                            snapshot=deletion_snapshot,
                            component_payloads=component_payloads,
                            event_type="settlement_deleted",
                            source="delete_settlement",
                            calculation_date=deleted_at.date(),
                            metadata_overrides={
                                "deletion_timestamp": deleted_at.isoformat(),
                                "hidden_superseded_log_ids": hidden_log_ids,
                            },
                        )
                    )
                )

            if entry:
                FinancialService._recalculate_entry_status(
                    entry=entry,
                    schedule=schedule,
                )

            db.session.commit()
            return {"message": "Baixa removida com sucesso.", "id": settlement.id}, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover baixa financeira %s", settlement_id)
            return None, f"Erro ao remover baixa: {str(exc)}"

    @staticmethod
    def delete_entry(
        *,
        entry_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        schedule = FinancialService._resolve_linked_schedule(entry, company_id)
        whole_delete_required = FinancialService._requires_whole_entry_delete(entry, schedule)
        active_settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
        ).all()

        if active_settlements and not whole_delete_required:
            return None, "Não é possível excluir um lançamento que ainda possui baixa ativa."

        reconciled_settlement = next(
            (
                settlement
                for settlement in active_settlements
                if str(getattr(settlement, "reconciliation_status", "") or "").strip().lower() in {"matched", "reconciled"}
            ),
            None,
        )
        if reconciled_settlement is not None:
            return None, "Não é possível excluir o lançamento porque a baixa já foi conciliada. Desfaça a conciliação antes de excluir."

        try:
            deleted_at = datetime.utcnow()
            entry.deleted_at = deleted_at
            entry.metadata_json = {
                **dict(getattr(entry, "metadata_json", {}) or {}),
                "deleted_with_whole_entry_flow": whole_delete_required,
                "deleted_at": deleted_at.isoformat(),
            }
            FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.company_id == company_id,
                FinancialEntryAllocation.financial_entry_id == entry.id,
                FinancialEntryAllocation.deleted_at.is_(None),
            ).update({"deleted_at": deleted_at}, synchronize_session=False)

            if schedule is not None and whole_delete_required:
                schedule.deleted_at = deleted_at
                schedule.metadata_json = {
                    **dict(getattr(schedule, "metadata_json", {}) or {}),
                    "deleted_with_whole_entry_flow": True,
                    "deleted_at": deleted_at.isoformat(),
                }

            for settlement in active_settlements:
                settlement.deleted_at = deleted_at
                settlement.metadata_json = {
                    **dict(getattr(settlement, "metadata_json", {}) or {}),
                    "deleted_at": deleted_at.isoformat(),
                    "deleted_with_whole_entry_flow": whole_delete_required,
                    "deleted_via": "financial_service.delete_entry",
                }

            db.session.commit()
            return {"message": "Lançamento financeiro removido com sucesso.", "id": entry.id}, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover lançamento financeiro %s", entry_id)
            return None, f"Erro ao remover lançamento financeiro: {str(exc)}"

    @staticmethod
    def _generate_settlement_code(company_id: int) -> str:
        # Códigos de baixa são únicos por empresa mesmo quando a baixa é excluída
        # logicamente. Portanto a geração não pode ignorar registros com deleted_at,
        # sob risco de reutilizar o código bloqueado pela constraint única.
        prefixes = ("BX", "LIQ")
        settlements = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
            )
            .order_by(FinancialSettlement.id.desc())
            .all()
        )
        max_number = 0
        for settlement in settlements or []:
            code = str(getattr(settlement, "settlement_code", "") or "").strip().upper()
            if not any(code.startswith(f"{prefix}-") for prefix in prefixes):
                continue
            try:
                max_number = max(max_number, int(code.split("-")[-1]))
            except Exception:
                max_number = max(max_number, int(getattr(settlement, "id", 0) or 0))
        return f"BX-{max_number + 1:06d}"

    @staticmethod
    def _is_auto_generated_settlement_code(code: Optional[str]) -> bool:
        normalized = str(code or "").strip().upper()
        if not normalized:
            return False
        for prefix in ("BX-", "LIQ-"):
            if not normalized.startswith(prefix):
                continue
            suffix = normalized[len(prefix):]
            return suffix.isdigit()
        return False

    @staticmethod
    def _normalize_requested_settlement_code(company_id: int, requested_code: Optional[str]) -> str:
        normalized = str(requested_code or "").strip().upper()
        if not normalized:
            return FinancialService._generate_settlement_code(company_id)

        existing = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.settlement_code == normalized,
        ).first()
        if not existing:
            return normalized

        if FinancialService._is_auto_generated_settlement_code(normalized):
            return FinancialService._generate_settlement_code(company_id)

        return normalized

    @staticmethod
    def upload_settlement_attachment(
        *,
        settlement_id: int,
        company_id: int,
        file: FileStorage,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Baixa financeira não encontrada no escopo da empresa."

        if not file or not file.filename:
            return None, "Nenhum arquivo informado."

        original_name = secure_filename(file.filename) or "anexo"
        attachment_id = uuid.uuid4().hex
        stored_name = f"{attachment_id}_{original_name}"
        relative_dir = os.path.join("financial_settlements", str(company_id), str(settlement.id))
        absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        absolute_path = os.path.join(absolute_dir, stored_name)
        file.save(absolute_path)

        metadata = dict(settlement.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        attachment = {
            "id": attachment_id,
            "name": original_name,
            "stored_name": stored_name,
            "content_type": file.mimetype,
            "size": os.path.getsize(absolute_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "url": f"/uploads/{relative_dir.replace(os.sep, '/')}/{stored_name}",
        }
        attachments.append(attachment)
        metadata["attachments"] = attachments
        settlement.metadata_json = metadata
        db.session.commit()
        return attachment, None

    @staticmethod
    def upload_entry_attachment(
        *,
        entry_id: int,
        company_id: int,
        file: FileStorage,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        if not file or not file.filename:
            return None, "Nenhum arquivo informado."

        original_name = secure_filename(file.filename) or "anexo"
        attachment_id = uuid.uuid4().hex
        stored_name = f"{attachment_id}_{original_name}"
        relative_dir = os.path.join("financial_entries", str(company_id), str(entry.id))
        absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        absolute_path = os.path.join(absolute_dir, stored_name)
        file.save(absolute_path)

        metadata = dict(entry.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        attachment = {
            "id": attachment_id,
            "name": original_name,
            "stored_name": stored_name,
            "content_type": file.mimetype,
            "size": os.path.getsize(absolute_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "url": f"/uploads/{relative_dir.replace(os.sep, '/')}/{stored_name}",
        }
        attachments.append(attachment)
        metadata["attachments"] = attachments
        entry.metadata_json = metadata
        db.session.commit()
        return attachment, None

    @staticmethod
    def delete_entry_attachment(
        *,
        entry_id: int,
        company_id: int,
        attachment_id: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        metadata = dict(entry.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        remaining: List[Dict[str, Any]] = []
        removed: Optional[Dict[str, Any]] = None
        for item in attachments:
            if str(item.get("id")) == str(attachment_id):
                removed = item
            else:
                remaining.append(item)

        if not removed:
            return None, "Anexo não encontrado para o lançamento."

        metadata["attachments"] = remaining
        entry.metadata_json = metadata
        db.session.commit()

        stored_name = removed.get("stored_name")
        if stored_name:
            absolute_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                "financial_entries",
                str(company_id),
                str(entry.id),
                stored_name,
            )
            if os.path.exists(absolute_path):
                os.remove(absolute_path)

        return removed, None

    @staticmethod
    def delete_settlement_attachment(
        *,
        settlement_id: int,
        company_id: int,
        attachment_id: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Baixa financeira não encontrada no escopo da empresa."

        metadata = dict(settlement.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        remaining: List[Dict[str, Any]] = []
        removed: Optional[Dict[str, Any]] = None
        for item in attachments:
            if str(item.get("id")) == str(attachment_id):
                removed = item
            else:
                remaining.append(item)

        if not removed:
            return None, "Anexo não encontrado para a baixa."

        metadata["attachments"] = remaining
        settlement.metadata_json = metadata
        db.session.commit()

        stored_name = removed.get("stored_name")
        if stored_name:
            absolute_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                "financial_settlements",
                str(company_id),
                str(settlement.id),
                stored_name,
            )
            if os.path.exists(absolute_path):
                os.remove(absolute_path)

        return removed, None

