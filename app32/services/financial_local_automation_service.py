from __future__ import annotations

from datetime import datetime
from typing import Optional

from models import db
from models.automation import AutomationRegistry, AutomationRule
from models.financial import FinancialSchedule


class FinancialLocalAutomationService:
    @staticmethod
    def get_schedule_automation_template_options() -> list[dict]:
        return [
            {
                "key": "settle_iss_withheld_on_settlement",
                "label": "ISS retido por baixa",
                "description": "Liquida o satélite de ISS retido conforme a baixa do título principal.",
            },
            {
                "key": "manual_retention_release",
                "label": "Retenção manual",
                "description": "Mantém a retenção em aberto até liberação manual.",
            },
            {
                "key": "settle_satellite_on_full_settlement",
                "label": "Satélite na quitação total",
                "description": "Liquida satélites apenas quando o título for totalmente quitado.",
            },
        ]

    @staticmethod
    def list_schedule_automations(schedule: FinancialSchedule):
        return (
            AutomationRegistry.query.filter(
                AutomationRegistry.company_id == schedule.company_id,
                AutomationRegistry.entity_type == "financial_schedule",
                AutomationRegistry.entity_id == schedule.id,
            )
            .order_by(AutomationRegistry.next_execution_at.asc().nullslast(), AutomationRegistry.name.asc())
            .all()
        )

    @staticmethod
    def create_schedule_automation(*, schedule: FinancialSchedule, template_key: str, user_id: Optional[int]):
        template_key = str(template_key or "").strip()
        template_map = {item["key"]: item for item in FinancialLocalAutomationService.get_schedule_automation_template_options()}
        if template_key not in template_map:
            raise ValueError("Modelo de automação inválido para o título financeiro.")

        existing = AutomationRegistry.query.filter(
            AutomationRegistry.company_id == schedule.company_id,
            AutomationRegistry.entity_type == "financial_schedule",
            AutomationRegistry.entity_id == schedule.id,
            AutomationRegistry.action_type == template_key,
            AutomationRegistry.is_active.is_(True),
        ).first()
        if existing:
            raise ValueError("Já existe uma automação ativa deste tipo para o título financeiro.")

        template = template_map[template_key]
        next_execution_at = datetime.combine(schedule.next_due_date, datetime.min.time()) if schedule.next_due_date else None
        trigger_type = "settlement"
        execution_mode = "automatic"
        requires_approval = False
        action_type = template_key

        if template_key == "manual_retention_release":
            trigger_type = "manual"
            execution_mode = "manual_release"
            next_execution_at = None
        elif template_key == "settle_satellite_on_full_settlement":
            trigger_type = "event"

        registry = AutomationRegistry(
            company_id=schedule.company_id,
            name=template["label"],
            module_key="financial",
            origin_type="financial",
            entity_type="financial_schedule",
            entity_id=schedule.id,
            trigger_type=trigger_type,
            action_type=action_type,
            execution_mode=execution_mode,
            status="active",
            requires_approval=requires_approval,
            is_active=True,
            next_execution_at=next_execution_at,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        db.session.add(registry)
        db.session.flush()

        if template_key == "settle_iss_withheld_on_settlement":
            trigger_config = {"event": "MAIN_TITLE_PARTIAL_SETTLEMENT", "mode": "proportional"}
            action_config = {
                "satellite_nature": "ISS_WITHHELD",
                "principal_effect": "PARTIAL_SETTLEMENT_BY_SETTLEMENT",
                "satellite_effect": "SETTLE_BY_SETTLEMENT",
            }
        elif template_key == "manual_retention_release":
            trigger_config = {"event": "MANUAL_RELEASE"}
            action_config = {"satellite_nature": "CONTRACTUAL_RETENTION", "satellite_effect": "OPEN_UNTIL_MANUAL"}
        else:
            trigger_config = {"event": "MAIN_TITLE_FULL_SETTLEMENT"}
            action_config = {"satellite_effect": "SETTLE_BY_SETTLEMENT", "mode": "full_only"}

        db.session.add(
            AutomationRule(
                company_id=schedule.company_id,
                automation_registry_id=registry.id,
                rule_code=template_key,
                trigger_config_json=trigger_config,
                action_config_json=action_config,
                policy_config_json={"entity_type": "financial_schedule", "entity_id": schedule.id},
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
        )
        db.session.commit()
        return registry

    @staticmethod
    def update_schedule_automation_status(*, schedule: FinancialSchedule, automation_id: int, activate: bool, user_id: Optional[int]):
        registry = AutomationRegistry.query.filter(
            AutomationRegistry.id == automation_id,
            AutomationRegistry.company_id == schedule.company_id,
            AutomationRegistry.entity_type == "financial_schedule",
            AutomationRegistry.entity_id == schedule.id,
        ).first()
        if not registry:
            raise ValueError("Automação do título financeiro não localizada.")
        registry.is_active = bool(activate)
        registry.status = "active" if activate else "paused"
        registry.updated_by_user_id = user_id
        db.session.commit()
        return registry
