from __future__ import annotations

from datetime import datetime

from . import db


class UserMcpToken(db.Model):
    """Token pessoal para acesso remoto ao MCP."""

    __tablename__ = "user_mcp_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    token_prefix = db.Column(db.String(24), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    last_client_name = db.Column(db.String(120), nullable=True)
    last_surface = db.Column(db.String(32), nullable=True)
    last_company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    last_harness_key = db.Column(db.String(120), nullable=True)
    notice_d3_sent_at = db.Column(db.DateTime, nullable=True)
    notice_d0_sent_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = db.relationship("User", foreign_keys=[user_id], back_populates="mcp_tokens")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    last_company = db.relationship("Company", foreign_keys=[last_company_id])

    @property
    def is_active(self) -> bool:
        return str(self.status or "").strip().lower() == "active" and self.revoked_at is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_prefix": self.token_prefix,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "last_client_name": self.last_client_name,
            "last_surface": self.last_surface,
            "last_company_id": self.last_company_id,
            "last_harness_key": self.last_harness_key,
            "notice_d3_sent_at": self.notice_d3_sent_at.isoformat() if self.notice_d3_sent_at else None,
            "notice_d0_sent_at": self.notice_d0_sent_at.isoformat() if self.notice_d0_sent_at else None,
        }
