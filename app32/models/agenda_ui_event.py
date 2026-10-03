from datetime import datetime

from . import db


class AgendaUiEvent(db.Model):
    """Evento de uso da Agenda, sem conteúdo dos itens: serve para medir adoção (SPEC agenda_unificada_blocos_pessoa_v1)."""

    __tablename__ = 'agenda_ui_events'
    __table_args__ = (
        db.Index('ix_agenda_ui_events_company_created', 'company_id', 'created_at'),
        db.Index('ix_agenda_ui_events_event_created', 'event', 'created_at'),
        {'extend_existing': True},
    )

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    event = db.Column(db.String(40), nullable=False)
    detail = db.Column(db.String(40))
    device = db.Column(db.String(10))  # mobile | desktop
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
