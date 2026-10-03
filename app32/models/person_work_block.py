"""Blocos de jornada da pessoa (SPEC agenda unificada, Fase 3).

Preferencia pessoal do USUARIO, sem `company_id` (decisao D3): vale para todas as
empresas em que a pessoa atua. So o proprio usuario le e grava; terceiros so enxergam
resultados agregados por servico (SPEC secoes 6.4 e 8.3).
"""

from __future__ import annotations

from datetime import datetime, time

from . import db


class PersonWorkBlock(db.Model):
    __tablename__ = 'person_work_blocks'
    __table_args__ = (
        db.Index('ix_person_work_blocks_user_active', 'user_id', 'is_active'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.Time, nullable=False, default=time(8, 0))
    end_time = db.Column(db.Time, nullable=False, default=time(18, 0))
    block_mode = db.Column(db.String(30), nullable=False, default='operational')
    weekdays_json = db.Column(db.JSON, nullable=False, default=list)
    preferred_item_types = db.Column(db.JSON, nullable=False, default=list)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end': self.end_time.strftime('%H:%M') if self.end_time else None,
            'mode': self.block_mode,
            'weekdays': list(self.weekdays_json or []),
            'preferred_item_types': list(self.preferred_item_types or []),
            'order_index': int(self.order_index or 0),
            'is_active': bool(self.is_active),
        }
