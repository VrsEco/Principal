from __future__ import annotations

import calendar
import logging
import os
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import db
from models.financial import FinancialChartAccount, FinancialCostCenter, FinancialEntry, FinancialSchedule
from schemas.financial import FinancialScheduleCreateInput, FinancialScheduleUpdateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialScheduleService:
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
        return [FinancialScheduleService._serialize_schedule(schedule) for schedule in schedules], None

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
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

        return FinancialScheduleService._serialize_schedule(schedule, include_related_entries=True), None

    @staticmethod
    def create_schedule(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_payload = dict(payload or {})
        company_id = normalized_payload.get("company_id")
        if company_id and not normalized_payload.get("schedule_code"):
            normalized_payload["schedule_code"] = FinancialScheduleService._generate_schedule_code(int(company_id))

        try:
            data = FinancialScheduleCreateInput(**normalized_payload)
        except Exception as exc:
            return None, f"Payload inválido para agendamento financeiro: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

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

        allocation_error = FinancialScheduleService._validate_schedule_allocations(
            company_id=data.company_id,
            template_amount=data.template_amount,
            metadata_json=data.metadata_json,
        )
        if allocation_error:
            return None, allocation_error

        existing = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == data.company_id,
            FinancialSchedule.schedule_code == data.schedule_code,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if existing:
            return None, f"Já existe agendamento com código {data.schedule_code} para esta empresa."

        try:
            normalized = data.model_dump()
            normalized["next_due_date"] = normalized.get("next_due_date") or normalized["first_due_date"]
            schedule = FinancialSchedule(**normalized)
            db.session.add(schedule)
            db.session.commit()
            return FinancialScheduleService._serialize_schedule(schedule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar agendamento financeiro")
            return None, f"Erro ao criar agendamento financeiro: {exc}"

    @staticmethod
    def update_schedule(
        *,
        schedule_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialScheduleUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização do agendamento: {exc}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
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

        allocation_error = FinancialScheduleService._validate_schedule_allocations(
            company_id=company_id,
            template_amount=merged.get("template_amount", schedule.template_amount),
            metadata_json=merged.get("metadata_json", schedule.metadata_json),
        )
        if allocation_error:
            return None, allocation_error

        start_date = merged.get("start_date", schedule.start_date)
        end_date = merged.get("end_date", schedule.end_date)
        first_due_date = merged.get("first_due_date", schedule.first_due_date)
        next_due_date = merged.get("next_due_date", schedule.next_due_date)
        if end_date and start_date and end_date < start_date:
            return None, "end_date não pode ser menor que start_date."
        if first_due_date and start_date and first_due_date < start_date:
            return None, "first_due_date não pode ser menor que start_date."
        if next_due_date and first_due_date and next_due_date < first_due_date:
            return None, "next_due_date não pode ser menor que first_due_date."

        try:
            for key, value in merged.items():
                setattr(schedule, key, value)
            db.session.commit()
            return FinancialScheduleService._serialize_schedule(schedule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar agendamento financeiro %s", schedule_id)
            return None, f"Erro ao atualizar agendamento financeiro: {exc}"

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
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

        if status not in {"active", "paused", "cancelled", "completed", "draft"}:
            return None, "Status inválido para o agendamento."

        try:
            schedule.status = status
            db.session.commit()
            return FinancialScheduleService._serialize_schedule(schedule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao alterar status do agendamento financeiro %s", schedule_id)
            return None, f"Erro ao alterar status do agendamento: {exc}"

    @staticmethod
    def create_entry_from_schedule(
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
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

        due_date = schedule.next_due_date or schedule.first_due_date
        if not due_date:
            return None, "Agendamento sem vencimento disponível para gerar baixa."

        entry_code = f"{schedule.schedule_code}-{due_date.isoformat()}"
        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.entry_code == entry_code,
        ).first()
        if existing:
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
                        schedule.next_due_date = None
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
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

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
            return None, "Agendamento financeiro não encontrado no escopo da empresa."

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
        metadata = dict(schedule.metadata_json or {})
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
            "issue_date": due_date,
            "competence_date": FinancialScheduleService._resolve_competence_date(schedule, due_date),
            "due_date": due_date,
            "occurred_on": due_date if (schedule.auto_post or force_posted) else None,
            "original_amount": Decimal(schedule.template_amount or 0),
            "currency_code": schedule.currency_code,
            "bank_account_id": schedule.bank_account_id,
            "counterparty_id": schedule.counterparty_id,
            "chart_account_id": schedule.chart_account_id,
            "cost_center_id": schedule.cost_center_id,
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
                "schedule_due_date": due_date.isoformat() if due_date else None,
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
        raw_allocations = list(metadata.get("allocations") or [])
        if not raw_allocations:
            return None

        payload = {
            "company_id": schedule.company_id,
            "financial_entry_id": entry_id,
            "allocations": [],
        }
        for item in raw_allocations:
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
                        "domain_type": item.get("domain_type"),
                        "domain_source_id": item.get("domain_source_id"),
                        "domain_label": item.get("domain_label"),
                    },
                }
            )

        _, error = FinancialService.replace_allocations(
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )
        return error

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
        metadata_json: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        allocations = list((metadata_json or {}).get("allocations") or [])
        if not allocations:
            return "Informe ao menos uma linha de rateio para o agendamento."

        amount_total = Decimal(str(template_amount or 0))
        percentage_total = Decimal("0")
        allocated_total = Decimal("0")

        for index, item in enumerate(allocations, start=1):
            chart_account_id = item.get("chart_account_id")
            cost_center_id = item.get("cost_center_id")
            if not chart_account_id:
                return f"Selecione o plano de contas na linha {index} do rateio."
            if not cost_center_id:
                return f"Selecione o centro de resultado na linha {index} do rateio."

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

            percentage_value = item.get("percentage")
            allocated_amount_value = item.get("allocated_amount")
            try:
                percentage = Decimal(str(percentage_value or 0))
                allocated_amount = Decimal(str(allocated_amount_value or 0))
            except Exception:
                return f"Percentual ou valor inválido na linha {index} do rateio."

            if percentage <= 0:
                return f"Informe um percentual maior que zero na linha {index} do rateio."
            if allocated_amount < 0:
                return f"O valor da linha {index} do rateio não pode ser negativo."

            percentage_total += percentage
            allocated_total += allocated_amount

        if abs(percentage_total - Decimal("100")) > Decimal("0.01"):
            return "A soma dos percentuais do rateio deve ser exatamente 100%."

        if abs(allocated_total - amount_total) > Decimal("0.01"):
            return "A soma dos valores do rateio deve ser igual ao valor do agendamento."

        return None

    @staticmethod

    def _serialize_schedule(
        schedule: FinancialSchedule,
        *,
        include_related_entries: bool = False,
    ) -> Dict[str, Any]:
        payload = schedule.to_dict()
        metadata = dict(schedule.metadata_json or {})
        payload["metadata_json"] = metadata
        payload["attachments"] = list(metadata.get("attachments") or [])
        payload["allocations"] = list(metadata.get("allocations") or [])
        payload["document_number"] = metadata.get("document_number")
        payload["correction_index_id"] = metadata.get("correction_index_id")
        payload["discount_rule_id"] = metadata.get("discount_rule_id")
        payload["competence_mode"] = metadata.get("competence_mode") or "same_as_due"
        payload["related_entries"] = []
        payload["has_entries"] = False
        if include_related_entries:
            entries = FinancialEntry.query.filter(
                FinancialEntry.company_id == schedule.company_id,
                FinancialEntry.external_reference == f"financial_schedule:{schedule.id}",
                FinancialEntry.deleted_at.is_(None),
            ).order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).all()
            payload["related_entries"] = [FinancialService.serialize_entry(item) for item in entries]
            payload["has_entries"] = bool(entries)
        return payload

    @staticmethod
    def _resolve_competence_date(schedule: FinancialSchedule, due_date: Optional[date]) -> Optional[date]:
        metadata = dict(schedule.metadata_json or {})
        mode = metadata.get("competence_mode") or "same_as_due"
        if mode == "keep_first_competence" and schedule.start_date:
            return schedule.start_date
        return due_date

    @staticmethod
    def _generate_schedule_code(company_id: int) -> str:
        prefix = "AG"
        base_query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
            FinancialSchedule.schedule_code.like(f"{prefix}-%"),
        )
        last = base_query.order_by(FinancialSchedule.id.desc()).first()
        next_number = 1
        if last and last.schedule_code:
            try:
                next_number = int(str(last.schedule_code).split("-")[-1]) + 1
            except Exception:
                next_number = last.id + 1
        return f"{prefix}-{next_number:06d}"

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
                    enabled.append(item)
        return enabled, None

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
