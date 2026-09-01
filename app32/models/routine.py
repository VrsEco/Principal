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
    execution_mode = db.Column(db.String(20), nullable=False, default='scheduled')
    
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
    role_assignments = db.relationship(
        'RoutineRoleAssignment',
        backref='routine_rel',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    triggers = db.relationship(
        'RoutineTrigger',
        backref='routine_rel',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

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


class RoutineRoleAssignment(db.Model):
    """Vincula a rotina a funções organizacionais, sem congelar o ocupante atual."""

    __tablename__ = 'routine_role_assignments'
    __table_args__ = (
        db.UniqueConstraint(
            'company_id',
            'routine_id',
            'role_id',
            'assignment_type',
            name='uq_routine_role_assignment',
        ),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    assignment_type = db.Column(db.String(20), nullable=False)  # responsible, executor
    distribution_mode = db.Column(db.String(20), nullable=False, default='collective')  # collective, individual, pool
    hours_used = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    role = db.relationship('Role', foreign_keys=[role_id], lazy='joined')


class RoutineTrigger(db.Model):
    """Gatilho adicional que pode iniciar uma rotina contínua ou híbrida."""

    __tablename__ = 'routine_triggers'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'routine_id', 'trigger_code', name='uq_routine_trigger_code'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id', ondelete='CASCADE'), nullable=False, index=True)
    trigger_type = db.Column(db.String(20), nullable=False, default='event')  # event, manual
    trigger_code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    activation_policy = db.Column(db.String(20), nullable=False, default='automatic')  # automatic, confirmation
    config_json = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = db.relationship(
        'RoutineTriggerEvent',
        backref='trigger_rel',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class RoutineTriggerEvent(db.Model):
    """Envelope idempotente de um evento recebido pelo motor de rotinas."""

    __tablename__ = 'routine_trigger_events'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'trigger_id', 'event_key', name='uq_routine_trigger_event_key'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id', ondelete='CASCADE'), nullable=False, index=True)
    trigger_id = db.Column(db.Integer, db.ForeignKey('routine_triggers.id', ondelete='CASCADE'), nullable=False, index=True)
    event_key = db.Column(db.String(200), nullable=False)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(30), nullable=False, default='received')
    created_instances_json = db.Column(db.JSON, nullable=False, default=list)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime)


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
