from . import db
from datetime import datetime

class Routine(db.Model):
    __tablename__ = 'routines'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=True)
    code = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    
    schedule_type = db.Column(db.String(50), default='weekly')  # daily, weekly, monthly, quarterly, yearly, specific
    schedule_value = db.Column(db.String(255))
    start_time = db.Column(db.String(10), default='00:01')
    
    deadline_days = db.Column(db.Integer, default=0)
    deadline_hours = db.Column(db.Integer, default=0)
    deadline_date = db.Column(db.Date)
    
    score_weight = db.Column(db.Numeric(10, 2), default=1.0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collaborators = db.relationship('RoutineCollaborator', backref='routine_rel', lazy='dynamic', cascade='all, delete-orphan')

class RoutineCollaborator(db.Model):
    __tablename__ = 'routine_collaborators'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    hours_used = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoutineJourneyBinding(db.Model):
    __tablename__ = 'routine_journey_bindings'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'routine_id', 'employee_id', name='uq_routine_journey_binding'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    block_id = db.Column(db.Integer, db.ForeignKey('work_journey_blocks.id', ondelete='SET NULL'), nullable=True, index=True)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    routine = db.relationship('Routine', backref=db.backref('journey_bindings', lazy='dynamic', cascade='all, delete-orphan'))
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    block = db.relationship('WorkJourneyBlock', foreign_keys=[block_id])

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'routine_id': self.routine_id,
            'employee_id': self.employee_id,
            'block_id': self.block_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
