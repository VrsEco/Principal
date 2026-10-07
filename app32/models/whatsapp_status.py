"""Private Status acervo, server schedules and durable publication ledger."""
from datetime import datetime, timezone
from . import db


def utcnow():
    return datetime.now(timezone.utc)


class WhatsAppStatusAccount(db.Model):
    __tablename__ = 'whatsapp_status_accounts'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), primary_key=True)
    integration_id = db.Column(db.String(120), nullable=False)
    # An explicitly authorized legacy global integration may be shared only via this binding.
    allow_global = db.Column(db.Boolean, nullable=False, default=False)
    expected_phone = db.Column(db.String(20), nullable=False)
    verified_at = db.Column(db.DateTime(timezone=True))
    status_tested_at = db.Column(db.DateTime(timezone=True))
    enabled = db.Column(db.Boolean, nullable=False, default=False)


class WhatsAppStatusArt(db.Model):
    __tablename__ = 'whatsapp_status_arts'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'id'),
        db.UniqueConstraint('company_id', 'kit_code', 'version', 'position'),
        db.UniqueConstraint('company_id', 'code', 'version'),
    )
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    kit_code = db.Column(db.String(40), nullable=False)
    kit_size = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(40), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    private_path = db.Column(db.String(255), nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    mime = db.Column(db.String(20), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at = db.Column(db.DateTime(timezone=True))


class WhatsAppStatusSchedule(db.Model):
    __tablename__ = 'whatsapp_status_schedules'
    __table_args__ = (db.UniqueConstraint('company_id', 'id'), db.UniqueConstraint('company_id', 'name'))
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    timezone = db.Column(db.String(40), nullable=False, default='America/Bahia')
    hour = db.Column(db.Integer, nullable=False, default=8)
    minute = db.Column(db.Integer, nullable=False, default=30)
    # weekday string -> ordered approved art IDs. No URLs or supplier configuration.
    weekly_arts = db.Column(db.JSON, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    principal_id = db.Column(db.Integer, db.ForeignKey('identity_principals.id'), nullable=False)
    review_due = db.Column(db.DateTime(timezone=True), nullable=False)
    last_run_date = db.Column(db.Date)
    last_result = db.Column(db.String(40))


class WhatsAppStatusBatch(db.Model):
    __tablename__ = 'whatsapp_status_batches'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'id'),
        db.UniqueConstraint('company_id', 'command_key'),
        db.ForeignKeyConstraint(['company_id', 'schedule_id'],
                                ['whatsapp_status_schedules.company_id', 'whatsapp_status_schedules.id']),
    )
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    command_key = db.Column(db.String(100), nullable=False)
    payload_digest = db.Column(db.String(64), nullable=False)
    art_ids = db.Column(db.JSON, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    principal_id = db.Column(db.Integer, db.ForeignKey('identity_principals.id'), nullable=False)
    schedule_id = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default='queued')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class WhatsAppStatusPublication(db.Model):
    __tablename__ = 'whatsapp_status_publications'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'sha256', 'local_date'),
        db.ForeignKeyConstraint(['company_id', 'art_id'],
                                ['whatsapp_status_arts.company_id', 'whatsapp_status_arts.id']),
        db.ForeignKeyConstraint(['company_id', 'batch_id'],
                                ['whatsapp_status_batches.company_id', 'whatsapp_status_batches.id']),
        db.CheckConstraint("status IN ('sending','accepted','failed','unknown')"),
    )
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    art_id = db.Column(db.Integer, nullable=False)
    batch_id = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    local_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    result_code = db.Column(db.String(40))
    provider_message_id = db.Column(db.String(120))
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True))
    mobile_confirmed_at = db.Column(db.DateTime(timezone=True))
    mobile_confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
