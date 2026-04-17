from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import (
    FinancialAutomationBatch,
    FinancialAutomationDocument,
    FinancialAutomationHistory,
    FinancialAutomationRecord,
    db,
)
from models.financial import (
    FinancialAutomationExecution,
    FinancialAutomationRule,
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialSchedule,
)
from models.process import Process, ProcessInstance, ProcessRoutine
from schemas.financial import FinancialAutomationRuleCreateInput, FinancialAutomationRuleUpdateInput
from schemas.financial_automation import (
    FinancialAutomationBatchCreateInput,
    FinancialAutomationBulkStatusInput,
    FinancialAutomationDocumentCreateInput,
    FinancialAutomationGenerateInput,
    FinancialAutomationHistoryCreateInput,
    FinancialAutomationRecordCreateInput,
    FinancialAutomationRecordUpdateInput,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialAutomationService:
    MAX_ATTEMPTS = 3

    @staticmethod
    def _refresh_batch_summary(batch: Optional[FinancialAutomationBatch]) -> None:
        if not batch:
            return
        records = batch.records.filter(FinancialAutomationRecord.deleted_at.is_(None)).all()
        batch.status_summary_json = {
            "records_total": len(records),
            "documents_total": batch.documents.filter(FinancialAutomationDocument.deleted_at.is_(None)).count(),
            "imported_count": sum(1 for item in records if item.status == "imported"),
            "validated_count": sum(1 for item in records if item.status == "validated"),
            "generated_count": sum(1 for item in records if item.status == "generated"),
            "excluded_count": sum(1 for item in records if item.status == "excluded"),
        }
        batch.updated_at = datetime.utcnow()

    @staticmethod
    def _ensure_company_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        return FinancialService._ensure_company_scope(company_id, allowed_company_ids)

    @staticmethod
    def _serialize_record(record: FinancialAutomationRecord) -> Dict[str, Any]:
        payload = record.to_dict()
        payload["document"] = record.source_document.to_dict() if record.source_document else None
        payload["batch"] = record.batch.to_dict() if getattr(record, "batch", None) else None
        return payload

    @staticmethod
    def _append_history(
        *,
        company_id: int,
        record_id: int,
        action_type: str,
        performed_by_user_id: Optional[int],
        payload_before_json: Optional[Dict[str, Any]] = None,
        payload_after_json: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        history_data = FinancialAutomationHistoryCreateInput(
            company_id=company_id,
            record_id=record_id,
            action_type=action_type,
            performed_by_user_id=performed_by_user_id,
            payload_before_json=payload_before_json or {},
            payload_after_json=payload_after_json or {},
            metadata_json=metadata_json or {},
        )
        db.session.add(FinancialAutomationHistory(**history_data.model_dump()))

    @staticmethod
    def _validate_catalog_links(
        *,
        company_id: int,
        bank_account_id: Optional[int],
        counterparty_id: Optional[int],
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
    ) -> Optional[str]:
        return FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=bank_account_id,
            counterparty_id=counterparty_id,
            chart_account_id=chart_account_id,
            cost_center_id=cost_center_id,
        )

    @staticmethod
    def _validate_domain_link(company_id: int, domain_type: Optional[str], domain_source_id: Optional[int]) -> Optional[str]:
        if not domain_type or not domain_source_id:
            return None
        _, error = FinancialDomainEnablementService._load_source(company_id, domain_type, domain_source_id)
        return error

    @staticmethod
    def _serialize_rule(rule: FinancialAutomationRule) -> Dict[str, Any]:
        payload = rule.to_dict()
        payload["signed_template_amount"] = FinancialService.get_signed_amount(
            payload.get("template_amount"),
            payload.get("movement_nature"),
        )
        payload["display_variant"] = "negative" if payload["signed_template_amount"] < 0 else "positive"
        return payload

    @staticmethod
    def list_rules(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rules = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.deleted_at.is_(None),
        ).order_by(FinancialAutomationRule.id.desc()).all()
        return [FinancialAutomationService._serialize_rule(rule) for rule in rules], None

    @staticmethod
    def list_executions(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        rule_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationExecution.query.filter(
            FinancialAutomationExecution.company_id == company_id,
        )
        if rule_id:
            query = query.filter(FinancialAutomationExecution.rule_id == rule_id)
        if process_instance_id:
            query = query.filter(FinancialAutomationExecution.process_instance_id == process_instance_id)

        rows = query.order_by(
            FinancialAutomationExecution.executed_at.desc(),
            FinancialAutomationExecution.id.desc(),
        ).limit(200).all()
        return [row.to_dict() for row in rows], None

    @staticmethod
    def create_rule(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationRuleCreateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para regra de automação financeira: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        validation_error = FinancialAutomationService._validate_rule_scope(
            company_id=data.company_id,
            process_id=data.process_id,
            activity_id=data.activity_id,
            bank_account_id=data.bank_account_id,
            counterparty_id=data.counterparty_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            routine_id=data.routine_id,
        )
        if validation_error:
            return None, validation_error

        existing = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == data.company_id,
            FinancialAutomationRule.rule_code == data.rule_code,
            FinancialAutomationRule.deleted_at.is_(None),
        ).first()
        if existing:
            return None, f"Já existe regra com código {data.rule_code} para esta empresa."

        try:
            rule = FinancialAutomationRule(**data.model_dump())
            db.session.add(rule)
            db.session.commit()
            return FinancialAutomationService._serialize_rule(rule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar regra de automação financeira")
            return None, f"Erro ao criar regra de automação financeira: {exc}"

    @staticmethod
    def update_rule(
        *,
        rule_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationRuleUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização da regra: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rule = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.id == rule_id,
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.deleted_at.is_(None),
        ).first()
        if not rule:
            return None, "Regra de automação financeira não encontrada no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        if "rule_code" in merged:
            if merged["rule_code"] != rule.rule_code:
                return None, "O código da regra de automação não pode ser alterado após a criação."
            merged.pop("rule_code", None)
        validation_error = FinancialAutomationService._validate_rule_scope(
            company_id=company_id,
            process_id=merged.get("process_id", rule.process_id),
            activity_id=merged.get("activity_id", rule.activity_id),
            bank_account_id=merged.get("bank_account_id", rule.bank_account_id),
            counterparty_id=merged.get("counterparty_id", rule.counterparty_id),
            chart_account_id=merged.get("chart_account_id", rule.chart_account_id),
            cost_center_id=merged.get("cost_center_id", rule.cost_center_id),
            routine_id=merged.get("routine_id", rule.routine_id),
        )
        if validation_error:
            return None, validation_error

        try:
            for key, value in merged.items():
                setattr(rule, key, value)
            db.session.commit()
            return FinancialAutomationService._serialize_rule(rule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar regra de automação financeira %s", rule_id)
            return None, f"Erro ao atualizar regra de automação financeira: {exc}"

    @staticmethod
    def apply_rules_to_instance(
        *,
        company_id: int,
        process_instance_id: int,
        rule_id: Optional[int] = None,
        trigger_status: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        instance = ProcessInstance.query.filter(
            ProcessInstance.id == process_instance_id,
            ProcessInstance.company_id == company_id,
        ).first()
        if not instance:
            return None, "Instância de processo não encontrada no escopo da empresa."

        current_status = trigger_status or instance.status or "pending"
        rules = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.is_active.is_(True),
            FinancialAutomationRule.deleted_at.is_(None),
        ).all()
        if rule_id:
            rules = [rule for rule in rules if rule.id == rule_id]

        matched_rules = [
            rule
            for rule in rules
            if FinancialAutomationService._matches_rule(rule=rule, instance=instance, trigger_status=current_status)
        ]

        created_schedules: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        executions: List[Dict[str, Any]] = []

        try:
            for rule in matched_rules:
                idempotency_key = FinancialAutomationService._build_idempotency_key(
                    rule_id=rule.id,
                    process_instance_id=process_instance_id,
                    trigger_status=current_status,
                )
                previous_success = FinancialAutomationExecution.query.filter(
                    FinancialAutomationExecution.company_id == company_id,
                    FinancialAutomationExecution.rule_id == rule.id,
                    FinancialAutomationExecution.process_instance_id == process_instance_id,
                    FinancialAutomationExecution.idempotency_key == idempotency_key,
                    FinancialAutomationExecution.execution_status == "success",
                ).first()
                if previous_success:
                    skipped_payload = {
                        "rule_id": rule.id,
                        "reason": "idempotent_already_applied",
                        "execution_id": previous_success.id,
                    }
                    skipped.append(skipped_payload)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=previous_success.schedule_id,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            payload_json=skipped_payload,
                        ).to_dict()
                    )
                    continue

                attempt_number = FinancialAutomationExecution.query.filter(
                    FinancialAutomationExecution.company_id == company_id,
                    FinancialAutomationExecution.rule_id == rule.id,
                    FinancialAutomationExecution.process_instance_id == process_instance_id,
                    FinancialAutomationExecution.idempotency_key == idempotency_key,
                ).count() + 1
                if attempt_number > FinancialAutomationService.MAX_ATTEMPTS:
                    skipped_payload = {
                        "rule_id": rule.id,
                        "reason": "max_attempts_reached",
                        "max_attempts": FinancialAutomationService.MAX_ATTEMPTS,
                    }
                    skipped.append(skipped_payload)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=None,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            attempt_number=attempt_number,
                            payload_json=skipped_payload,
                            error_message="Número máximo de tentativas atingido.",
                        ).to_dict()
                    )
                    continue

                schedule_code = f"{rule.rule_code}-{process_instance_id}"
                existing = FinancialSchedule.query.filter(
                    FinancialSchedule.company_id == company_id,
                    FinancialSchedule.schedule_code == schedule_code,
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                if existing:
                    payload_json = {"rule_id": rule.id, "reason": "schedule_already_exists", "schedule_id": existing.id}
                    skipped.append(payload_json)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=existing.id,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            attempt_number=attempt_number,
                            payload_json=payload_json,
                        ).to_dict()
                    )
                    continue

                payload = FinancialAutomationService._build_schedule_payload(rule=rule, instance=instance)
                schedule, error = FinancialScheduleService.create_schedule(
                    payload=payload,
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    payload_json = {"rule_id": rule.id, "reason": error, "schedule_code": payload["schedule_code"]}
                    skipped.append(payload_json)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=None,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="error",
                            attempt_number=attempt_number,
                            payload_json=payload_json,
                            error_message=error,
                        ).to_dict()
                    )
                    continue

                persisted = FinancialSchedule.query.filter(
                    FinancialSchedule.company_id == company_id,
                    FinancialSchedule.schedule_code == payload["schedule_code"],
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                rule.last_execution_at = datetime.utcnow()
                if persisted:
                    rule.last_generated_schedule_id = persisted.id
                executions.append(
                    FinancialAutomationService._register_execution(
                        company_id=company_id,
                        rule_id=rule.id,
                        process_instance_id=process_instance_id,
                        schedule_id=persisted.id if persisted else None,
                        trigger_status=current_status,
                        idempotency_key=idempotency_key,
                        execution_status="success",
                        attempt_number=attempt_number,
                        payload_json={
                            "rule_id": rule.id,
                            "schedule_code": payload["schedule_code"],
                            "created_schedule_id": persisted.id if persisted else None,
                        },
                    ).to_dict()
                )
                created_schedules.append(schedule)

            db.session.commit()
            return {
                "company_id": company_id,
                "process_instance_id": process_instance_id,
                "trigger_status": current_status,
                "matched_rules": len(matched_rules),
                "created_count": len(created_schedules),
                "created_schedules": created_schedules,
                "skipped": skipped,
                "executions": executions,
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao aplicar automação financeira à instância %s", process_instance_id)
            return None, f"Erro ao aplicar automação financeira à instância: {exc}"

    @staticmethod
    def _matches_rule(*, rule: FinancialAutomationRule, instance: ProcessInstance, trigger_status: str) -> bool:
        if rule.process_id and rule.process_id != instance.process_id:
            return False
        if rule.trigger_status not in {"any", trigger_status}:
            return False
        if rule.activity_id and rule.activity_id != instance.routine_id:
            return False
        return True

    @staticmethod
    def _build_schedule_payload(*, rule: FinancialAutomationRule, instance: ProcessInstance) -> Dict[str, Any]:
        base_date = instance.due_date or date.today()
        start_date = base_date + timedelta(days=int(rule.start_offset_days or 0))
        due_date = base_date + timedelta(days=int(rule.due_offset_days or 0))
        schedule_name = FinancialAutomationService._render_template(rule.schedule_name_template, instance)
        description = FinancialAutomationService._render_template(rule.description_template, instance)
        schedule_code = f"{rule.rule_code}-{instance.id}"

        return {
            "company_id": rule.company_id,
            "schedule_code": schedule_code,
            "name": schedule_name[:120],
            "entry_type": rule.entry_type,
            "movement_nature": rule.movement_nature,
            "origin_type": rule.origin_type,
            "status": "active" if rule.auto_activate_schedule else "draft",
            "frequency": rule.frequency,
            "interval_value": rule.interval_value,
            "start_date": start_date,
            "first_due_date": due_date,
            "next_due_date": due_date,
            "description": description[:255],
            "memo": instance.description,
            "document_number_prefix": instance.instance_code or rule.rule_code,
            "template_amount": rule.template_amount,
            "currency_code": rule.currency_code,
            "auto_post": rule.auto_post,
            "generate_advance_days": rule.generate_advance_days,
            "bank_account_id": rule.bank_account_id,
            "counterparty_id": rule.counterparty_id,
            "chart_account_id": rule.chart_account_id,
            "cost_center_id": rule.cost_center_id,
            "activity_id": rule.activity_id or instance.routine_id,
            "process_instance_id": instance.id,
            "routine_id": rule.routine_id or instance.routine_id,
            "notes": rule.notes,
            "metadata_json": {
                **(rule.metadata_json or {}),
                "financial_automation_rule_id": rule.id,
                "generated_from_process_instance": instance.id,
                "process_id": instance.process_id,
                "instance_status": instance.status,
            },
        }

    @staticmethod
    def _render_template(template: str, instance: ProcessInstance) -> str:
        values = {
            "instance_id": str(instance.id),
            "instance_code": instance.instance_code or f"PI-{instance.id}",
            "instance_title": instance.title or "",
            "process_id": str(instance.process_id),
            "status": instance.status or "",
            "due_date": instance.due_date.isoformat() if instance.due_date else "",
        }

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return values.get(key, "")

        return re.sub(r"\{([a-z_]+)\}", replace, template or "")

    @staticmethod
    def _build_idempotency_key(*, rule_id: int, process_instance_id: int, trigger_status: str) -> str:
        return f"rule:{rule_id}|instance:{process_instance_id}|status:{trigger_status}"

    @staticmethod
    def _register_execution(
        *,
        company_id: int,
        rule_id: int,
        process_instance_id: int,
        schedule_id: Optional[int],
        trigger_status: str,
        idempotency_key: str,
        execution_status: str,
        payload_json: Dict[str, Any],
        attempt_number: int = 1,
        error_message: Optional[str] = None,
    ) -> FinancialAutomationExecution:
        execution = FinancialAutomationExecution(
            company_id=company_id,
            rule_id=rule_id,
            process_instance_id=process_instance_id,
            schedule_id=schedule_id,
            trigger_status=trigger_status,
            idempotency_key=idempotency_key,
            execution_status=execution_status,
            attempt_number=attempt_number,
            error_message=error_message,
            payload_json=payload_json,
        )
        db.session.add(execution)
        return execution

    @staticmethod
    def _validate_rule_scope(
        *,
        company_id: int,
        process_id: Optional[int],
        activity_id: Optional[int],
        bank_account_id: Optional[int],
        counterparty_id: Optional[int],
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
        routine_id: Optional[int],
    ) -> Optional[str]:
        if not process_id and not activity_id:
            return "A regra precisa de process_id ou activity_id."

        if process_id:
            process = Process.query.filter(Process.id == process_id, Process.company_id == company_id).first()
            if not process:
                return "Processo não encontrado no escopo da empresa."

        if activity_id:
            activity = ProcessRoutine.query.filter(
                ProcessRoutine.id == activity_id,
                ProcessRoutine.company_id == company_id,
            ).first()
            if not activity:
                return "Atividade de processo não encontrada no escopo da empresa."

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
            process_instance_id=None,
            routine_id=routine_id,
        )

    @staticmethod
    def list_options(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        def _ordered_items(model):
            return model.query.filter(
                model.company_id == company_id,
                model.deleted_at.is_(None),
            ).order_by(model.name.asc(), model.id.asc()).all()

        domains, domain_error = FinancialDomainEnablementService.list_items(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if domain_error:
            return None, domain_error

        items_by_type = (domains or {}).get("items_by_type") or {}
        domain_options: List[Dict[str, Any]] = []
        for domain_type, items in items_by_type.items():
            for item in items or []:
                domain_options.append(
                    {
                        "domain_type": domain_type,
                        "source_id": item.get("source_id"),
                        "label": item.get("display_label"),
                        "is_enabled": item.get("is_enabled"),
                    }
                )

        return {
            "bank_accounts": [item.to_dict() for item in _ordered_items(FinancialBankAccount)],
            "chart_accounts": [item.to_dict() for item in _ordered_items(FinancialChartAccount)],
            "cost_centers": [item.to_dict() for item in _ordered_items(FinancialCostCenter)],
            "counterparties": [item.to_dict() for item in _ordered_items(FinancialCounterparty)],
            "domain_options": domain_options,
            "status_options": ["imported", "validated", "generated", "excluded"],
            "entry_direction_options": ["payable", "receivable"],
            "settlement_state_options": ["settled", "open"],
            "generate_target_options": ["entry", "schedule"],
        }, None

    @staticmethod
    def create_batch(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        raw_payload = dict(payload or {})
        raw_documents = list(raw_payload.pop("documents", []) or [])
        raw_records = list(raw_payload.pop("records", []) or [])

        try:
            batch_data = FinancialAutomationBatchCreateInput.model_validate(raw_payload)
        except Exception as exc:
            return None, f"Payload inválido para lote da Central de Automação Financeira: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(batch_data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        try:
            batch = FinancialAutomationBatch(**batch_data.model_dump())
            db.session.add(batch)
            db.session.flush()

            created_documents: List[FinancialAutomationDocument] = []
            for raw_document in raw_documents:
                document_data = FinancialAutomationDocumentCreateInput.model_validate(
                    {
                        **dict(raw_document or {}),
                        "company_id": batch.company_id,
                        "batch_id": batch.id,
                    }
                )
                document = FinancialAutomationDocument(**document_data.model_dump())
                db.session.add(document)
                db.session.flush()
                created_documents.append(document)

            created_records: List[FinancialAutomationRecord] = []
            for raw_record in raw_records:
                record_data = FinancialAutomationRecordCreateInput.model_validate(
                    {
                        **dict(raw_record or {}),
                        "company_id": batch.company_id,
                        "batch_id": batch.id,
                    }
                )
                reference_error = FinancialAutomationService._validate_catalog_links(
                    company_id=batch.company_id,
                    bank_account_id=record_data.bank_account_id,
                    counterparty_id=record_data.counterparty_id,
                    chart_account_id=record_data.chart_account_id,
                    cost_center_id=record_data.cost_center_id,
                )
                if reference_error:
                    raise ValueError(reference_error)
                domain_error = FinancialAutomationService._validate_domain_link(
                    batch.company_id,
                    record_data.domain_type,
                    record_data.domain_source_id,
                )
                if domain_error:
                    raise ValueError(domain_error)
                record = FinancialAutomationRecord(**record_data.model_dump())
                db.session.add(record)
                db.session.flush()
                created_records.append(record)
                FinancialAutomationService._append_history(
                    company_id=batch.company_id,
                    record_id=record.id,
                    action_type="import",
                    performed_by_user_id=batch.created_by_user_id,
                    payload_after_json=record.to_dict(),
                    metadata_json={"batch_id": batch.id},
                )

            batch.status_summary_json = {
                "records_total": len(created_records),
                "documents_total": len(created_documents),
                "imported_count": len(created_records),
                "validated_count": 0,
                "generated_count": 0,
                "excluded_count": 0,
            }
            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "documents": [item.to_dict() for item in created_documents],
                "records": [FinancialAutomationService._serialize_record(item) for item in created_records],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao criar lote da Central de Automação Financeira: {exc}"

    @staticmethod
    def list_records(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        status: Optional[str] = None,
        origin_type: Optional[str] = None,
        batch_id: Optional[int] = None,
        competence_date_from: Optional[str] = None,
        competence_date_to: Optional[str] = None,
        due_date_from: Optional[str] = None,
        due_date_to: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationRecord.query.join(
            FinancialAutomationBatch,
            FinancialAutomationBatch.id == FinancialAutomationRecord.batch_id,
        ).filter(
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
            FinancialAutomationBatch.deleted_at.is_(None),
        )

        if status:
            query = query.filter(FinancialAutomationRecord.status == status)
        if origin_type:
            query = query.filter(FinancialAutomationBatch.origin_type == origin_type)
        if batch_id:
            query = query.filter(FinancialAutomationRecord.batch_id == batch_id)
        if competence_date_from:
            query = query.filter(FinancialAutomationRecord.competence_date >= competence_date_from)
        if competence_date_to:
            query = query.filter(FinancialAutomationRecord.competence_date <= competence_date_to)
        if due_date_from:
            query = query.filter(FinancialAutomationRecord.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialAutomationRecord.due_date <= due_date_to)

        items = query.order_by(FinancialAutomationRecord.created_at.desc(), FinancialAutomationRecord.id.desc()).all()
        return [FinancialAutomationService._serialize_record(item) for item in items], None

    @staticmethod
    def get_record(
        *,
        company_id: int,
        record_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.id == record_id,
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Registro da Central de Automação Financeira não encontrado no escopo da empresa."
        payload = FinancialAutomationService._serialize_record(item)
        payload["history"] = [
            history.to_dict()
            for history in item.history_items.order_by(FinancialAutomationHistory.created_at.desc()).all()
        ]
        return payload, None

    @staticmethod
    def update_record(
        *,
        company_id: int,
        record_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        performed_by_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.id == record_id,
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Registro da Central de Automação Financeira não encontrado no escopo da empresa."
        if item.status == "generated":
            return None, "Registro já gerado não pode ser editado por este fluxo."

        try:
            data = FinancialAutomationRecordUpdateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização do registro: {exc}"

        merged = data.model_dump(exclude_unset=True)
        if merged.get("status") == "generated":
            return None, "Status Gerada só pode ser definido pelo processamento oficial da Central."
        reference_error = FinancialAutomationService._validate_catalog_links(
            company_id=company_id,
            bank_account_id=merged.get("bank_account_id", item.bank_account_id),
            counterparty_id=merged.get("counterparty_id", item.counterparty_id),
            chart_account_id=merged.get("chart_account_id", item.chart_account_id),
            cost_center_id=merged.get("cost_center_id", item.cost_center_id),
        )
        if reference_error:
            return None, reference_error
        domain_error = FinancialAutomationService._validate_domain_link(
            company_id,
            merged.get("domain_type", item.domain_type),
            merged.get("domain_source_id", item.domain_source_id),
        )
        if domain_error:
            return None, domain_error

        before = item.to_dict()
        try:
            for key, value in merged.items():
                setattr(item, key, value)
            if item.status == "validated":
                item.validated_by_user_id = performed_by_user_id
                item.validated_at = datetime.utcnow()
            FinancialAutomationService._refresh_batch_summary(item.batch)
            item.updated_at = datetime.utcnow()
            FinancialAutomationService._append_history(
                company_id=company_id,
                record_id=item.id,
                action_type="update",
                performed_by_user_id=performed_by_user_id,
                payload_before_json=before,
                payload_after_json=item.to_dict(),
            )
            db.session.commit()
            return FinancialAutomationService._serialize_record(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar registro da Central: {exc}"

    @staticmethod
    def bulk_update_status(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        performed_by_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationBulkStatusInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização em lote: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.company_id == data.company_id,
            FinancialAutomationRecord.id.in_(data.record_ids),
            FinancialAutomationRecord.deleted_at.is_(None),
        ).all()
        if len(items) != len(set(data.record_ids)):
            return None, "Um ou mais registros não foram encontrados no escopo da empresa."
        if data.status == "generated":
            return None, "Use a ação de geração oficial para marcar registros como Gerada."

        updated_items: List[Dict[str, Any]] = []
        try:
            for item in items:
                if item.status == "generated" and data.status != "generated":
                    return None, "Registros já gerados não podem voltar de status por este fluxo."
                before = item.to_dict()
                item.status = data.status
                if data.validation_notes is not None:
                    item.validation_notes = data.validation_notes
                if data.status == "validated":
                    item.validated_by_user_id = performed_by_user_id
                    item.validated_at = datetime.utcnow()
                FinancialAutomationService._append_history(
                    company_id=data.company_id,
                    record_id=item.id,
                    action_type="bulk_status",
                    performed_by_user_id=performed_by_user_id,
                    payload_before_json=before,
                    payload_after_json=item.to_dict(),
                    metadata_json={"new_status": data.status},
                )
                updated_items.append(FinancialAutomationService._serialize_record(item))
            for batch in {item.batch for item in items if getattr(item, "batch", None)}:
                FinancialAutomationService._refresh_batch_summary(batch)
            db.session.commit()
            return {"items": updated_items, "count": len(updated_items)}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar registros em lote: {exc}"

    @staticmethod
    def get_document(
        *,
        company_id: int,
        document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationDocument.query.filter(
            FinancialAutomationDocument.id == document_id,
            FinancialAutomationDocument.company_id == company_id,
            FinancialAutomationDocument.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Documento de origem não encontrado no escopo da empresa."
        payload = item.to_dict()
        payload["public_url"] = f"/uploads/{item.stored_relative_path}" if item.stored_relative_path else None
        return payload, None

    @staticmethod
    def _generate_entry_code(company_id: int) -> str:
        return f"FAC-{company_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _build_generation_metadata(record: FinancialAutomationRecord) -> Dict[str, Any]:
        metadata = dict(record.metadata_json or {})
        metadata["financial_automation_record_id"] = record.id
        metadata["financial_automation_batch_id"] = record.batch_id
        return metadata

    @staticmethod
    def _generate_entry_from_record(
        record: FinancialAutomationRecord,
        generated_by_user_id: Optional[int],
        allowed_company_ids: Optional[Sequence[int]],
    ) -> Tuple[Optional[int], Optional[str]]:
        payload = {
            "company_id": record.company_id,
            "entry_code": FinancialAutomationService._generate_entry_code(record.company_id),
            "entry_type": record.entry_direction,
            "movement_nature": "credit" if record.entry_direction == "receivable" else "debit",
            "origin_type": "api",
            "status": "posted",
            "review_status": "approved",
            "description": record.description or "Registro gerado pela Central de Automação Financeira",
            "memo": record.validation_notes,
            "external_reference": f"financial_automation:{record.id}",
            "origin_reference": f"financial_automation_batch:{record.batch_id}",
            "competence_date": record.competence_date or datetime.utcnow().date(),
            "due_date": record.due_date,
            "occurred_on": record.competence_date or datetime.utcnow().date(),
            "original_amount": Decimal(str(record.amount or 0)),
            "bank_account_id": record.bank_account_id,
            "counterparty_id": record.counterparty_id,
            "chart_account_id": record.chart_account_id,
            "cost_center_id": record.cost_center_id,
            "created_by_user_id": generated_by_user_id,
            "approved_by_user_id": generated_by_user_id,
            "metadata_json": FinancialAutomationService._build_generation_metadata(record),
        }
        entry, error = FinancialService.create_entry(payload=payload, allowed_company_ids=allowed_company_ids)
        if error:
            return None, error
        if record.settlement_state == "settled":
            settlement_payload = {
                "company_id": record.company_id,
                "financial_entry_id": entry.id,
                "settlement_type": "manual",
                "settlement_status": "posted",
                "settlement_date": record.due_date or record.competence_date or datetime.utcnow().date(),
                "bank_account_id": record.bank_account_id,
                "principal_amount": Decimal(str(record.amount or 0)),
                "interest_amount": Decimal("0"),
                "penalty_amount": Decimal("0"),
                "discount_amount": Decimal("0"),
                "fee_amount": Decimal("0"),
                "other_adjustments_amount": Decimal("0"),
                "net_amount": Decimal(str(record.amount or 0)),
                "reconciliation_status": "pending",
                "notes": f"Liquidação criada pela Central de Automação Financeira (record {record.id}).",
                "metadata_json": FinancialAutomationService._build_generation_metadata(record),
            }
            _, settlement_error = FinancialService.create_settlement(
                payload=settlement_payload,
                allowed_company_ids=allowed_company_ids,
            )
            if settlement_error:
                return None, settlement_error
        return entry.id, None

    @staticmethod
    def _generate_schedule_from_record(
        record: FinancialAutomationRecord,
        generated_by_user_id: Optional[int],
        allowed_company_ids: Optional[Sequence[int]],
    ) -> Tuple[Optional[int], Optional[str]]:
        base_date = record.competence_date or record.due_date or datetime.utcnow().date()
        payload = {
            "company_id": record.company_id,
            "name": (record.description or "Registro da Central")[:120],
            "entry_type": record.entry_direction,
            "movement_nature": "credit" if record.entry_direction == "receivable" else "debit",
            "origin_type": "api",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": base_date,
            "first_due_date": record.due_date or base_date,
            "next_due_date": record.due_date or base_date,
            "description": (record.description or "Agendamento gerado pela Central de Automação Financeira")[:255],
            "template_amount": Decimal(str(record.amount or 0)),
            "bank_account_id": record.bank_account_id,
            "counterparty_id": record.counterparty_id,
            "chart_account_id": record.chart_account_id,
            "cost_center_id": record.cost_center_id,
            "created_by_user_id": generated_by_user_id,
            "notes": record.validation_notes,
            "metadata_json": FinancialAutomationService._build_generation_metadata(record),
        }
        result, error = FinancialScheduleService.create_schedule(
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        return int(result["id"]), None

    @staticmethod
    def generate_records(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationGenerateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para geração: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.company_id == data.company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
            FinancialAutomationRecord.status == data.only_status,
        )
        if data.record_ids:
            query = query.filter(FinancialAutomationRecord.id.in_(data.record_ids))
        items = query.order_by(FinancialAutomationRecord.id.asc()).all()
        if not items:
            return {"items": [], "count": 0}, None

        generated_items: List[Dict[str, Any]] = []
        try:
            for item in items:
                before = item.to_dict()
                generate_target = (
                    (item.metadata_json or {}).get("generate_target")
                    or (item.normalized_payload_json or {}).get("generate_target")
                    or ("entry" if item.settlement_state == "settled" else "schedule")
                )
                if generate_target == "entry":
                    entry_id, error = FinancialAutomationService._generate_entry_from_record(
                        item,
                        data.generated_by_user_id,
                        allowed_company_ids,
                    )
                    if error:
                        return None, error
                    item.generated_financial_entry_id = entry_id
                else:
                    schedule_id, error = FinancialAutomationService._generate_schedule_from_record(
                        item,
                        data.generated_by_user_id,
                        allowed_company_ids,
                    )
                    if error:
                        return None, error
                    item.generated_financial_schedule_id = schedule_id
                item.status = "generated"
                item.generated_by_user_id = data.generated_by_user_id
                item.generated_at = datetime.utcnow()
                FinancialAutomationService._append_history(
                    company_id=data.company_id,
                    record_id=item.id,
                    action_type="generate",
                    performed_by_user_id=data.generated_by_user_id,
                    payload_before_json=before,
                    payload_after_json=item.to_dict(),
                    metadata_json={"generate_target": generate_target},
                )
                generated_items.append(FinancialAutomationService._serialize_record(item))
            for batch in {item.batch for item in items if getattr(item, "batch", None)}:
                FinancialAutomationService._refresh_batch_summary(batch)
            db.session.commit()
            return {"items": generated_items, "count": len(generated_items)}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao gerar registros da Central: {exc}"
