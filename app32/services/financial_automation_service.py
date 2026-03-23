from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialAutomationExecution, FinancialAutomationRule, FinancialSchedule
from models.process import Process, ProcessInstance, ProcessRoutine
from schemas.financial import FinancialAutomationRuleCreateInput, FinancialAutomationRuleUpdateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialAutomationService:
    MAX_ATTEMPTS = 3

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
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
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
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationExecution.query.filter(
            FinancialAutomationExecution.company_id == company_id,
        )
        if rule_id:
            query = query.filter(FinancialAutomationExecution.rule_id == rule_id)
        if process_instance_id:
            query = query.filter(FinancialAutomationExecution.process_instance_id == process_instance_id)

        rows = query.order_by(FinancialAutomationExecution.executed_at.desc(), FinancialAutomationExecution.id.desc()).limit(200).all()
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

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
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

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
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
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
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
            logger.exception("Erro ao aplicar regras financeiras à instância %s", process_instance_id)
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
