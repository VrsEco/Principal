from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialCounterparty, FinancialDomainEnablement, FinancialEntry, FinancialSchedule
from models.financial_budget import (
    FinancialBudgetContract,
    FinancialBudgetDocument,
    FinancialBudgetLine,
    FinancialBudgetVersion,
)
from schemas.financial import FinancialDirectEntryCreateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_manual_domain_service import FinancialManualDomainService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


class FinancialDirectEntryService:
    @staticmethod
    def list_options(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        counterparties, error = FinancialCatalogService.list_items(
            catalog_type="counterparties",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        bank_accounts, error = FinancialCatalogService.list_items(
            catalog_type="bank_accounts",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        chart_accounts, error = FinancialCatalogService.list_items(
            catalog_type="chart_accounts",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        cost_centers, error = FinancialCatalogService.list_items(
            catalog_type="cost_centers",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        correction_indexes, error = FinancialCatalogService.list_items(
            catalog_type="correction_indexes",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        discount_rules, error = FinancialCatalogService.list_items(
            catalog_type="discount_rules",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        enabled_domains, error = FinancialScheduleService.list_enabled_domains(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        default_suggestions, error = FinancialScheduleService.list_default_suggestions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        budget_versions = (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetVersion.period_start.desc(), FinancialBudgetVersion.id.desc())
            .all()
        )
        budget_lines = (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.deleted_at.is_(None),
                FinancialBudgetLine.is_active.is_(True),
            )
            .order_by(FinancialBudgetLine.line_order.asc(), FinancialBudgetLine.id.asc())
            .all()
        )
        budget_contracts = (
            FinancialBudgetContract.query.filter(
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetContract.name.asc(), FinancialBudgetContract.id.asc())
            .all()
        )
        budget_documents = (
            FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetDocument.title.asc(), FinancialBudgetDocument.id.asc())
            .all()
        )

        return {
            "counterparties": counterparties,
            "bank_accounts": bank_accounts,
            "chart_accounts": chart_accounts,
            "cost_centers": cost_centers,
            "correction_indexes": correction_indexes,
            "discount_rules": discount_rules,
            "enabled_domains": enabled_domains,
            "default_suggestions": default_suggestions or {},
            "budget_versions": [
                {
                    "id": item.id,
                    "code": item.full_code or item.code,
                    "name": item.name,
                    "status": item.status,
                    "budget_category": getattr(item, "budget_category", None),
                }
                for item in budget_versions
            ],
            "budget_lines": [
                {
                    "id": item.id,
                    "budget_version_id": item.budget_version_id,
                    "code": getattr(item, "full_code", None) or item.line_code,
                    "name": item.line_name,
                }
                for item in budget_lines
            ],
            "budget_contracts": [
                {
                    "id": item.id,
                    "budget_line_id": item.budget_line_id,
                    "code": getattr(item, "full_code", None) or item.contract_code,
                    "name": item.name,
                }
                for item in budget_contracts
            ],
            "budget_documents": [
                {
                    "id": item.id,
                    "budget_contract_id": item.budget_contract_id,
                    "code": getattr(item, "full_code", None) or item.document_code,
                    "name": item.title,
                    "is_default_suggestion": bool(getattr(item, "is_default_suggestion", False)),
                }
                for item in budget_documents
            ],
        }, None

    @staticmethod
    def create_direct_entry(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialDirectEntryCreateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para lançamento direto: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if not data.bank_account_id:
            return None, "Selecione a conta bancária do lançamento rápido."

        FinancialDirectEntryService._apply_counterparty_defaults(
            company_id=data.company_id,
            counterparty_id=data.counterparty_id,
            allocations=data.allocations,
        )

        ref_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            counterparty_id=data.counterparty_id,
        )
        if ref_error:
            return None, ref_error

        allocation_error = FinancialScheduleService._validate_schedule_allocations(
            company_id=data.company_id,
            template_amount=data.original_amount,
            due_date=data.due_date or data.occurred_on,
            metadata_json={
                "allocations": [
                    {
                        "chart_account_id": item.chart_account_id,
                        "cost_center_id": item.cost_center_id,
                        "budget_line_id": item.budget_line_id,
                        "budget_contract_id": item.budget_contract_id,
                        "budget_document_id": item.budget_document_id,
                        "domain_source_kind": item.domain_source_kind or "routine",
                        "domain_type": item.domain_type,
                        "domain_source_id": item.domain_source_id,
                        "domain_label": item.domain_label,
                        "allocation_type": item.allocation_type,
                        "percentage": item.percentage,
                        "allocated_amount": item.allocated_amount,
                    }
                    for item in data.allocations
                ]
            },
        )
        if allocation_error:
            return None, allocation_error

        domain_error = FinancialDirectEntryService._validate_enabled_domains(
            company_id=data.company_id,
            allocations=data.allocations,
        )
        if domain_error:
            return None, domain_error

        schedule_payload = FinancialDirectEntryService._build_schedule_payload(data)
        schedule_result, error = FinancialScheduleService.create_schedule(
            payload=schedule_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == data.company_id,
            FinancialSchedule.id == schedule_result["id"],
        ).first()
        if not schedule:
            return None, "Falha ao localizar o agendamento criado para o lançamento direto."

        entry_payload = FinancialDirectEntryService._build_entry_payload(data, schedule)
        entry, error = FinancialService.create_entry(
            payload=entry_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            FinancialDirectEntryService._cleanup_partial_direct_entry(
                company_id=data.company_id,
                schedule_id=schedule.id,
            )
            return None, error

        allocations_payload = {
            "company_id": data.company_id,
            "financial_entry_id": entry.id,
            "allocations": [
                {
                    "company_id": data.company_id,
                    "financial_entry_id": entry.id,
                    "chart_account_id": item.chart_account_id,
                    "cost_center_id": item.cost_center_id,
                    "allocation_type": item.allocation_type,
                    "percentage": item.percentage,
                    "allocated_amount": item.allocated_amount,
                    "notes": item.notes,
                    "metadata_json": {
                        **(item.metadata_json or {}),
                        "domain_source_kind": item.domain_source_kind or "routine",
                        "domain_type": item.domain_type,
                        "domain_source_id": item.domain_source_id,
                        "domain_label": item.domain_label,
                        "budget_version_id": item.budget_version_id,
                        "budget_line_id": item.budget_line_id,
                        "budget_contract_id": item.budget_contract_id,
                        "budget_document_id": item.budget_document_id,
                    },
                }
                for item in data.allocations
            ],
        }
        if allocations_payload["allocations"]:
            _, error = FinancialService.replace_allocations(
                payload=allocations_payload,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                FinancialDirectEntryService._cleanup_partial_direct_entry(
                    company_id=data.company_id,
                    schedule_id=schedule.id,
                    entry_id=entry.id,
                )
                return None, error

        schedule.status = "completed"
        schedule.last_generated_entry_id = entry.id
        schedule.last_generated_at = datetime.utcnow()
        schedule.metadata_json = {
            **(schedule.metadata_json or {}),
            "direct_entry": True,
            "direct_entry_id": entry.id,
        }
        db.session.commit()

        return {
            "schedule": FinancialScheduleService._serialize_schedule(schedule, include_related_entries=True),
            "entry": FinancialService.serialize_entry(entry),
        }, None

    @staticmethod
    def _apply_counterparty_defaults(
        *,
        company_id: int,
        counterparty_id: int,
        allocations: Sequence[Any],
    ) -> None:
        if len(allocations or []) != 1:
            return

        counterparty = FinancialCounterparty.query.filter(
            FinancialCounterparty.company_id == company_id,
            FinancialCounterparty.id == counterparty_id,
            FinancialCounterparty.deleted_at.is_(None),
        ).first()
        if not counterparty:
            return

        allocation = allocations[0]
        if not allocation.chart_account_id and counterparty.default_chart_account_id:
            allocation.chart_account_id = counterparty.default_chart_account_id
        if not allocation.cost_center_id and counterparty.default_cost_center_id:
            allocation.cost_center_id = counterparty.default_cost_center_id

    @staticmethod
    def _validate_enabled_domains(
        *,
        company_id: int,
        allocations: Sequence[Any],
    ) -> Optional[str]:
        selected_pairs = {
            (
                str(item.domain_source_kind or "routine").strip().lower() or "routine",
                item.domain_type,
                int(item.domain_source_id),
            )
            for item in allocations
            if item.domain_type and item.domain_source_id
        }
        if not selected_pairs:
            return None

        enabled_pairs = {
            ("routine", record.domain_type, int(record.source_id))
            for record in FinancialDomainEnablement.query.filter(
                FinancialDomainEnablement.company_id == company_id,
                FinancialDomainEnablement.deleted_at.is_(None),
                FinancialDomainEnablement.is_enabled.is_(True),
            ).all()
        }
        manual_enabled, error = FinancialManualDomainService.list_enabled_items(company_id=company_id)
        if error:
            return error
        for record in manual_enabled or []:
            enabled_pairs.add(("manual", record["domain_type"], int(record["source_id"])))

        for source_kind, domain_type, source_id in selected_pairs:
            if (source_kind, domain_type, source_id) not in enabled_pairs:
                label = "projeto" if domain_type == "project" else "processo"
                return f"O {label} selecionado no rateio não está habilitado no Financeiro."
        return None

    @staticmethod
    def _cleanup_partial_direct_entry(
        *,
        company_id: int,
        schedule_id: Optional[int] = None,
        entry_id: Optional[int] = None,
    ) -> None:
        try:
            if entry_id:
                entry = FinancialEntry.query.filter(
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.id == entry_id,
                ).first()
                if entry:
                    db.session.delete(entry)

            if schedule_id:
                schedule = FinancialSchedule.query.filter(
                    FinancialSchedule.company_id == company_id,
                    FinancialSchedule.id == schedule_id,
                ).first()
                if schedule:
                    db.session.delete(schedule)

            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def _build_schedule_payload(data: FinancialDirectEntryCreateInput) -> Dict[str, Any]:
        budget_links = {
            "budget_line_id": data.budget_line_id,
            "budget_contract_id": data.budget_contract_id,
            "budget_document_id": data.budget_document_id,
        }
        metadata_json = FinancialService._merge_budget_metadata({
            **(data.metadata_json or {}),
            "direct_entry": True,
            "document_number": data.document_number,
            "correction_index_id": data.correction_index_id,
            "discount_rule_id": data.discount_rule_id,
            "allocations": [
                {
                    "chart_account_id": item.chart_account_id,
                    "cost_center_id": item.cost_center_id,
                    "allocation_type": item.allocation_type,
                    "percentage": item.percentage,
                    "allocated_amount": item.allocated_amount,
                    "domain_source_kind": item.domain_source_kind or "routine",
                    "domain_type": item.domain_type,
                    "domain_source_id": item.domain_source_id,
                    "domain_label": item.domain_label,
                    "notes": item.notes,
                    "budget_version_id": item.budget_version_id,
                    "budget_line_id": item.budget_line_id,
                    "budget_contract_id": item.budget_contract_id,
                    "budget_document_id": item.budget_document_id,
                    "metadata_json": item.metadata_json or {},
                }
                for item in data.allocations
            ],
        }, budget_links)
        return {
            "company_id": data.company_id,
            "name": data.description[:120],
            "description": data.description,
            "entry_type": data.entry_type,
            "movement_nature": "credit" if data.entry_type == "receivable" else "debit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": data.competence_date,
            "first_due_date": data.due_date or data.occurred_on,
            "next_due_date": data.due_date or data.occurred_on,
            "template_amount": data.original_amount,
            "bank_account_id": data.bank_account_id,
            "counterparty_id": data.counterparty_id,
            "chart_account_id": data.chart_account_id or (data.allocations[0].chart_account_id if data.allocations else None),
            "cost_center_id": data.cost_center_id or (data.allocations[0].cost_center_id if data.allocations else None),
            "budget_line_id": data.budget_line_id,
            "budget_contract_id": data.budget_contract_id,
            "budget_document_id": data.budget_document_id,
            "created_by_user_id": data.created_by_user_id,
            "created_by_employee_id": data.created_by_employee_id,
            "created_by_agent": data.created_by_agent,
            "notes": data.notes,
            "metadata_json": metadata_json,
        }

    @staticmethod
    def _build_entry_payload(data: FinancialDirectEntryCreateInput, schedule: FinancialSchedule) -> Dict[str, Any]:
        entry_code = f"DIR-{schedule.id:06d}"
        budget_links = {
            "budget_line_id": data.budget_line_id,
            "budget_contract_id": data.budget_contract_id,
            "budget_document_id": data.budget_document_id,
        }
        metadata_json = FinancialService._merge_budget_metadata({
            **(data.metadata_json or {}),
            "direct_entry": True,
            "schedule_id": schedule.id,
            "correction_index_id": data.correction_index_id,
            "discount_rule_id": data.discount_rule_id,
        }, budget_links)
        return {
            "company_id": data.company_id,
            "entry_code": entry_code,
            "entry_type": "bank_movement",
            "movement_nature": "credit" if data.entry_type == "receivable" else "debit",
            "origin_type": "manual",
            "status": "posted",
            "review_status": "approved",
            "description": data.description,
            "document_number": data.document_number,
            "external_reference": f"financial_schedule:{schedule.id}",
            "origin_reference": schedule.schedule_code,
            "competence_date": data.competence_date,
            "due_date": data.due_date or data.occurred_on,
            "occurred_on": data.occurred_on,
            "original_amount": data.original_amount,
            "bank_account_id": data.bank_account_id,
            "counterparty_id": data.counterparty_id,
            "chart_account_id": data.chart_account_id or (data.allocations[0].chart_account_id if data.allocations else None),
            "cost_center_id": data.cost_center_id or (data.allocations[0].cost_center_id if data.allocations else None),
            "budget_line_id": data.budget_line_id,
            "budget_contract_id": data.budget_contract_id,
            "budget_document_id": data.budget_document_id,
            "created_by_user_id": data.created_by_user_id,
            "created_by_employee_id": data.created_by_employee_id,
            "created_by_agent": data.created_by_agent,
            "notes": data.notes,
            "metadata_json": metadata_json,
        }
