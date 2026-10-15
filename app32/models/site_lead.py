import uuid
from datetime import datetime

from models import db


def _new_lead_id() -> str:
    return uuid.uuid4().hex


class SiteLead(db.Model):
    """Lead captado por formulário público de site, isolado por company_id."""

    __tablename__ = "site_leads"
    __table_args__ = (
        db.Index("ix_site_leads_company_created", "company_id", "created_at"),
        db.Index("ix_site_leads_company_channel", "company_id", "utm_source", "utm_medium", "utm_campaign"),
        db.Index("ix_site_leads_dedupe", "company_id", "dedupe_hash", "created_at"),
        {"extend_existing": True},
    )

    id = db.Column(db.String(32), primary_key=True, default=_new_lead_id)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    source = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="novo")

    nome = db.Column(db.String(80))
    assunto = db.Column(db.String(60), nullable=False)
    relato = db.Column(db.String(600))

    utm_source = db.Column(db.String(120))
    utm_medium = db.Column(db.String(120))
    utm_campaign = db.Column(db.String(120))
    utm_content = db.Column(db.String(120))
    utm_term = db.Column(db.String(120))
    referrer_host = db.Column(db.String(255))
    landing = db.Column(db.String(300))
    page = db.Column(db.String(300))
    client_ts = db.Column(db.DateTime)

    consent_at = db.Column(db.DateTime, nullable=False)
    privacy_policy_version = db.Column(db.String(40), nullable=False)
    ip_hash = db.Column(db.String(64))
    dedupe_hash = db.Column(db.String(64), nullable=False)
    project_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    erased_at = db.Column(db.DateTime)
