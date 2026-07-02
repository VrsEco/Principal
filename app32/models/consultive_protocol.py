from __future__ import annotations

from datetime import date, datetime

from . import db


CONSULTIVE_PROTOCOL_STATUS_VALUES = ("draft", "active", "archived")
CONSULTIVE_PROTOCOL_AUDIENCE_VALUES = ("ai_cli", "client_squad", "versus_squad", "consultant")
CONSULTIVE_PROTOCOL_DEPTH_VALUES = ("basic", "internal_diagnosis", "deep_research", "simulation")


def _iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


class ConsultiveProtocol(db.Model):
    """Protocolo consultivo evolutivo, versionado e resolvido via APP32/MCP."""

    __tablename__ = "consultive_protocols"
    __table_args__ = (
        db.CheckConstraint(
            f"status IN {CONSULTIVE_PROTOCOL_STATUS_VALUES}",
            name="ck_consultive_protocols_status",
        ),
        db.CheckConstraint(
            f"audience IN {CONSULTIVE_PROTOCOL_AUDIENCE_VALUES}",
            name="ck_consultive_protocols_audience",
        ),
        db.CheckConstraint(
            f"depth_level IN {CONSULTIVE_PROTOCOL_DEPTH_VALUES}",
            name="ck_consultive_protocols_depth_level",
        ),
        db.Index("ix_consultive_protocols_resolution", "company_id", "front_key", "subphase_key", "audience", "status"),
        db.Index("ix_consultive_protocols_global_resolution", "front_key", "subphase_key", "audience", "status"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    front_key = db.Column(db.String(40), nullable=False, index=True)
    subphase_key = db.Column(db.String(80), nullable=True, index=True)
    audience = db.Column(db.String(40), nullable=False, default="ai_cli", index=True)
    depth_level = db.Column(db.String(40), nullable=False, default="basic")
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    protocol_version = db.Column(db.String(40), nullable=False, default="v1")
    title = db.Column(db.String(255), nullable=False)
    objective = db.Column(db.Text)
    prompt_markdown = db.Column(db.Text, nullable=False)
    protocol_json = db.Column(db.JSON, default=dict)
    notes = db.Column(db.Text)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "front_key": self.front_key,
            "subphase_key": self.subphase_key,
            "audience": self.audience,
            "depth_level": self.depth_level,
            "status": self.status,
            "protocol_version": self.protocol_version,
            "title": self.title,
            "objective": self.objective,
            "prompt_markdown": self.prompt_markdown,
            "protocol": self.protocol_json or {},
            "notes": self.notes,
            "approved_by_user_id": self.approved_by_user_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "approved_at": _iso(self.approved_at),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "source": "tenant" if self.company_id else "global",
        }


__all__ = [
    "CONSULTIVE_PROTOCOL_STATUS_VALUES",
    "CONSULTIVE_PROTOCOL_AUDIENCE_VALUES",
    "CONSULTIVE_PROTOCOL_DEPTH_VALUES",
    "ConsultiveProtocol",
]
