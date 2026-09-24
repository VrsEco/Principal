"""Ledger multi-tenant de solicitações de deploy do Squad Engenharia."""
from __future__ import annotations

from datetime import datetime

from models import db


class AgentDeployment(db.Model):
    __tablename__ = "agent_deployments"
    __table_args__ = (
        db.UniqueConstraint("company_id", "correlation_id", name="uq_agent_deployment_company_correlation"),
        db.Index("ix_agent_deployment_company_status_created", "company_id", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_by_principal_id = db.Column(db.Integer, db.ForeignKey("identity_principals.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_subject = db.Column(db.String(255), nullable=False)
    actor_client_id = db.Column(db.String(255), nullable=False)
    actor_kind = db.Column(db.String(32), nullable=False)
    mode = db.Column(db.String(16), nullable=False)
    restart_mcp = db.Column(db.Boolean, nullable=False, default=False)
    target_sha = db.Column(db.String(64), nullable=False)
    correlation_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="requested")
    github_run_url = db.Column(db.String(512), nullable=True)
    evidence_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship("Company", lazy="joined")

    def to_dict(self) -> dict:
        return {
            "deployment_id": self.id,
            "company_id": self.company_id,
            "correlation_id": self.correlation_id,
            "actor_kind": self.actor_kind,
            "mode": self.mode,
            "restart_mcp": self.restart_mcp,
            "target_sha": self.target_sha,
            "status": self.status,
            "github_run_url": self.github_run_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
