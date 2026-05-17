from __future__ import annotations

from datetime import datetime

from . import db


class InstructionRegistryEntry(db.Model):
    __tablename__ = "instruction_registry_entries"

    id = db.Column(db.Integer, primary_key=True)
    scope_type = db.Column(db.String(24), nullable=False, index=True, default="runtime")
    runtime_profile = db.Column(db.String(80), nullable=False, index=True)
    agent_key = db.Column(db.String(80), nullable=True, index=True)
    harness_key = db.Column(db.String(120), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    channel = db.Column(db.String(20), nullable=False, default="stable", index=True)
    environment = db.Column(db.String(20), nullable=False, default="production", index=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    rollout_status = db.Column(db.String(30), nullable=False, default="active", index=True)
    entry_version = db.Column(db.String(40), nullable=False, default="v1")
    checksum = db.Column(db.String(64), nullable=False, default="")
    invalidation_token = db.Column(db.String(64), nullable=False, default="seed")
    cache_ttl_seconds = db.Column(db.Integer, nullable=False, default=1800)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    notes = db.Column(db.Text, nullable=True)
    last_invalidated_at = db.Column(db.DateTime, nullable=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship("Company", foreign_keys=[company_id], lazy="joined")
    approved_by = db.relationship("User", foreign_keys=[approved_by_user_id], lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id], lazy="joined")
    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id], lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope_type": self.scope_type,
            "runtime_profile": self.runtime_profile,
            "agent_key": self.agent_key,
            "harness_key": self.harness_key,
            "company_id": self.company_id,
            "channel": self.channel,
            "environment": self.environment,
            "status": self.status,
            "rollout_status": self.rollout_status,
            "entry_version": self.entry_version,
            "checksum": self.checksum,
            "invalidation_token": self.invalidation_token,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "payload_json": dict(self.payload_json or {}),
            "notes": self.notes,
            "last_invalidated_at": self.last_invalidated_at.isoformat() if self.last_invalidated_at else None,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InstructionRegistryAuditLog(db.Model):
    __tablename__ = "instruction_registry_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("instruction_registry_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    result = db.Column(db.String(20), nullable=False, default="success", index=True)
    detail = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    entry = db.relationship("InstructionRegistryEntry", lazy="joined")
    company = db.relationship("Company", lazy="joined")
    actor_user = db.relationship("User", lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "company_id": self.company_id,
            "actor_user_id": self.actor_user_id,
            "event_type": self.event_type,
            "result": self.result,
            "detail": self.detail,
            "payload_json": dict(self.payload_json or {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
