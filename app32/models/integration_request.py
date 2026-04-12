from datetime import datetime

from . import db


class IntegrationRequest(db.Model):
    """Solicitação estruturada para nova integração."""

    __tablename__ = "integration_requests"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(120), nullable=False, index=True)
    business_domain = db.Column(db.String(80), nullable=False)
    integration_mode = db.Column(db.String(32), nullable=False)
    technical_channel = db.Column(db.String(32), nullable=False)
    source_channel = db.Column(db.String(64), nullable=False, default="ui")
    status = db.Column(db.String(32), nullable=False, default="requested")
    external_system = db.Column(db.String(255), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    data_summary = db.Column(db.Text, nullable=False)
    frequency = db.Column(db.String(64))
    urgency = db.Column(db.String(32), nullable=False, default="medium")
    compliance_level = db.Column(db.String(32), nullable=False, default="internal")
    provider_contact = db.Column(db.String(255))
    provider_docs_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    backlog_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "requester_user_id": self.requester_user_id,
            "title": self.title,
            "slug": self.slug,
            "business_domain": self.business_domain,
            "integration_mode": self.integration_mode,
            "technical_channel": self.technical_channel,
            "source_channel": self.source_channel,
            "status": self.status,
            "external_system": self.external_system,
            "objective": self.objective,
            "data_summary": self.data_summary,
            "frequency": self.frequency,
            "urgency": self.urgency,
            "compliance_level": self.compliance_level,
            "provider_contact": self.provider_contact,
            "provider_docs_url": self.provider_docs_url,
            "notes": self.notes,
            "payload": self.payload or {},
            "backlog_task_id": self.backlog_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
