"""Chaves de idempotência das mutações do mcp-versus (SPEC onda 2, seção 10)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db


class McpIdempotencyKey(db.Model):
    __tablename__ = "mcp_idempotency_keys"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id", "principal_id", "tool_name", "idempotency_key", name="uq_mcp_idempotency_scope"
        ),
        db.Index("ix_mcp_idempotency_keys_expires_at", "expires_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False)
    principal_id = db.Column(db.String(120), nullable=False)
    tool_name = db.Column(db.String(160), nullable=False)
    idempotency_key = db.Column(db.String(128), nullable=False)
    payload_digest = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="in_progress")
    result = db.Column(db.JSON().with_variant(JSONB, "postgresql"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
