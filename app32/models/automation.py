from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db


class AutomationRegistry(db.Model):
    __tablename__ = "automation_registry"
    __table_args__ = (
        db.Index("ix_automation_registry_company", "company_id"),
        db.Index("ix_automation_registry_module", "company_id", "module_key"),
        db.Index("ix_automation_registry_entity", "company_id", "entity_type", "entity_id"),
        db.Index("ix_automation_registry_status", "company_id", "status"),
        db.Index("ix_automation_registry_next_exec", "company_id", "next_execution_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    module_key = db.Column(db.String(50), nullable=False, index=True)
    origin_type = db.Column(db.String(30), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    trigger_type = db.Column(db.String(30), nullable=False, index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    execution_mode = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="active", index=True)
    requires_approval = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    next_execution_at = db.Column(db.DateTime, index=True)
    last_execution_at = db.Column(db.DateTime, index=True)
    last_result = db.Column(db.String(30))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rules = db.relationship("AutomationRule", backref="registry", lazy="dynamic", cascade="all, delete-orphan")
    executions = db.relationship("AutomationExecution", backref="registry", lazy="dynamic", cascade="all, delete-orphan")
    bpms_links = db.relationship("AutomationBpmsLink", backref="registry", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "module_key": self.module_key,
            "origin_type": self.origin_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "trigger_type": self.trigger_type,
            "action_type": self.action_type,
            "execution_mode": self.execution_mode,
            "status": self.status,
            "requires_approval": bool(self.requires_approval),
            "is_active": bool(self.is_active),
            "next_execution_at": self.next_execution_at.isoformat() if self.next_execution_at else None,
            "last_execution_at": self.last_execution_at.isoformat() if self.last_execution_at else None,
            "last_result": self.last_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AutomationRule(db.Model):
    __tablename__ = "automation_rule"
    __table_args__ = (
        db.UniqueConstraint("company_id", "automation_registry_id", name="uq_automation_rule_registry"),
        db.Index("ix_automation_rule_company", "company_id"),
        db.Index("ix_automation_rule_code", "company_id", "rule_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    automation_registry_id = db.Column(db.Integer, db.ForeignKey("automation_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code = db.Column(db.String(80), nullable=False, index=True)
    trigger_config_json = db.Column(JSONB, nullable=False, default=dict)
    action_config_json = db.Column(JSONB, nullable=False, default=dict)
    policy_config_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "automation_registry_id": self.automation_registry_id,
            "rule_code": self.rule_code,
            "trigger_config_json": self.trigger_config_json or {},
            "action_config_json": self.action_config_json or {},
            "policy_config_json": self.policy_config_json or {},
        }


class AutomationExecution(db.Model):
    __tablename__ = "automation_execution"
    __table_args__ = (
        db.UniqueConstraint("company_id", "execution_key", name="uq_automation_execution_key"),
        db.Index("ix_automation_execution_company", "company_id"),
        db.Index("ix_automation_execution_registry", "company_id", "automation_registry_id"),
        db.Index("ix_automation_execution_status", "company_id", "status"),
        db.Index("ix_automation_execution_triggered", "company_id", "triggered_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    automation_registry_id = db.Column(db.Integer, db.ForeignKey("automation_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_key = db.Column(db.String(160), nullable=False)
    trigger_event = db.Column(db.String(60), index=True)
    triggered_at = db.Column(db.DateTime, nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(30), nullable=False, index=True)
    result_message = db.Column(db.Text)
    entity_snapshot_json = db.Column(JSONB, nullable=False, default=dict)
    execution_payload_json = db.Column(JSONB, nullable=False, default=dict)
    error_payload_json = db.Column(JSONB, nullable=False, default=dict)
    reversed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "automation_registry_id": self.automation_registry_id,
            "execution_key": self.execution_key,
            "trigger_event": self.trigger_event,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "result_message": self.result_message,
            "entity_snapshot_json": self.entity_snapshot_json or {},
            "execution_payload_json": self.execution_payload_json or {},
            "error_payload_json": self.error_payload_json or {},
            "reversed_at": self.reversed_at.isoformat() if self.reversed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AutomationBpmsLink(db.Model):
    __tablename__ = "automation_bpms_link"
    __table_args__ = (
        db.Index("ix_automation_bpms_link_company", "company_id"),
        db.Index("ix_automation_bpms_link_registry", "company_id", "automation_registry_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    automation_registry_id = db.Column(db.Integer, db.ForeignKey("automation_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), index=True)
    process_step_id = db.Column(db.Integer, db.ForeignKey("process_steps.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    bpms_mode = db.Column(db.String(30), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "automation_registry_id": self.automation_registry_id,
            "process_id": self.process_id,
            "process_step_id": self.process_step_id,
            "process_instance_id": self.process_instance_id,
            "bpms_mode": self.bpms_mode,
        }
