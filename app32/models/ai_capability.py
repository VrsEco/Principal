from __future__ import annotations

from datetime import datetime

from . import db


class AICapability(db.Model):
    __tablename__ = "ai_capabilities"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(160), nullable=False, unique=True, index=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    domain = db.Column(db.String(80), nullable=False, index=True)
    capability_type = db.Column(db.String(40), nullable=False, index=True, default="feature")
    risk_level = db.Column(db.String(20), nullable=False, default="medium", index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    rollout_status = db.Column(db.String(30), nullable=False, default="draft", index=True)
    origin = db.Column(db.String(30), nullable=False, default="system", index=True)
    source_ref = db.Column(db.String(180), index=True)
    requires_human_gate = db.Column(db.Boolean, nullable=False, default=False)
    requires_active_company = db.Column(db.Boolean, nullable=False, default=True)
    requires_user_binding = db.Column(db.Boolean, nullable=False, default=True)
    technical_binding_json = db.Column(db.JSON, nullable=False, default=dict)
    supported_channels_json = db.Column(db.JSON, nullable=False, default=list)
    supported_surfaces_json = db.Column(db.JSON, nullable=False, default=list)
    default_settings_json = db.Column(db.JSON, nullable=False, default=dict)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    approved_by = db.relationship("User", foreign_keys=[approved_by_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "capability_type": self.capability_type,
            "risk_level": self.risk_level,
            "status": self.status,
            "rollout_status": self.rollout_status,
            "origin": self.origin,
            "source_ref": self.source_ref,
            "requires_human_gate": self.requires_human_gate,
            "requires_active_company": self.requires_active_company,
            "requires_user_binding": self.requires_user_binding,
            "technical_binding_json": self.technical_binding_json or {},
            "supported_channels_json": list(self.supported_channels_json or []),
            "supported_surfaces_json": list(self.supported_surfaces_json or []),
            "default_settings_json": dict(self.default_settings_json or {}),
            "metadata_json": dict(self.metadata_json or {}),
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AICapabilityGrant(db.Model):
    __tablename__ = "ai_capability_grants"
    __table_args__ = (
        db.UniqueConstraint(
            "capability_id",
            "scope_type",
            "company_id",
            "user_id",
            "role_id",
            name="uq_ai_capability_grants_scope",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    capability_id = db.Column(db.Integer, db.ForeignKey("ai_capabilities.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type = db.Column(db.String(20), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    channels_json = db.Column(db.JSON, nullable=False, default=list)
    notes = db.Column(db.Text)
    valid_from = db.Column(db.DateTime, nullable=True)
    valid_until = db.Column(db.DateTime, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    capability = db.relationship("AICapability", lazy="joined")
    company = db.relationship("Company", foreign_keys=[company_id], lazy="joined")
    user = db.relationship("User", foreign_keys=[user_id], lazy="joined")
    role = db.relationship("Role", foreign_keys=[role_id], lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id], lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capability_id": self.capability_id,
            "scope_type": self.scope_type,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "is_enabled": self.is_enabled,
            "channels_json": list(self.channels_json or []),
            "notes": self.notes,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AICapabilityCompanySetting(db.Model):
    __tablename__ = "ai_capability_company_settings"
    __table_args__ = (
        db.UniqueConstraint("capability_id", "company_id", name="uq_ai_capability_company_settings"),
    )

    id = db.Column(db.Integer, primary_key=True)
    capability_id = db.Column(db.Integer, db.ForeignKey("ai_capabilities.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    settings_json = db.Column(db.JSON, nullable=False, default=dict)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    capability = db.relationship("AICapability", lazy="joined")
    company = db.relationship("Company", lazy="joined")
    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id], lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capability_id": self.capability_id,
            "company_id": self.company_id,
            "settings_json": dict(self.settings_json or {}),
            "is_enabled": self.is_enabled,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AICapabilityAuditLog(db.Model):
    __tablename__ = "ai_capability_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    capability_id = db.Column(db.Integer, db.ForeignKey("ai_capabilities.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    result = db.Column(db.String(20), nullable=False, default="success", index=True)
    channel = db.Column(db.String(50), nullable=True, index=True)
    surface = db.Column(db.String(40), nullable=True, index=True)
    detail = db.Column(db.Text)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    capability = db.relationship("AICapability", lazy="joined")
    company = db.relationship("Company", lazy="joined")
    user = db.relationship("User", foreign_keys=[user_id], lazy="joined")
    actor_user = db.relationship("User", foreign_keys=[actor_user_id], lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capability_id": self.capability_id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "actor_user_id": self.actor_user_id,
            "event_type": self.event_type,
            "result": self.result,
            "channel": self.channel,
            "surface": self.surface,
            "detail": self.detail,
            "payload_json": dict(self.payload_json or {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
