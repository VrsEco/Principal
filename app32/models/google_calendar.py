from datetime import datetime

from . import db


class GoogleCalendarConnection(db.Model):
    """Conexão OAuth de um usuário com o Google Calendar (uma por usuário, vale em todas as empresas).

    Tokens sempre criptografados.
    """

    __tablename__ = 'google_calendar_connections'
    __table_args__ = (
        db.UniqueConstraint('user_id', name='uq_google_calendar_conn_user'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    google_email = db.Column(db.String(255))
    refresh_token_enc = db.Column(db.Text, nullable=False)
    access_token_enc = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    scope = db.Column(db.Text)
    calendar_id = db.Column(db.String(255), nullable=False, default='primary')
    status = db.Column(db.String(20), nullable=False, default='active')  # active | error | revoked
    last_error = db.Column(db.String(500))
    last_synced_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class GoogleCalendarEventLink(db.Model):
    """Vínculo entre um registro do app (reunião, atividade, instância) e o evento criado no Google."""

    __tablename__ = 'google_calendar_event_links'
    __table_args__ = (
        db.UniqueConstraint('connection_id', 'source_type', 'source_id', name='uq_google_calendar_link_source'),
        db.Index('ix_google_calendar_links_company_date', 'company_id', 'event_date'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    connection_id = db.Column(
        db.Integer, db.ForeignKey('google_calendar_connections.id', ondelete='CASCADE'), nullable=False
    )
    source_type = db.Column(db.String(30), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    google_event_id = db.Column(db.String(255), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    last_synced_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
