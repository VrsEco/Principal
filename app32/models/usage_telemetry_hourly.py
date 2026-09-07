from datetime import datetime

from . import db


class UsageTelemetryHourly(db.Model):
    """Bucket agregado: nunca contém payload, segredo ou conteúdo de IA."""
    __tablename__ = 'usage_telemetry_hourly'
    id = db.Column(db.BigInteger, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    bucket_started_at = db.Column(db.DateTime, nullable=False)
    channel = db.Column(db.String(24), nullable=False, default='web')
    usage_kind = db.Column(db.String(24), nullable=False, default='standard')
    sessions_started = db.Column(db.Integer, nullable=False, default=0)
    active_seconds = db.Column(db.Integer, nullable=False, default=0)
    request_count = db.Column(db.Integer, nullable=False, default=0)
    ai_request_count = db.Column(db.Integer, nullable=False, default=0)
    mcp_request_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    latency_ms_total = db.Column(db.BigInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('company_id', 'user_id', 'bucket_started_at', 'channel', 'usage_kind', name='uq_usage_telemetry_hourly_bucket'),
        db.CheckConstraint('sessions_started >= 0 AND active_seconds >= 0 AND request_count >= 0 AND ai_request_count >= 0 AND mcp_request_count >= 0 AND error_count >= 0 AND latency_ms_total >= 0', name='ck_usage_telemetry_nonnegative'),
        db.Index('ix_usage_telemetry_company_bucket', 'company_id', 'bucket_started_at'),
        db.Index('ix_usage_telemetry_user_bucket', 'user_id', 'bucket_started_at'),
    )
