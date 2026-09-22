"""Outbox transacional para sincronização de identidades no Keycloak.

O evento não armazena senha ou token. A credencial inicial é definida pelo
Keycloak via ação obrigatória de troca de senha, disparada após o provisionamento.
"""
from __future__ import annotations

from datetime import datetime

from . import db


class IdentityProvisioningOutbox(db.Model):
    __tablename__ = "identity_provisioning_outbox"
    __table_args__ = (
        db.CheckConstraint(
            "operation IN ('upsert_user', 'disable_user')",
            name="ck_identity_outbox_operation",
        ),
        db.CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="ck_identity_outbox_status",
        ),
        db.UniqueConstraint("user_id", "operation", "dedupe_key", name="uq_identity_outbox_dedupe"),
        db.Index("ix_identity_outbox_status_next_attempt", "status", "next_attempt_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = db.Column(db.String(32), nullable=False)
    dedupe_key = db.Column(db.String(128), nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=True, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    external_subject = db.Column(db.String(512), nullable=True)
    last_error_code = db.Column(db.String(80), nullable=True)
    last_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("identity_provisioning_events", lazy="dynamic"))
