from __future__ import annotations

import calendar
import logging
import os
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Counter as CounterType, Dict, List, Optional, Sequence, Tuple

from financial_domain import (
    FINANCIAL_OPERATIONAL_GLOSSARY,
    build_financial_title_contract_payload,
    build_title_operational_state_metadata,
    title_state_has_open_balance,
)
from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import db
from models.financial import (
    FinancialChartAccount,
    FinancialCorrectionIndex,
    FinancialCostCenter,
    FinancialDiscountRule,
    FinancialDomainEnablement,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSchedule,
    FinancialSettlement,
)
from models.financial_budget import FinancialBudgetContract, FinancialBudgetDocument, FinancialBudgetLine, FinancialBudgetVersion
from schemas.financial import FinancialScheduleCreateInput, FinancialScheduleUpdateInput
from services.financial_budget_schedule_policy import FinancialBudgetSchedulePolicy
from services.financial_catalog_service import FinancialCatalogService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_manual_domain_service import FinancialManualDomainService
from services.financial_service import FinancialService
from services.financial_title_amount_service import FinancialTitleAmountService
from services.financial_title_balance_service import FinancialTitleBalanceService


logger = logging.getLogger(__name__)


class FinancialScheduleService:
    AUTO_GENERATED_SCHEDULE_CODE_MAX_ATTEMPTS = 5
    COMPETENCE_MODE_SAME = "same_competence"
    COMPETENCE_MODE_DUE_DATE = "due_date"

    @staticmethod
    def _normalize_domain_source_kind(value: Any) -> str:
        return "manual" if str(value or "").strip().lower() == "manual" else "routine"

    @staticmethod
    def _build_domain_value(
        domain_type: Optional[str],
        domain_source_id: Optional[int],
        domain_source_kind: Optional[str] = None,
    ) -> str:
        if not domain_type or domain_source_id in ("", None):
            return ""
        normalized_kind = FinancialScheduleService._normalize_domain_source_kind(domain_source_kind)
        return f"{normalized_kind}:{domain_type}:{domain_source_id}"

    @staticmethod
    def _sanitize_json(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: FinancialScheduleService._sanitize_json(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [FinancialScheduleService._sanitize_json(item) for item in value]
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return FinancialScheduleService._sanitize_json(value.model_dump())
        return value

    @staticmethod
    def _is_direct_entry_schedule(schedule: Optional[FinancialSchedule]) -> bool:
        if schedule is None:
            return False
        metadata = dict(getattr(schedule, "metadata_json", {}) or {})
        return bool(metadata.get("direct_entry"))

    @staticmethod
    def _normalize_competence_mode(value: Any) -> str:
        return (
            FinancialScheduleService.COMPETENCE_MODE_DUE_DATE
            if str(value or "").strip() == FinancialScheduleService.COMPETENCE_MODE_DUE_DATE
            else FinancialScheduleService.COMPETENCE_MODE_SAME
        )

    @staticmethod
    def _normalize_schedule_metadata(metadata_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        metadata = FinancialScheduleService._sanitize_json(dict(metadata_json or {}))
        metadata["competence_mode"] = FinancialScheduleService._normalize_competence_mode(
            metadata.get("competence_mode")
        )
        return metadata

    @staticmethod
    def _resolve_generated_entry_competence_date(*, schedule: FinancialSchedule, due_date: Optional[date]) -> Optional[date]:
        metadata = dict(schedule.metadata_json or {})
        competence_mode = FinancialScheduleService._normalize_competence_mode(metadata.get("competence_mode"))
        if competence_mode == FinancialScheduleService.COMPETENCE_MODE_DUE_DATE:
            return due_date or getattr(schedule, "competence_date", None)
        return getattr(schedule, "competence_date", None) or due_date

    @staticmethod
    def _format_schedule_payload_error(exc: Exception, *, operation: str) -> str:
        message = str(exc)
        if "first_due_date não pode ser menor que competence_date" in message:
            return (
                f"Payload inválido para {operation} do agendamento: "
                "o vencimento não pode ser anterior à competência."
            )
        if "next_due_date não pode ser menor que first_due_date" in message:
            return (
                f"Payload inválido para {operation} do agendamento: "
                "a próxima data de vencimento não pode ser anterior ao primeiro vencimento."
            )
        if "end_date não pode ser menor que start_date" in message:
            return (
                f"Payload inválido para {operation} do agendamento: "
                "a data final não pode ser anterior à competência."
            )
        return f"Payload inválido para {operation} do agendamento: {exc}"

    @staticmethod
    def _has_active_settlements(*, company_id: int, schedule_id: int) -> bool:
        entry_ids = [
            int(entry_id)
            for (entry_id,) in (
                db.session.query(FinancialEntry.id)
                .filter(
                    FinancialEntry.company_id == company_id,
                    db.or_(
                        FinancialEntry.financial_schedule_id == schedule_id,
                        FinancialEntry.external_reference == f"financial_schedule:{schedule_id}",
                    ),
                    FinancialEntry.deleted_at.is_(None),
                )
                .all()
            )
            if entry_id is not None
        ]
        query = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
        )
        if entry_ids:
            query = query.filter(
                db.or_(
                    FinancialSettlement.financial_entry_id.in_(entry_ids),
                    FinancialSettlement.external_reference == f"financial_schedule:{schedule_id}",
                )
            )
        else:
            query = query.filter(FinancialSettlement.external_reference == f"financial_schedule:{schedule_id}")
        return query.first() is not None

    @staticmethod
    def list_schedules(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        status: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        )
        if status:
            query = query.filter(FinancialSchedule.status == status)

        schedules = query.order_by(FinancialSchedule.next_due_date.asc(), FinancialSchedule.id.desc()).all()
        return [FinancialScheduleService._serialize_schedule(schedule, include_summary=True) for schedule in schedules], None

    @staticmethod
    def get_schedule_detail(
        *,
        schedule_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."

        return FinancialScheduleService._serialize_schedule(schedule, include_related_entries=True), None

    @staticmethod
    def build_budget_document_schedule_payload(
        *,
        company_id: int,
        document: FinancialBudgetDocument,
        contract: FinancialBudgetContract,
        line: FinancialBudgetLine,
        label: str,
        amount: Decimal,
        due_date: Any,
        competence_date: Any,
        notes: Optional[str],
        status: str,
        auto_post: Optional[bool],
        current_schedule: Optional[FinancialSchedule] = None,
        default_suggestions: Optional[Dict[str, Any]] = None,
        default_correction_index_id: Optional[int] = None,
        domain_type: Optional[str] = None,
        domain_source_kind: Optional[str] = None,
        domain_source_id: Optional[int] = None,
        domain_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        counterparty = getattr(document, "counterparty", None) or getattr(contract, "counterparty", None)
        default_suggestions = dict(default_suggestions or {})
        line_metadata = dict(getattr(line, "metadata_json", None) or {})
        contract_metadata = dict(getattr(contract, "metadata_json", None) or {})
        document_metadata = dict(getattr(document, "metadata_json", None) or {})
        existing_metadata = dict(getattr(current_schedule, "metadata_json", None) or {})
        base_metadata = {
            **default_suggestions,
            **line_metadata,
            **contract_metadata,
            **document_metadata,
            **existing_metadata,
        }

        normalized_label = str(label or "").strip()
        effective_notes = notes if notes is not None else (getattr(current_schedule, "notes", None) or None)
        effective_due_date = due_date
        effective_competence_date = competence_date or due_date
        effective_domain_type = domain_type
        effective_domain_source_kind = FinancialScheduleService._normalize_domain_source_kind(domain_source_kind)
        effective_domain_source_id = domain_source_id
        effective_domain_label = domain_label
        domain_value = FinancialScheduleService._build_domain_value(
            effective_domain_type,
            effective_domain_source_id,
            effective_domain_source_kind,
        )
        correction_index_id = base_metadata.get("correction_index_id") or default_correction_index_id
        allocation_notes = f"{normalized_label} | {document.title}"

        metadata_json = {
            **base_metadata,
            "budget_schedule_source": "financial_budget_workspace",
            "document_number": document.document_number or document.document_code,
            "correction_index_id": correction_index_id,
            "discount_rule_id": base_metadata.get("discount_rule_id"),
            "discount_amount_override": base_metadata.get("discount_amount_override", 0),
            "repeat_count": base_metadata.get("repeat_count", 1),
            "attachments": list(base_metadata.get("attachments") or []),
            "counterparty_name": getattr(counterparty, "name", None) or base_metadata.get("counterparty_name"),
            "budget_version_id": line.budget_version_id,
            "budget_version_code": getattr(getattr(line, "version", None), "code", None),
            "budget_line_id": line.id,
            "budget_line_code": line.line_code,
            "budget_contract_id": contract.id,
            "budget_contract_code": contract.contract_code,
            "budget_document_id": document.id,
            "budget_document_code": document.document_code,
            "budget_document_title": document.title,
            "contract_name": contract.name,
            "domain_type": effective_domain_type,
            "domain_source_kind": effective_domain_source_kind,
            "domain_source_id": effective_domain_source_id,
            "domain_label": effective_domain_label,
            "domain_value": domain_value,
        }
        metadata_json = FinancialScheduleService._normalize_schedule_metadata(metadata_json)
        metadata_json["allocations"] = FinancialScheduleService._build_budget_document_schedule_allocations(
            company_id=company_id,
            line=line,
            contract=contract,
            document=document,
            metadata_json=metadata_json,
            template_amount=amount,
            due_date=effective_due_date,
            allocation_notes=allocation_notes,
            domain_type=effective_domain_type,
            domain_source_kind=effective_domain_source_kind,
            domain_source_id=effective_domain_source_id,
            domain_label=effective_domain_label,
            domain_value=domain_value,
        )

        return {
            "company_id": company_id,
            "budget_line_id": line.id,
            "budget_contract_id": contract.id,
            "budget_document_id": document.id,
            "name": normalized_label,
            "entry_type": "receivable" if line.movement_nature == "credit" else "payable",
            "movement_nature": line.movement_nature,
            "origin_type": getattr(current_schedule, "origin_type", None) or "manual",
            "status": status,
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": effective_competence_date,
            "competence_date": effective_competence_date,
            "first_due_date": effective_due_date,
            "next_due_date": effective_due_date,
            "description": allocation_notes,
            "memo": effective_notes or getattr(current_schedule, "memo", None) or document.notes or contract.notes,
            "document_number_prefix": document.document_number
            or document.document_code
            or getattr(current_schedule, "document_number_prefix", None),
            "template_amount": amount,
            "counterparty_id": getattr(counterparty, "id", None)
            or getattr(current_schedule, "counterparty_id", None),
            "chart_account_id": line.chart_account_id,
            "cost_center_id": line.cost_center_id,
            "notes": effective_notes or normalized_label,
            "auto_post": bool(auto_post) if auto_post is not None else bool(getattr(current_schedule, "auto_post", False)),
            "metadata_json": metadata_json,
        }

    @staticmethod
    def _build_budget_document_schedule_allocations(
        *,
        company_id: int,
        line: FinancialBudgetLine,
        contract: FinancialBudgetContract,
        document: FinancialBudgetDocument,
        metadata_json: Dict[str, Any],
        template_amount: Decimal,
        due_date: Any,
        allocation_notes: str,
        domain_type: Optional[str],
        domain_source_kind: Optional[str],
        domain_source_id: Optional[int],
        domain_label: Optional[str],
        domain_value: str,
    ) -> List[Dict[str, Any]]:
        allocations: List[Dict[str, Any]] = [
            {
                "chart_account_id": line.chart_account_id,
                "cost_center_id": line.cost_center_id,
                "allocation_type": "amount",
                "percentage": 100,
                "allocated_amount": float(template_amount),
                "notes": allocation_notes,
                "domain_type": domain_type,
                "domain_source_kind": FinancialScheduleService._normalize_domain_source_kind(domain_source_kind),
                "domain_source_id": domain_source_id,
                "domain_label": domain_label,
                "domain_value": domain_value,
                "budget_version_id": line.budget_version_id,
                "budget_version_code": getattr(getattr(line, "version", None), "code", None),
                "budget_line_id": line.id,
                "budget_line_code": line.line_code,
                "budget_contract_id": contract.id,
                "budget_contract_code": contract.contract_code,
                "budget_document_id": document.id,
                "budget_document_code": document.document_code,
                "metadata_json": {
                    "adjustment_kind": None,
                    "adjustment_label": None,
                },
            }
        ]
        return allocations

    @staticmethod
    def _build_budget_document_adjustment_allocation(
        *,
        kind: str,
        label: str,
        amount: Decimal,
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
        domain_type: Optional[str],
        domain_source_kind: Optional[str],
        domain_source_id: Optional[int],
        domain_label: Optional[str],
        domain_value: str,
        notes: str,
    ) -> Dict[str, Any]:
        return {
            "chart_account_id": chart_account_id,
            "cost_center_id": cost_center_id,
            "allocation_type": "amount",
            "percentage": None,
            "allocated_amount": float(amount),
            "notes": notes,
            "domain_type": domain_type,
            "domain_source_kind": FinancialScheduleService._normalize_domain_source_kind(domain_source_kind),
            "domain_source_id": domain_source_id,
            "domain_label": domain_label,
            "domain_value": domain_value,
            "budget_version_id": None,
            "budget_version_code": None,
            "budget_line_id": None,
            "budget_line_code": None,
            "budget_contract_id": None,
            "budget_contract_code": None,
            "budget_document_id": None,
            "budget_document_code": None,
            "metadata_json": {
                "adjustment_kind": kind,
                "adjustment_label": label,
            },
        }

    @staticmethod
    def _resolve_adjustment_chart_account_id(
        *,
        company_id: int,
        adjustment_kind: str,
        adjustment_source_id: Optional[Any],
        fallback_chart_account_id: Optional[int],
    ) -> Optional[int]:
        if adjustment_source_id in ("", None):
            return fallback_chart_account_id

        model = FinancialCorrectionIndex if adjustment_kind == "correction" else FinancialDiscountRule
        try:
            normalized_source_id = int(adjustment_source_id)
        except (TypeError, ValueError):
            return fallback_chart_account_id

        adjustment_source = model.query.filter(
            model.id == normalized_source_id,
            model.company_id == company_id,
            model.deleted_at.is_(None),
            model.is_active.is_(True),
        ).first()
        if not adjustment_source:
            return fallback_chart_account_id

        chart_account_id = dict(adjustment_source.metadata_json or {}).get("chart_account_id")
        if chart_account_id in ("", None):
            return fallback_chart_account_id
        try:
            return int(chart_account_id)
        except (TypeError, ValueError):
            return fallback_chart_account_id

    @staticmethod
    def create_schedule(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        auto_commit: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_payload = dict(payload or {})
        company_id = normalized_payload.get("company_id")
        auto_generated_code = bool(company_id and not normalized_payload.get("schedule_code"))
        if auto_generated_code:
            normalized_payload["schedule_code"] = FinancialScheduleService._generate_schedule_code(int(company_id))

        try:
            data = FinancialScheduleCreateInput(**normalized_payload)
        except Exception as exc:
            return None, FinancialScheduleService._format_schedule_payload_error(exc, operation="criação")

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        expected_movement_nature = FinancialScheduleService._expected_movement_nature(data.entry_type)
        if data.movement_nature != expected_movement_nature:
            return None, "movement_nature inválido para o tipo do agendamento informado."

        validation_error = FinancialScheduleService._validate_schedule_links(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
            counterparty_id=data.counterparty_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            activity_id=data.activity_id,
            process_instance_id=data.process_instance_id,
            routine_id=data.routine_id,
        )
        if validation_error:
            return None, validation_error

        normalized_metadata_json = dict(data.metadata_json or {})
        if data.allocations:
            normalized_metadata_json["allocations"] = FinancialScheduleService._sanitize_json(
                [item.model_dump() for item in data.allocations]
            )
        normalized_metadata_json["allocations"] = FinancialScheduleService._normalize_schedule_allocations(
            company_id=data.company_id,
            template_amount=data.template_amount,
            due_date=data.next_due_date or data.first_due_date,
            metadata_json=normalized_metadata_json,
            fallback_chart_account_id=data.chart_account_id,
            fallback_cost_center_id=data.cost_center_id,
            fallback_domain_type=normalized_metadata_json.get("domain_type"),
            fallback_domain_source_kind=normalized_metadata_json.get("domain_source_kind"),
            fallback_domain_source_id=normalized_metadata_json.get("domain_source_id"),
            fallback_domain_label=normalized_metadata_json.get("domain_label"),
        )

        allocation_error = FinancialScheduleService._validate_schedule_allocations(
            company_id=data.company_id,
            template_amount=data.template_amount,
            due_date=data.next_due_date or data.first_due_date,
            metadata_json=normalized_metadata_json,
        )
        if allocation_error:
            return None, allocation_error

        allocation_budget_links = FinancialScheduleService._derive_budget_links_from_allocations(
            metadata_json=normalized_metadata_json,
        )

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=data.company_id,
            budget_line_id=getattr(data, "budget_line_id", None) or allocation_budget_links.get("budget_line_id"),
            budget_contract_id=getattr(data, "budget_contract_id", None) or allocation_budget_links.get("budget_contract_id"),
            budget_document_id=getattr(data, "budget_document_id", None) or allocation_budget_links.get("budget_document_id"),
        )
        if budget_error:
            return None, budget_error

        budget_document_error = FinancialBudgetSchedulePolicy.validate_document_schedule_amount(
            company_id=data.company_id,
            budget_document_id=(budget_links or {}).get("budget_document_id"),
            requested_amount=data.template_amount,
            allowed_company_ids=allowed_company_ids,
        )
        if budget_document_error:
            return None, budget_document_error

        existing = FinancialScheduleService._find_schedule_by_code(
            company_id=data.company_id,
            schedule_code=data.schedule_code,
        )
        if existing and not auto_generated_code:
            return None, f"Já existe agendamento com código {data.schedule_code} para esta empresa."

        normalized = data.model_dump(exclude={"allocations"})
        normalized.update(budget_links or {})
        normalized["competence_date"] = normalized.get("competence_date") or normalized.get("start_date")
        normalized["metadata_json"] = FinancialScheduleService._normalize_schedule_metadata(
            FinancialService._merge_budget_metadata(
                normalized_metadata_json,
                budget_links,
            )
        )
        normalized["next_due_date"] = normalized.get("next_due_date") or normalized["first_due_date"]
        max_attempts = FinancialScheduleService.AUTO_GENERATED_SCHEDULE_CODE_MAX_ATTEMPTS if auto_generated_code else 1
        current_schedule_code = normalized["schedule_code"]

        try:
            for attempt in range(max_attempts):
                payload_to_persist = dict(normalized)
                if auto_generated_code:
                    if attempt > 0:
                        current_schedule_code = FinancialScheduleService._generate_schedule_code(data.company_id)
                    payload_to_persist["schedule_code"] = current_schedule_code

                schedule = FinancialSchedule(**payload_to_persist)
                db.session.add(schedule)
                try:
                    if auto_commit:
                        db.session.commit()
                    else:
                        db.session.flush()
                    return FinancialScheduleService._serialize_schedule(schedule), None
                except IntegrityError as exc:
                    db.session.rollback()
                    if auto_generated_code and FinancialScheduleService._is_schedule_code_unique_violation(exc):
                        logger.warning(
                            "Conflito ao gerar schedule_code automático para company_id=%s; tentativa=%s/%s",
                            data.company_id,
                            attempt + 1,
                            max_attempts,
                        )
                        continue
                    if FinancialScheduleService._is_schedule_code_unique_violation(exc):
                        return None, (
                            f"Já existe Título Financeiro com código {payload_to_persist['schedule_code']} para esta empresa."
                        )
                    raise
            return None, "Não foi possível gerar um código único para o Título Financeiro. Tente novamente."
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar título financeiro")
            return None, f"Erro ao criar Título Financeiro: {exc}"

    @staticmethod
    def update_schedule(
        *,
        schedule_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        auto_commit: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialScheduleUpdateInput(**payload)
        except Exception as exc:
            return None, FinancialScheduleService._format_schedule_payload_error(exc, operation="atualização")

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
        if active_bordero:
            return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."
        if FinancialScheduleService._has_active_settlements(company_id=company_id, schedule_id=schedule.id):
            return None, "Título Financeiro com baixa registrada. Remova as baixas antes de alterar o cadastro do título."

        allocations_in_payload = "allocations" in data.model_fields_set
        raw_allocations = [item.model_dump() for item in data.allocations] if allocations_in_payload else None

        merged = data.model_dump(exclude_unset=True, exclude={"allocations"})
        if "schedule_code" in merged:
            if merged["schedule_code"] != schedule.schedule_code:
                return None, "O código do Título Financeiro não pode ser alterado após a criação."
            merged.pop("schedule_code", None)
        if "metadata_json" in merged:
            merged["metadata_json"] = FinancialScheduleService._sanitize_json(merged.get("metadata_json") or {})
        if "entry_type" in merged and merged["entry_type"] != schedule.entry_type:
            return None, "O tipo do Título Financeiro (pagamento/recebimento) não pode ser alterado após a criação."
        if "movement_nature" in merged and merged["movement_nature"] != schedule.movement_nature:
            return None, "A natureza do movimento do Título Financeiro não pode ser alterada após a criação."
        validation_error = FinancialScheduleService._validate_schedule_links(
            company_id=company_id,
            bank_account_id=merged.get("bank_account_id", schedule.bank_account_id),
            counterparty_id=merged.get("counterparty_id", schedule.counterparty_id),
            chart_account_id=merged.get("chart_account_id", schedule.chart_account_id),
            cost_center_id=merged.get("cost_center_id", schedule.cost_center_id),
            activity_id=merged.get("activity_id", schedule.activity_id),
            process_instance_id=merged.get("process_instance_id", schedule.process_instance_id),
            routine_id=merged.get("routine_id", schedule.routine_id),
        )
        if validation_error:
            return None, validation_error

        merged_metadata_json = dict(merged.get("metadata_json", schedule.metadata_json) or {})
        if raw_allocations is not None:
            merged_metadata_json["allocations"] = FinancialScheduleService._sanitize_json(raw_allocations)
        merged_metadata_json["allocations"] = FinancialScheduleService._normalize_schedule_allocations(
            company_id=company_id,
            template_amount=merged.get("template_amount", schedule.template_amount),
            due_date=merged.get("next_due_date", merged.get("first_due_date", schedule.next_due_date or schedule.first_due_date)),
            metadata_json=merged_metadata_json,
            fallback_chart_account_id=merged.get("chart_account_id", schedule.chart_account_id),
            fallback_cost_center_id=merged.get("cost_center_id", schedule.cost_center_id),
            fallback_domain_type=merged_metadata_json.get("domain_type"),
            fallback_domain_source_kind=merged_metadata_json.get("domain_source_kind"),
            fallback_domain_source_id=merged_metadata_json.get("domain_source_id"),
            fallback_domain_label=merged_metadata_json.get("domain_label"),
        )
        legacy_domain_allowance = FinancialScheduleService._build_legacy_domain_allowance(
            company_id=company_id,
            template_amount=schedule.template_amount,
            due_date=schedule.next_due_date or schedule.first_due_date,
            metadata_json=schedule.metadata_json,
            fallback_chart_account_id=schedule.chart_account_id,
            fallback_cost_center_id=schedule.cost_center_id,
            fallback_domain_type=dict(schedule.metadata_json or {}).get("domain_type"),
            fallback_domain_source_kind=dict(schedule.metadata_json or {}).get("domain_source_kind"),
            fallback_domain_source_id=dict(schedule.metadata_json or {}).get("domain_source_id"),
            fallback_domain_label=dict(schedule.metadata_json or {}).get("domain_label"),
        )

        allocation_error = FinancialScheduleService._validate_schedule_allocations(
            company_id=company_id,
            template_amount=merged.get("template_amount", schedule.template_amount),
            due_date=merged.get("next_due_date", merged.get("first_due_date", schedule.next_due_date or schedule.first_due_date)),
            metadata_json=merged_metadata_json,
            legacy_domain_allowance=legacy_domain_allowance,
        )
        if allocation_error:
            return None, allocation_error

        allocation_budget_links = FinancialScheduleService._derive_budget_links_from_allocations(
            metadata_json=merged_metadata_json,
        )

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=company_id,
            budget_line_id=merged.get("budget_line_id", getattr(schedule, "budget_line_id", None)) or allocation_budget_links.get("budget_line_id"),
            budget_contract_id=merged.get("budget_contract_id", getattr(schedule, "budget_contract_id", None)) or allocation_budget_links.get("budget_contract_id"),
            budget_document_id=merged.get("budget_document_id", getattr(schedule, "budget_document_id", None)) or allocation_budget_links.get("budget_document_id"),
        )
        if budget_error:
            return None, budget_error

        budget_document_error = FinancialBudgetSchedulePolicy.validate_document_schedule_amount(
            company_id=company_id,
            budget_document_id=(budget_links or {}).get("budget_document_id"),
            requested_amount=merged.get("template_amount", schedule.template_amount),
            allowed_company_ids=allowed_company_ids,
            exclude_schedule_id=schedule.id,
        )
        if budget_document_error:
            return None, budget_document_error

        start_date = merged.get("start_date", schedule.start_date)
        competence_date = merged.get("competence_date", getattr(schedule, "competence_date", None) or start_date)
        end_date = merged.get("end_date", schedule.end_date)
        first_due_date = merged.get("first_due_date", schedule.first_due_date)
        next_due_date = merged.get("next_due_date", schedule.next_due_date)
        if end_date and start_date and end_date < start_date:
            return None, "end_date não pode ser menor que start_date."
        if first_due_date and competence_date and first_due_date < competence_date:
            return None, "first_due_date não pode ser menor que competence_date."
        if next_due_date and first_due_date and next_due_date < first_due_date:
            return None, "next_due_date não pode ser menor que first_due_date."

        try:
            merged.update(budget_links or {})
            merged["competence_date"] = competence_date
            merged["metadata_json"] = FinancialScheduleService._normalize_schedule_metadata(
                FinancialService._merge_budget_metadata(
                    merged_metadata_json,
                    budget_links,
                )
            )
            for key, value in merged.items():
                setattr(schedule, key, value)
            if auto_commit:
                db.session.commit()
            else:
                db.session.flush()
            return FinancialScheduleService._serialize_schedule(schedule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar título financeiro %s", schedule_id)
            return None, f"Erro ao atualizar Título Financeiro: {exc}"

    @staticmethod
    def toggle_schedule(
        *,
        schedule_id: int,
        company_id: int,
        status: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
        if active_bordero:
            return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."

        if status not in {"active", "paused", "cancelled", "completed", "draft"}:
            return None, "Status inválido para o Título Financeiro."

        try:
            schedule.status = status
            db.session.commit()
            return FinancialScheduleService._serialize_schedule(schedule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao alterar status do título financeiro %s", schedule_id)
            return None, f"Erro ao alterar status do Título Financeiro: {exc}"

    @staticmethod
    def delete_schedule(
        *,
        schedule_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
        if active_bordero:
            return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."

        generated_entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.external_reference == f"financial_schedule:{schedule.id}",
            FinancialEntry.deleted_at.is_(None),
        ).all()
        direct_entry_schedule = FinancialScheduleService._is_direct_entry_schedule(schedule)
        active_settlements: List[FinancialSettlement] = []
        now = datetime.utcnow()
        for entry in generated_entries:
            entry_active_settlements = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            ).all()
            if not entry_active_settlements:
                continue
            if not direct_entry_schedule:
                return None, "Não é possível excluir um Título Financeiro que já possui baixas. Cancele-o ou edite-o."
            active_settlements.extend(entry_active_settlements)

        if direct_entry_schedule:
            reconciled_settlement = next(
                (
                    settlement
                    for settlement in active_settlements
                    if str(getattr(settlement, "reconciliation_status", "") or "").strip().lower() in {"matched", "reconciled"}
                ),
                None,
            )
            if reconciled_settlement is not None:
                return None, (
                    "Não é possível excluir o lançamento rápido inteiro porque a baixa já foi conciliada. "
                    "Desfaça a conciliação antes de excluir."
                )

        try:
            schedule.deleted_at = now
            schedule.metadata_json = {
                **dict(getattr(schedule, "metadata_json", None) or {}),
                "deleted_with_direct_entry_flow": direct_entry_schedule,
            }
            for entry in generated_entries:
                entry.deleted_at = now
                metadata = dict(getattr(entry, "metadata_json", None) or {})
                metadata["deleted_with_schedule"] = True
                metadata["deleted_with_direct_entry_flow"] = direct_entry_schedule
                entry.metadata_json = metadata
                FinancialEntryAllocation.query.filter(
                    FinancialEntryAllocation.company_id == company_id,
                    FinancialEntryAllocation.financial_entry_id == entry.id,
                    FinancialEntryAllocation.deleted_at.is_(None),
                ).update({"deleted_at": now}, synchronize_session=False)
            for settlement in active_settlements:
                settlement.deleted_at = now
                settlement.metadata_json = {
                    **dict(getattr(settlement, "metadata_json", None) or {}),
                    "deleted_at": now.isoformat(),
                    "deleted_with_schedule": True,
                    "deleted_with_direct_entry_flow": True,
                    "deleted_via": "financial_schedule_service.delete_schedule",
                }
            db.session.commit()
            return {"message": "Título Financeiro removido com sucesso.", "id": schedule_id}, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover título financeiro %s", schedule_id)
            return None, f"Erro ao remover Título Financeiro: {exc}"

    @staticmethod
    def create_entry_from_schedule(
        *,
        schedule_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        ignore_bordero_lock: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        if not ignore_bordero_lock:
            from services.financial_bordero_service import FinancialBorderoService

            active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
            if active_bordero:
                return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."

        due_date = schedule.next_due_date or schedule.first_due_date
        if not due_date:
            return None, "Título Financeiro sem vencimento disponível para gerar baixa."

        entry_code = f"{schedule.schedule_code}-{due_date.isoformat()}"
        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.entry_code == entry_code,
        ).first()
        if existing:
            entry_payload = FinancialScheduleService._build_entry_payload(
                schedule=schedule,
                entry_code=entry_code,
                force_posted=True,
                occurrence_date=due_date,
            )
            existing.original_amount = entry_payload["original_amount"]
            existing.issue_date = entry_payload["issue_date"]
            existing.competence_date = entry_payload["competence_date"]
            existing.due_date = entry_payload["due_date"]
            existing.occurred_on = entry_payload["occurred_on"]
            existing.status = entry_payload["status"]
            existing.review_status = entry_payload["review_status"]
            existing.chart_account_id = entry_payload["chart_account_id"]
            existing.cost_center_id = entry_payload["cost_center_id"]
            existing.metadata_json = entry_payload["metadata_json"]
            allocation_error = FinancialScheduleService._apply_schedule_allocations(
                schedule=schedule,
                entry_id=existing.id,
                allowed_company_ids=allowed_company_ids,
            )
            if allocation_error:
                return None, allocation_error
            db.session.commit()
            return {"entry": FinancialService.serialize_entry(existing), "created": False}, None

        entry_payload = FinancialScheduleService._build_entry_payload(
            schedule=schedule,
            entry_code=entry_code,
            force_posted=True,
            occurrence_date=due_date,
        )
        entry, error = FinancialService.create_entry(
            payload=entry_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        allocation_error = FinancialScheduleService._apply_schedule_allocations(
            schedule=schedule,
            entry_id=entry.id,
            allowed_company_ids=allowed_company_ids,
        )
        if allocation_error:
            return None, allocation_error

        schedule.last_generated_at = datetime.utcnow()
        schedule.last_generated_entry_id = entry.id
        if schedule.status == "draft":
            schedule.status = "active"
        db.session.commit()
        return {"entry": FinancialService.serialize_entry(entry), "created": True}, None

    @staticmethod
    def create_settlement_from_schedule(
        *,
        schedule_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."

        entry_result, entry_error = FinancialScheduleService.create_entry_from_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
            ignore_bordero_lock=True,
        )
        if entry_error:
            return None, entry_error

        entry_payload = entry_result.get("entry") if isinstance(entry_result, dict) else None
        entry_id = entry_payload.get("id") if isinstance(entry_payload, dict) else None
        if not entry_id:
            return None, "Não foi possível identificar o lançamento vinculado ao título financeiro."

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro gerado não encontrado no escopo da empresa."

        settlement_payload = dict(payload or {})
        settlement_payload.pop("settlement_code", None)
        settlement_payload["company_id"] = company_id
        settlement_payload["financial_entry_id"] = entry_id
        settlement_payload["external_reference"] = f"financial_schedule:{schedule.id}"

        settlement, settlement_error = FinancialService.create_settlement(
            payload=settlement_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if settlement_error:
            return None, settlement_error

        return {
            "entry": FinancialService.serialize_entry(entry),
            "settlement": FinancialService.serialize_settlement(
                settlement,
                entry=entry,
                schedule=schedule,
                include_components=True,
            ),
            "created_entry": bool(entry_result.get("created")) if isinstance(entry_result, dict) else False,
        }, None

    @staticmethod
    def generate_due_entries(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        schedule_id: Optional[int] = None,
        run_until: Optional[date] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        run_until = run_until or date.today()
        query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
            FinancialSchedule.status == "active",
        )
        if schedule_id:
            query = query.filter(FinancialSchedule.id == schedule_id)

        schedules = query.order_by(FinancialSchedule.next_due_date.asc(), FinancialSchedule.id.asc()).all()
        generated_entries: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []

        try:
            for schedule in schedules:
                effective_limit = run_until + timedelta(days=int(schedule.generate_advance_days or 0))
                while schedule.next_due_date and schedule.next_due_date <= effective_limit:
                    if schedule.end_date and schedule.next_due_date > schedule.end_date:
                        schedule.status = "completed"
                        break

                    entry_code = f"{schedule.schedule_code}-{schedule.next_due_date.isoformat()}"
                    existing = FinancialEntry.query.filter(
                        FinancialEntry.company_id == company_id,
                        FinancialEntry.entry_code == entry_code,
                    ).first()
                    if existing:
                        skipped.append(
                            {
                                "schedule_id": schedule.id,
                                "entry_code": entry_code,
                                "reason": "entry_already_exists",
                            }
                        )
                    else:
                        entry_payload = FinancialScheduleService._build_entry_payload(
                            schedule=schedule,
                            entry_code=entry_code,
                        )
                        entry, error = FinancialService.create_entry(
                            payload=entry_payload,
                            allowed_company_ids=allowed_company_ids,
                        )
                        if error:
                            skipped.append(
                                {
                                    "schedule_id": schedule.id,
                                    "entry_code": entry_code,
                                    "reason": error,
                                }
                            )
                            break
                        allocation_error = FinancialScheduleService._apply_schedule_allocations(
                            schedule=schedule,
                            entry_id=entry.id,
                            allowed_company_ids=allowed_company_ids,
                        )
                        if allocation_error:
                            skipped.append(
                                {
                                    "schedule_id": schedule.id,
                                    "entry_code": entry_code,
                                    "reason": allocation_error,
                                }
                            )
                            break
                        generated_entries.append(FinancialService.serialize_entry(entry, include_children=False))
                        schedule.last_generated_at = datetime.utcnow()
                        schedule.last_generated_entry_id = entry.id

                    next_due = FinancialScheduleService._calculate_next_due_date(schedule, schedule.next_due_date)
                    if not next_due or (schedule.end_date and next_due > schedule.end_date):
                        schedule.status = "completed"
                        break
                    schedule.next_due_date = next_due

            db.session.commit()
            return {
                "company_id": company_id,
                "run_until": run_until.isoformat(),
                "generated_count": len(generated_entries),
                "skipped_count": len(skipped),
                "generated_entries": generated_entries,
                "skipped": skipped,
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao gerar lançamentos a partir de agendamentos financeiros")
            return None, f"Erro ao gerar lançamentos financeiros agendados: {exc}"

    @staticmethod
    def upload_attachment(
        *,
        schedule_id: int,
        company_id: int,
        file: FileStorage,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
        if active_bordero:
            return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."

        if not file or not file.filename:
            return None, "Nenhum arquivo informado."

        original_name = secure_filename(file.filename) or "anexo"
        attachment_id = uuid.uuid4().hex
        stored_name = f"{attachment_id}_{original_name}"
        relative_dir = os.path.join("financial_schedules", str(company_id), str(schedule.id))
        absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        absolute_path = os.path.join(absolute_dir, stored_name)
        file.save(absolute_path)

        metadata = dict(schedule.metadata_json or {})
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
        schedule.metadata_json = metadata
        db.session.commit()
        return attachment, None

    @staticmethod
    def delete_attachment(
        *,
        schedule_id: int,
        company_id: int,
        attachment_id: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Título Financeiro não encontrado no escopo da empresa."
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule.id)
        if active_bordero:
            return None, f"Título Financeiro bloqueado pelo borderô {active_bordero.bordero_code}. Consulte o borderô para realizar baixas."

        metadata = dict(schedule.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        remaining: List[Dict[str, Any]] = []
        removed: Optional[Dict[str, Any]] = None
        for item in attachments:
            if str(item.get("id")) == str(attachment_id):
                removed = item
            else:
                remaining.append(item)

        if not removed:
            return None, "Anexo não encontrado para o agendamento."

        metadata["attachments"] = remaining
        schedule.metadata_json = metadata
        db.session.commit()

        stored_name = removed.get("stored_name")
        if stored_name:
            relative_dir = os.path.join("financial_schedules", str(company_id), str(schedule.id))
            absolute_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_dir, stored_name)
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
        return removed, None

    @staticmethod
    def _build_entry_payload(
        *,
        schedule: FinancialSchedule,
        entry_code: str,
        force_posted: bool = False,
        occurrence_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        due_date = occurrence_date or schedule.next_due_date or schedule.first_due_date
        adjustment_totals = FinancialScheduleService._calculate_schedule_adjustments(
            company_id=schedule.company_id,
            template_amount=schedule.template_amount,
            metadata_json=schedule.metadata_json,
            due_date=due_date,
        )
        budget_links = {
            "budget_line_id": getattr(schedule, "budget_line_id", None),
            "budget_contract_id": getattr(schedule, "budget_contract_id", None),
            "budget_document_id": getattr(schedule, "budget_document_id", None),
        }
        metadata = FinancialService._merge_budget_metadata(dict(schedule.metadata_json or {}), budget_links)
        status = "posted" if (schedule.auto_post or force_posted) else "scheduled"
        document_number = None
        explicit_document = str(metadata.get("document_number") or "").strip()
        if explicit_document:
            if schedule.frequency == "one_time" or force_posted:
                document_number = explicit_document
            elif due_date:
                document_number = f"{explicit_document}-{due_date.strftime('%Y%m%d')}"
        elif schedule.document_number_prefix and due_date:
            document_number = f"{schedule.document_number_prefix}-{due_date.strftime('%Y%m%d')}"

        competence_date = FinancialScheduleService._resolve_generated_entry_competence_date(
            schedule=schedule,
            due_date=due_date,
        )
        competence_mode = FinancialScheduleService._normalize_competence_mode(metadata.get("competence_mode"))

        return {
            "company_id": schedule.company_id,
            "entry_code": entry_code,
            "entry_type": schedule.entry_type,
            "movement_nature": schedule.movement_nature,
            "origin_type": schedule.origin_type,
            "status": status,
            "review_status": "approved" if (schedule.auto_post or force_posted) else "pending_review",
            "description": schedule.description,
            "memo": schedule.memo,
            "document_number": document_number,
            "external_reference": f"financial_schedule:{schedule.id}",
            "origin_reference": schedule.schedule_code,
            "financial_schedule_id": schedule.id,
            "issue_date": due_date,
            "competence_date": competence_date,
            "due_date": due_date,
            "occurred_on": due_date if (schedule.auto_post or force_posted) else None,
            "original_amount": Decimal(str(adjustment_totals.get("updated_amount") or schedule.template_amount or 0)),
            "currency_code": schedule.currency_code,
            "bank_account_id": schedule.bank_account_id,
            "counterparty_id": schedule.counterparty_id,
            "chart_account_id": schedule.chart_account_id,
            "cost_center_id": schedule.cost_center_id,
            "budget_line_id": getattr(schedule, "budget_line_id", None),
            "budget_contract_id": getattr(schedule, "budget_contract_id", None),
            "budget_document_id": getattr(schedule, "budget_document_id", None),
            "activity_id": schedule.activity_id,
            "process_instance_id": schedule.process_instance_id,
            "routine_id": schedule.routine_id,
            "created_by_user_id": schedule.created_by_user_id,
            "created_by_employee_id": schedule.created_by_employee_id,
            "created_by_agent": schedule.created_by_agent,
            "notes": schedule.notes,
            "metadata_json": {
                **metadata,
                "financial_schedule_id": schedule.id,
                "generated_from_schedule": True,
                "schedule_template_amount": adjustment_totals.get("template_amount"),
                "schedule_correction_amount": adjustment_totals.get("correction_amount"),
                "schedule_discount_amount": adjustment_totals.get("discount_amount"),
                "schedule_updated_amount": adjustment_totals.get("updated_amount"),
                "schedule_due_date": due_date.isoformat() if due_date else None,
                "schedule_competence_date": competence_date.isoformat() if competence_date else None,
                "schedule_competence_mode": competence_mode,
            },
        }

    @staticmethod
    def _apply_schedule_allocations(
        *,
        schedule: FinancialSchedule,
        entry_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Optional[str]:
        metadata = dict(schedule.metadata_json or {})
        raw_allocations = FinancialScheduleService._normalize_schedule_allocations(
            company_id=schedule.company_id,
            template_amount=schedule.template_amount,
            due_date=schedule.next_due_date or schedule.first_due_date,
            metadata_json=metadata,
            fallback_chart_account_id=getattr(schedule, "chart_account_id", None),
            fallback_cost_center_id=getattr(schedule, "cost_center_id", None),
            fallback_domain_type=metadata.get("domain_type"),
            fallback_domain_source_kind=metadata.get("domain_source_kind"),
            fallback_domain_source_id=metadata.get("domain_source_id"),
            fallback_domain_label=metadata.get("domain_label"),
        )
        if not raw_allocations:
            return None

        if raw_allocations != list(metadata.get("allocations") or []):
            metadata["allocations"] = FinancialScheduleService._sanitize_json(raw_allocations)
            schedule.metadata_json = metadata

        payload = {
            "company_id": schedule.company_id,
            "financial_entry_id": entry_id,
            "allocations": [],
        }
        for item in raw_allocations:
            row_metadata = dict(item.get("metadata_json") or {})
            payload["allocations"].append(
                {
                    "company_id": schedule.company_id,
                    "financial_entry_id": entry_id,
                    "chart_account_id": item.get("chart_account_id"),
                    "cost_center_id": item.get("cost_center_id"),
                    "allocation_type": item.get("allocation_type") or "percentage",
                    "percentage": item.get("percentage"),
                    "allocated_amount": item.get("allocated_amount"),
                    "notes": item.get("notes"),
                    "metadata_json": {
                        **row_metadata,
                        "domain_type": item.get("domain_type"),
                        "domain_source_kind": item.get("domain_source_kind"),
                        "domain_source_id": item.get("domain_source_id"),
                        "domain_label": item.get("domain_label"),
                        "budget_version_id": item.get("budget_version_id"),
                        "budget_version_code": item.get("budget_version_code"),
                        "budget_line_id": item.get("budget_line_id"),
                        "budget_line_code": item.get("budget_line_code"),
                        "budget_contract_id": item.get("budget_contract_id"),
                        "budget_contract_code": item.get("budget_contract_code"),
                        "budget_document_id": item.get("budget_document_id"),
                        "budget_document_code": item.get("budget_document_code"),
                    },
                }
            )

        _, error = FinancialService.replace_allocations(
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )
        return error

    @staticmethod
    def _normalize_schedule_allocations(
        *,
        company_id: int,
        template_amount: Any,
        due_date: Optional[date],
        metadata_json: Optional[Dict[str, Any]],
        fallback_chart_account_id: Optional[int] = None,
        fallback_cost_center_id: Optional[int] = None,
        fallback_domain_type: Optional[str] = None,
        fallback_domain_source_kind: Optional[str] = None,
        fallback_domain_source_id: Optional[int] = None,
        fallback_domain_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        metadata = dict(metadata_json or {})
        raw_allocations = list(metadata.get("allocations") or [])
        if not raw_allocations:
            return []

        normalized_allocations: List[Dict[str, Any]] = []
        for item in raw_allocations:
            row = dict(item or {})
            row_metadata = dict(row.get("metadata_json") or {})
            adjustment_kind = str(row_metadata.get("adjustment_kind") or "").strip().lower()
            if adjustment_kind in {"correction", "discount"}:
                continue
            row["metadata_json"] = {
                **row_metadata,
                "adjustment_kind": None,
                "adjustment_label": None,
            }
            row["chart_account_id"] = row.get("chart_account_id") or fallback_chart_account_id
            row["cost_center_id"] = row.get("cost_center_id") or fallback_cost_center_id
            row["allocation_type"] = str(
                row.get("allocation_type")
                or ("amount" if row.get("allocated_amount") not in ("", None) else "percentage")
            ).strip().lower() or "percentage"
            row["domain_type"] = row.get("domain_type") or fallback_domain_type
            row["domain_source_id"] = row.get("domain_source_id") or fallback_domain_source_id
            row["domain_source_kind"] = (
                FinancialScheduleService._normalize_domain_source_kind(
                    row.get("domain_source_kind") or fallback_domain_source_kind
                )
                if row.get("domain_type") and row.get("domain_source_id") not in ("", None)
                else None
            )
            row["domain_label"] = row.get("domain_label") or fallback_domain_label
            row["domain_value"] = FinancialScheduleService._build_domain_value(
                row.get("domain_type"),
                row.get("domain_source_id"),
                row.get("domain_source_kind"),
            )
            normalized_allocations.append(row)

        return normalized_allocations

    @staticmethod
    def _build_allocation_domain_key(item: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str, int]]:
        row = dict(item or {})
        domain_type = str(row.get("domain_type") or "").strip().lower()
        domain_source_id = row.get("domain_source_id")
        if not domain_type or domain_source_id in ("", None):
            return None
        try:
            normalized_source_id = int(domain_source_id)
        except (TypeError, ValueError):
            return None
        domain_source_kind = FinancialScheduleService._normalize_domain_source_kind(
            row.get("domain_source_kind")
        )
        return (domain_source_kind, domain_type, normalized_source_id)

    @staticmethod
    def _build_legacy_domain_allowance(
        *,
        company_id: int,
        template_amount: Any,
        due_date: Optional[date],
        metadata_json: Optional[Dict[str, Any]],
        fallback_chart_account_id: Optional[int] = None,
        fallback_cost_center_id: Optional[int] = None,
        fallback_domain_type: Optional[str] = None,
        fallback_domain_source_kind: Optional[str] = None,
        fallback_domain_source_id: Optional[int] = None,
        fallback_domain_label: Optional[str] = None,
    ) -> CounterType[Tuple[str, str, int]]:
        counter: CounterType[Tuple[str, str, int]] = Counter()
        allocations = FinancialScheduleService._normalize_schedule_allocations(
            company_id=company_id,
            template_amount=template_amount,
            due_date=due_date,
            metadata_json=metadata_json,
            fallback_chart_account_id=fallback_chart_account_id,
            fallback_cost_center_id=fallback_cost_center_id,
            fallback_domain_type=fallback_domain_type,
            fallback_domain_source_kind=fallback_domain_source_kind,
            fallback_domain_source_id=fallback_domain_source_id,
            fallback_domain_label=fallback_domain_label,
        )
        for item in allocations:
            key = FinancialScheduleService._build_allocation_domain_key(item)
            if key:
                counter[key] += 1
        return counter

    @staticmethod
    def _validate_schedule_links(
        *,
        company_id: int,
        bank_account_id: Optional[int],
        counterparty_id: Optional[int],
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
        activity_id: Optional[int],
        process_instance_id: Optional[int],
        routine_id: Optional[int],
    ) -> Optional[str]:
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=bank_account_id,
            counterparty_id=counterparty_id,
            chart_account_id=chart_account_id,
            cost_center_id=cost_center_id,
        )
        if reference_error:
            return reference_error

        return FinancialService._validate_operational_links(
            company_id=company_id,
            activity_id=activity_id,
            process_instance_id=process_instance_id,
            routine_id=routine_id,
        )

    @staticmethod
    def _validate_schedule_allocations(
        *,
        company_id: int,
        template_amount: Any,
        due_date: Optional[date],
        metadata_json: Optional[Dict[str, Any]],
        legacy_domain_allowance: Optional[CounterType[Tuple[str, str, int]]] = None,
        existing_metadata_json: Optional[Dict[str, Any]] = None,
        existing_fallback_chart_account_id: Optional[int] = None,
        existing_fallback_cost_center_id: Optional[int] = None,
        existing_fallback_domain_type: Optional[str] = None,
        existing_fallback_domain_source_kind: Optional[str] = None,
        existing_fallback_domain_source_id: Optional[int] = None,
        existing_fallback_domain_label: Optional[str] = None,
    ) -> Optional[str]:
        allocations = list((metadata_json or {}).get("allocations") or [])
        if not allocations:
            return "Informe ao menos uma linha de rateio para o agendamento."

        resolved_legacy_domain_allowance = legacy_domain_allowance
        if resolved_legacy_domain_allowance is None and existing_metadata_json:
            resolved_legacy_domain_allowance = FinancialScheduleService._build_legacy_domain_allowance(
                company_id=company_id,
                template_amount=template_amount,
                due_date=due_date,
                metadata_json=existing_metadata_json,
                fallback_chart_account_id=existing_fallback_chart_account_id,
                fallback_cost_center_id=existing_fallback_cost_center_id,
                fallback_domain_type=existing_fallback_domain_type,
                fallback_domain_source_kind=existing_fallback_domain_source_kind,
                fallback_domain_source_id=existing_fallback_domain_source_id,
                fallback_domain_label=existing_fallback_domain_label,
            )

        totals = FinancialScheduleService._calculate_schedule_adjustments(
            company_id=company_id,
            template_amount=template_amount,
            metadata_json=metadata_json,
            due_date=due_date,
        )
        amount_total = Decimal(str(totals.get("template_amount") or template_amount or 0))
        percentage_total = Decimal("0")
        allocated_total = Decimal("0")
        allocation_mode: Optional[str] = None

        for index, item in enumerate(allocations, start=1):
            chart_account_id = item.get("chart_account_id")
            cost_center_id = item.get("cost_center_id")
            if not chart_account_id:
                return f"Selecione o plano de contas na linha {index} do rateio."
            if not cost_center_id:
                return f"Selecione o centro de resultado na linha {index} do rateio."

            budget_line_id = item.get("budget_line_id")
            budget_contract_id = item.get("budget_contract_id")
            budget_document_id = item.get("budget_document_id")
            if budget_line_id or budget_contract_id or budget_document_id:
                _, budget_error = FinancialService._resolve_budget_links(
                    company_id=company_id,
                    budget_line_id=budget_line_id,
                    budget_contract_id=budget_contract_id,
                    budget_document_id=budget_document_id,
                )
                if budget_error:
                    return f"Linha {index} do rateio: {budget_error}"

            chart_account = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == chart_account_id,
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not chart_account:
                return f"Plano de contas inválido na linha {index} do rateio."
            if not chart_account.accepts_posting:
                return f"O plano de contas da linha {index} do rateio precisa ser analítico."

            cost_center = FinancialCostCenter.query.filter(
                FinancialCostCenter.id == cost_center_id,
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if not cost_center:
                return f"Centro de resultado inválido na linha {index} do rateio."

            child_center = FinancialCostCenter.query.filter(
                FinancialCostCenter.parent_id == cost_center.id,
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if child_center:
                return f"O centro de resultado da linha {index} do rateio precisa ser analítico/final."

            domain_type = item.get("domain_type")
            domain_source_id = item.get("domain_source_id")
            domain_source_kind = item.get("domain_source_kind") or "routine"
            if domain_type and domain_source_id:
                domain_key = FinancialScheduleService._build_allocation_domain_key(
                    {
                        "domain_type": domain_type,
                        "domain_source_id": domain_source_id,
                        "domain_source_kind": domain_source_kind,
                    }
                )
                _, domain_error = FinancialDomainEnablementService._load_source(
                    company_id,
                    domain_type,
                    int(domain_source_id),
                    source_kind=domain_source_kind,
                )
                if domain_error:
                    if (
                        domain_key
                        and resolved_legacy_domain_allowance
                        and resolved_legacy_domain_allowance.get(domain_key, 0) > 0
                    ):
                        resolved_legacy_domain_allowance[domain_key] -= 1
                    else:
                        return f"Linha {index} do rateio: {domain_error}"

            percentage_value = item.get("percentage")
            allocated_amount_value = item.get("allocated_amount")
            try:
                percentage = Decimal(str(percentage_value or 0))
                allocated_amount = Decimal(str(allocated_amount_value or 0))
            except Exception:
                return f"Percentual ou valor inválido na linha {index} do rateio."

            current_mode = str(item.get("allocation_type") or "percentage").strip().lower()
            if allocation_mode is None:
                allocation_mode = current_mode
            elif allocation_mode != current_mode:
                return "Não é permitido misturar rateio por percentual e por valor no mesmo agendamento."

            if current_mode == "percentage" and percentage <= 0:
                return f"Informe um percentual maior que zero na linha {index} do rateio."
            if current_mode == "amount" and allocated_amount == 0:
                return f"Informe um valor diferente de zero na linha {index} do rateio."
            if current_mode == "amount" and allocated_amount < 0:
                return f"O valor da linha {index} do rateio não pode ser negativo."
            if current_mode not in {"percentage", "amount"}:
                return f"Tipo de rateio inválido na linha {index} do agendamento."

            percentage_total += percentage
            allocated_total += allocated_amount

        if allocation_mode == "percentage" and abs(percentage_total - Decimal("100")) > Decimal("0.01"):
            return "A soma dos percentuais do rateio deve ser exatamente 100%."

        if allocation_mode == "amount" and abs(allocated_total - amount_total) > Decimal("0.01"):
            return "A soma dos valores do rateio deve ser igual ao valor principal do agendamento."

        return None

    @staticmethod

    def _serialize_schedule(
        schedule: FinancialSchedule,
        *,
        include_related_entries: bool = False,
        include_summary: bool = False,
    ) -> Dict[str, Any]:
        from services.financial_bordero_service import FinancialBorderoService

        payload = schedule.to_dict()
        payload["signed_template_amount"] = FinancialService.get_signed_amount(
            payload.get("template_amount"),
            schedule.movement_nature,
        )
        payload["entity_label"] = FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]["singular"]
        payload["entity_legacy_label"] = FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]["legacy_singular"]
        payload["display_variant"] = "negative" if payload["signed_template_amount"] < 0 else "positive"
        metadata = dict(schedule.metadata_json or {})
        payload["metadata_json"] = metadata
        payload["attachments"] = list(metadata.get("attachments") or [])
        payload["allocations"] = FinancialScheduleService._normalize_schedule_allocations(
            company_id=schedule.company_id,
            template_amount=schedule.template_amount,
            due_date=schedule.next_due_date or schedule.first_due_date,
            metadata_json=metadata,
            fallback_chart_account_id=getattr(schedule, "chart_account_id", None),
            fallback_cost_center_id=getattr(schedule, "cost_center_id", None),
            fallback_domain_type=metadata.get("domain_type"),
            fallback_domain_source_kind=metadata.get("domain_source_kind"),
            fallback_domain_source_id=metadata.get("domain_source_id"),
            fallback_domain_label=metadata.get("domain_label"),
        )
        payload["document_number"] = metadata.get("document_number")
        payload["correction_index_id"] = metadata.get("correction_index_id")
        payload["discount_rule_id"] = metadata.get("discount_rule_id")
        payload["related_entries"] = []
        payload["has_entries"] = False
        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(
            company_id=schedule.company_id,
            schedule_id=schedule.id,
        )
        payload["bordero"] = (
            {
                "id": active_bordero.id,
                "code": active_bordero.bordero_code,
                "status": active_bordero.status,
                "type": active_bordero.bordero_type,
                "locked": True,
            }
            if active_bordero
            else None
        )
        payload["is_bordero_locked"] = bool(active_bordero)
        if include_related_entries:
            entries = FinancialEntry.query.filter(
                FinancialEntry.company_id == schedule.company_id,
                FinancialEntry.external_reference == f"financial_schedule:{schedule.id}",
                FinancialEntry.deleted_at.is_(None),
            ).order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).all()
            payload["related_entries"] = [FinancialService.serialize_entry(item) for item in entries]
            payload["has_entries"] = bool(entries)
        if include_summary:
            payload["summary"] = FinancialScheduleService._build_schedule_summary(schedule)
            if payload["summary"] is not None:
                payload["summary"]["bordero_code"] = active_bordero.bordero_code if active_bordero else None
                payload["summary"]["is_bordero_locked"] = bool(active_bordero)
        return build_financial_title_contract_payload(payload)

    @staticmethod
    def _derive_budget_links_from_allocations(
        *,
        metadata_json: Optional[Dict[str, Any]],
    ) -> Dict[str, Optional[int]]:
        allocations = list((metadata_json or {}).get("allocations") or [])
        if not allocations:
            return {}

        def _single_value(key: str) -> Optional[int]:
            values = {
                int(value)
                for value in (item.get(key) for item in allocations)
                if str(value or "").strip()
            }
            if len(values) == 1:
                return next(iter(values))
            return None

        return {
            "budget_line_id": _single_value("budget_line_id"),
            "budget_contract_id": _single_value("budget_contract_id"),
            "budget_document_id": _single_value("budget_document_id"),
        }

    @staticmethod
    def _expected_movement_nature(entry_type: str) -> str:
        return "credit" if entry_type == "receivable" else "debit"

    @staticmethod
    def _calculate_schedule_adjustments(
        *,
        company_id: int,
        template_amount: Any,
        metadata_json: Optional[Dict[str, Any]],
        due_date: Optional[date],
    ) -> Dict[str, float]:
        return FinancialTitleAmountService.calculate(
            company_id=company_id,
            template_amount=template_amount,
            metadata_json=metadata_json,
            due_date=due_date,
            correction_index_model=FinancialCorrectionIndex,
            discount_rule_model=FinancialDiscountRule,
        )

    @staticmethod
    def _build_schedule_summary(schedule: FinancialSchedule) -> Dict[str, Any]:
        metadata = dict(schedule.metadata_json or {})
        balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule)
        operational_state = build_title_operational_state_metadata(
            schedule_status=schedule.status,
            settlement_state=balance.get("settlement_state"),
            entry_type=schedule.entry_type,
            metadata_json=schedule.metadata_json,
        )
        original_total = Decimal(str(balance.get("principal_amount") or 0))
        settled_total = Decimal(str(balance.get("principal_settled") or 0))
        open_total = Decimal(str(balance.get("total_open") or balance.get("principal_open") or 0))
        suggested_financial_correction = Decimal("0.00")
        suggested_discount = Decimal("0.00")
        try:
            from services.financial_title_adjustment_service import FinancialTitleAdjustmentService

            adjustment_simulation = FinancialTitleAdjustmentService.simulate_for_schedule(
                schedule=schedule,
                reference_date=date.today(),
                base_amount=balance.get("principal_open"),
            )
            totals = adjustment_simulation.get("totals") or {}
            suggested_financial_correction = Decimal(str(totals.get("positive_adjustments") or 0))
            suggested_discount = Decimal(str(totals.get("discount") or 0))
        except Exception:
            logger.debug("Não foi possível calcular sugestão de correção do título %s", getattr(schedule, "id", None), exc_info=True)
        settlement_state = str(balance.get("settlement_state") or "open")
        operational_state_code = str(operational_state["code"] or "open")
        settled_entries = 1 if operational_state_code == "settled" and original_total > 0 else 0
        partial_entries = 1 if operational_state_code == "partial" else 0
        open_entries = 1 if operational_state_code == "open" and open_total > 0 else 0
        return {
            "entry_count": int(balance.get("entry_count") or 0),
            "settled_entries": settled_entries,
            "partial_entries": partial_entries,
            "open_entries": open_entries,
            "original_total": float(original_total),
            "settled_total": float(settled_total),
            "open_total": float(open_total),
            "signed_original_total": balance.get("signed_principal_amount"),
            "signed_settled_total": balance.get("signed_principal_settled"),
            "signed_open_total": balance.get("signed_total_open"),
            "settlement_state": settlement_state,
            "principal_amount": balance.get("principal_amount"),
            "principal_settled": balance.get("principal_settled"),
            "settlement_total_amount": balance.get("settlement_total_amount"),
            "principal_open": balance.get("principal_open"),
            "adjustments_generated": balance.get("adjustments_generated"),
            "adjustments_settled": balance.get("adjustments_settled"),
            "adjustments_open": balance.get("adjustments_open"),
            "discounts_open": balance.get("discounts_open"),
            "discounts_applied": balance.get("discounts_applied"),
            "suggested_financial_correction": float(suggested_financial_correction.quantize(Decimal("0.01"))),
            "suggested_discount": float(suggested_discount.quantize(Decimal("0.01"))),
            "suggested_updated_amount": float(
                max(
                    Decimal(str(balance.get("principal_open") or 0)) + suggested_financial_correction - suggested_discount,
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
            ),
            "principal_corrected_open": float(
                max(
                    Decimal(str(balance.get("principal_open") or 0)) + suggested_financial_correction - suggested_discount,
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
            ),
            "total_open": balance.get("total_open"),
            "signed_total_open": balance.get("signed_total_open"),
            "counterparty_name": metadata.get("counterparty_name"),
            "operational_state": operational_state["code"],
            "operational_state_label": operational_state["label"],
            "has_open_balance": bool(balance.get("has_open_balance")) or title_state_has_open_balance(operational_state_code),
            "enters_transactional_views": bool(balance.get("enters_transactional_views")),
            "include_in_accounting_reports": operational_state["include_in_accounting_reports"],
            "include_in_projected_reports": operational_state["include_in_projected_reports"],
        }

    @staticmethod
    def _find_schedule_by_code(*, company_id: int, schedule_code: str) -> Optional[FinancialSchedule]:
        return FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.schedule_code == schedule_code,
        ).first()

    @staticmethod
    def _is_schedule_code_unique_violation(exc: Exception) -> bool:
        constraint_name = getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None)
        if constraint_name == "uq_financial_schedules_company_code":
            return True
        return "uq_financial_schedules_company_code" in str(exc)

    @staticmethod
    def _generate_schedule_code(company_id: int) -> str:
        prefix = "AG"
        base_query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.schedule_code.like(f"{prefix}-%"),
        )
        last = base_query.order_by(FinancialSchedule.id.desc()).first()
        next_number = 1
        if last and last.schedule_code:
            try:
                next_number = int(str(last.schedule_code).split("-")[-1]) + 1
            except Exception:
                next_number = last.id + 1
        schedule_code = f"{prefix}-{next_number:06d}"
        while FinancialScheduleService._find_schedule_by_code(
            company_id=company_id,
            schedule_code=schedule_code,
        ):
            next_number += 1
            schedule_code = f"{prefix}-{next_number:06d}"
        return schedule_code

    @staticmethod
    def list_enabled_domains(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        result, error = FinancialDomainEnablementService.list_items(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        items_by_type = (result or {}).get("items_by_type") or {}
        enabled: List[Dict[str, Any]] = []
        for domain_type in ("project", "process"):
            for item in items_by_type.get(domain_type, []):
                if item.get("is_enabled"):
                    enabled.append(
                        {
                            **item,
                            "source_kind": "routine",
                            "domain_value": FinancialScheduleService._build_domain_value(
                                item.get("domain_type"),
                                item.get("source_id"),
                                "routine",
                            ),
                        }
                    )
        manual_items, manual_error = FinancialManualDomainService.list_enabled_items(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if manual_error:
            return None, manual_error
        for item in manual_items or []:
            enabled.append(
                {
                    **item,
                    "domain_value": FinancialScheduleService._build_domain_value(
                        item.get("domain_type"),
                        item.get("source_id"),
                        item.get("source_kind"),
                    ),
                }
            )
        return enabled, None

    @staticmethod
    def list_default_suggestions(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        result: Dict[str, Any] = {}

        default_cost_center = (
            FinancialCostCenter.query.filter(
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
                FinancialCostCenter.is_active.is_(True),
                FinancialCostCenter.is_default_suggestion.is_(True),
            )
            .order_by(FinancialCostCenter.updated_at.desc(), FinancialCostCenter.id.desc())
            .first()
        )
        if default_cost_center:
            result["cost_center_id"] = default_cost_center.id
            result["cost_center_label"] = (
                f"{default_cost_center.code} - {default_cost_center.name}"
                if default_cost_center.code
                else default_cost_center.name
            )

        default_domain = (
            FinancialDomainEnablement.query.filter(
                FinancialDomainEnablement.company_id == company_id,
                FinancialDomainEnablement.deleted_at.is_(None),
                FinancialDomainEnablement.is_enabled.is_(True),
                FinancialDomainEnablement.is_default_suggestion.is_(True),
            )
            .order_by(FinancialDomainEnablement.updated_at.desc(), FinancialDomainEnablement.id.desc())
            .first()
        )
        if default_domain:
            enabled_result, error = FinancialDomainEnablementService.list_items(
                company_id=company_id,
                domain_type=default_domain.domain_type,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                return None, error
            default_item = next(
                (
                    item for item in (enabled_result or {}).get("items", [])
                    if int(item.get("source_id") or 0) == int(default_domain.source_id)
                ),
                None,
            )
            if default_item:
                result["domain_type"] = default_item.get("domain_type")
                result["domain_source_kind"] = "routine"
                result["domain_source_id"] = default_item.get("source_id")
                result["domain_label"] = default_item.get("display_label")

        manual_default, manual_error = FinancialManualDomainService.get_default_suggestion(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if manual_error:
            return None, manual_error
        if manual_default:
            result["domain_type"] = manual_default.get("domain_type")
            result["domain_source_kind"] = manual_default.get("source_kind")
            result["domain_source_id"] = manual_default.get("source_id")
            result["domain_label"] = manual_default.get("display_label")

        default_document = (
            FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
                FinancialBudgetDocument.is_default_suggestion.is_(True),
            )
            .order_by(FinancialBudgetDocument.updated_at.desc(), FinancialBudgetDocument.id.desc())
            .first()
        )
        if default_document:
            contract = FinancialBudgetContract.query.filter(
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.id == default_document.budget_contract_id,
                FinancialBudgetContract.deleted_at.is_(None),
            ).first()
            line = (
                FinancialBudgetLine.query.filter(
                    FinancialBudgetLine.company_id == company_id,
                    FinancialBudgetLine.id == contract.budget_line_id,
                    FinancialBudgetLine.deleted_at.is_(None),
                ).first()
                if contract
                else None
            )
            version = (
                FinancialBudgetVersion.query.filter(
                    FinancialBudgetVersion.company_id == company_id,
                    FinancialBudgetVersion.id == line.budget_version_id,
                    FinancialBudgetVersion.deleted_at.is_(None),
                ).first()
                if line
                else None
            )
            result.update(
                {
                    "budget_version_id": version.id if version else None,
                    "budget_line_id": line.id if line else None,
                    "budget_contract_id": contract.id if contract else None,
                    "budget_document_id": default_document.id,
                    "budget_document_label": default_document.title,
                }
            )

        correction_indexes = (
            FinancialCorrectionIndex.query.filter(
                FinancialCorrectionIndex.company_id == company_id,
                FinancialCorrectionIndex.deleted_at.is_(None),
                FinancialCorrectionIndex.is_active.is_(True),
            )
            .order_by(FinancialCorrectionIndex.updated_at.desc(), FinancialCorrectionIndex.id.desc())
            .all()
        )
        default_receivable_correction = next(
            (
                item for item in correction_indexes
                if bool((item.metadata_json or {}).get("is_default_receivable"))
            ),
            None,
        )
        if default_receivable_correction:
            result["receivable_correction_index_id"] = default_receivable_correction.id
            result["receivable_correction_index_label"] = default_receivable_correction.name

        default_payable_correction = next(
            (
                item for item in correction_indexes
                if bool((item.metadata_json or {}).get("is_default_payable"))
            ),
            None,
        )
        if default_payable_correction:
            result["payable_correction_index_id"] = default_payable_correction.id
            result["payable_correction_index_label"] = default_payable_correction.name

        return result, None

    @staticmethod
    def _calculate_next_due_date(schedule: FinancialSchedule, current_due_date: date) -> Optional[date]:
        if schedule.frequency == "one_time":
            return None
        if schedule.frequency == "weekly":
            return current_due_date + timedelta(days=7 * int(schedule.interval_value or 1))
        if schedule.frequency == "monthly":
            return FinancialScheduleService._add_months(
                current_due_date,
                int(schedule.interval_value or 1),
                schedule.day_of_month,
            )
        if schedule.frequency == "yearly":
            return FinancialScheduleService._add_years(current_due_date, int(schedule.interval_value or 1))
        return None

    @staticmethod
    def _add_months(base_date: date, months: int, preferred_day: Optional[int]) -> date:
        month_index = (base_date.month - 1) + months
        year = base_date.year + (month_index // 12)
        month = (month_index % 12) + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(preferred_day or base_date.day, max_day)
        return date(year, month, day)

    @staticmethod
    def _add_years(base_date: date, years: int) -> date:
        year = base_date.year + years
        max_day = calendar.monthrange(year, base_date.month)[1]
        day = min(base_date.day, max_day)
        return date(year, base_date.month, day)
