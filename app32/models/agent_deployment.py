"""Ledger multi-tenant de deploys do Squad Engenharia (estado + eventos append-only)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import event

from models import db


class AgentDeployment(db.Model):
    __tablename__ = "agent_deployments"
    __table_args__ = (
        db.UniqueConstraint("correlation_id", name="uq_agent_deployment_correlation"),
        db.Index("ix_agent_deployment_company_status_created", "company_id", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_by_principal_id = db.Column(db.Integer, db.ForeignKey("identity_principals.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_subject = db.Column(db.String(255), nullable=False)
    actor_client_id = db.Column(db.String(255), nullable=False)
    # Derivado do client_id autenticado no servidor; nunca do payload.
    actor_kind = db.Column(db.String(16), nullable=False)
    mode = db.Column(db.String(16), nullable=False)
    restart_mcp = db.Column(db.Boolean, nullable=False, default=False)
    target_sha = db.Column(db.String(40), nullable=False)
    correlation_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="pending_approval")

    approved_by_principal_id = db.Column(db.Integer, db.ForeignKey("identity_principals.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_subject = db.Column(db.String(255), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Preenchidos exclusivamente a partir de claims OIDC verificados do GitHub.
    github_run_id = db.Column(db.BigInteger, nullable=True)
    github_run_attempt = db.Column(db.Integer, nullable=True)
    github_actor = db.Column(db.String(255), nullable=True)
    github_triggering_actor = db.Column(db.String(255), nullable=True)
    github_workflow_ref = db.Column(db.String(512), nullable=True)
    github_sha = db.Column(db.String(40), nullable=True)
    github_run_url = db.Column(db.String(512), nullable=True)

    failure_reason = db.Column(db.String(255), nullable=True)
    evidence_json = db.Column(db.JSON, nullable=False, default=dict)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship("Company", lazy="joined")

    def to_dict(self) -> dict:
        # correlation_id é o vínculo do workflow e não é exposto aos agentes.
        return {
            "deployment_id": self.id,
            "company_id": self.company_id,
            "actor_kind": self.actor_kind,
            "mode": self.mode,
            "restart_mcp": self.restart_mcp,
            "target_sha": self.target_sha,
            "status": self.status,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "github_run_id": self.github_run_id,
            "github_run_attempt": self.github_run_attempt,
            "github_actor": self.github_actor,
            "github_run_url": self.github_run_url,
            "failure_reason": self.failure_reason,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentDeploymentEvent(db.Model):
    """Evidência append-only: inserida pelo service, nunca alterada ou removida."""

    __tablename__ = "agent_deployment_events"
    __table_args__ = (
        db.Index("ix_agent_deployment_event_deployment", "deployment_id", "id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    deployment_id = db.Column(db.Integer, db.ForeignKey("agent_deployments.id", ondelete="RESTRICT"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type = db.Column(db.String(32), nullable=False)
    from_status = db.Column(db.String(24), nullable=True)
    to_status = db.Column(db.String(24), nullable=True)
    source = db.Column(db.String(16), nullable=False)  # mcp | github_oidc | system
    actor_ref = db.Column(db.String(255), nullable=True)
    evidence_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "source": self.source,
            "actor_ref": self.actor_ref,
            "evidence": self.evidence_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@event.listens_for(AgentDeploymentEvent, "before_update")
def _block_event_update(mapper, connection, target):
    raise ValueError("agent_deployment_events é append-only")


@event.listens_for(AgentDeploymentEvent, "before_delete")
def _block_event_delete(mapper, connection, target):
    raise ValueError("agent_deployment_events é append-only")
