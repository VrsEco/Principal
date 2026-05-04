from datetime import datetime, time

from . import db


class WorkJourneyBlock(db.Model):
    __tablename__ = 'work_journey_blocks'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.Time, nullable=False, default=time(8, 0))
    end_time = db.Column(db.Time, nullable=False, default=time(18, 0))
    block_mode = db.Column(db.String(30), nullable=False, default='operational')
    weekdays_json = db.Column(db.JSON, nullable=False, default=list)
    accepted_item_types = db.Column(db.JSON, nullable=False, default=list)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('work_journey_blocks', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'name': self.name,
            'description': self.description,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'block_mode': self.block_mode,
            'weekdays': list(self.weekdays_json or []),
            'accepted_item_types': list(self.accepted_item_types or []),
            'order_index': self.order_index,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyRule(db.Model):
    __tablename__ = 'work_journey_rules'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    preferred_block_id = db.Column(db.Integer, db.ForeignKey('work_journey_blocks.id', ondelete='SET NULL'), nullable=True, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    item_type = db.Column(db.String(40), nullable=False, default='manual')
    recurrence_type = db.Column(db.String(40), nullable=False, default='daily')
    recurrence_config = db.Column(db.JSON, nullable=False, default=dict)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=60)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('work_journey_rules', lazy='dynamic'))
    preferred_block = db.relationship('WorkJourneyBlock', foreign_keys=[preferred_block_id])

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'preferred_block_id': self.preferred_block_id,
            'title': self.title,
            'description': self.description,
            'item_type': self.item_type,
            'recurrence_type': self.recurrence_type,
            'recurrence_config': dict(self.recurrence_config or {}),
            'estimated_minutes': int(self.estimated_minutes or 0),
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyItem(db.Model):
    __tablename__ = 'work_journey_items'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'item_type', 'source_id', name='uq_work_journey_items_source'),
        db.UniqueConstraint('company_id', 'rule_id', 'occurrence_date', name='uq_work_journey_items_rule_occurrence'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    block_id = db.Column(db.Integer, db.ForeignKey('work_journey_blocks.id', ondelete='SET NULL'), nullable=True, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('work_journey_rules.id', ondelete='SET NULL'), nullable=True, index=True)
    item_type = db.Column(db.String(40), nullable=False, default='manual', index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    recurrence_type = db.Column(db.String(40), nullable=True)
    occurrence_date = db.Column(db.Date, nullable=True, index=True)
    due_date = db.Column(db.Date, nullable=True, index=True)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=60)
    worked_minutes = db.Column(db.Integer, nullable=False, default=0)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('work_journey_items', lazy='dynamic'))
    block = db.relationship('WorkJourneyBlock', foreign_keys=[block_id])
    rule = db.relationship('WorkJourneyRule', foreign_keys=[rule_id])

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'block_id': self.block_id,
            'rule_id': self.rule_id,
            'item_type': self.item_type,
            'source_id': self.source_id,
            'title': self.title,
            'description': self.description,
            'recurrence_type': self.recurrence_type,
            'occurrence_date': self.occurrence_date.isoformat() if self.occurrence_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_minutes': int(self.estimated_minutes or 0),
            'worked_minutes': int(self.worked_minutes or 0),
            'priority': self.priority,
            'status': self.status,
            'metadata_json': dict(self.metadata_json or {}),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyAbsenceRequest(db.Model):
    __tablename__ = 'work_journey_absence_requests'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    absence_type = db.Column(db.String(40), nullable=False, default='vacation')
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    reason = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    cleanup_notes = db.Column(db.Text)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('work_journey_absence_requests', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'requested_by_user_id': self.requested_by_user_id,
            'approved_by_user_id': self.approved_by_user_id,
            'absence_type': self.absence_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'reason': self.reason,
            'status': self.status,
            'cleanup_notes': self.cleanup_notes,
            'metadata_json': dict(self.metadata_json or {}),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyTransferRequest(db.Model):
    __tablename__ = 'work_journey_transfer_requests'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_journey_items.id', ondelete='CASCADE'), nullable=False, index=True)
    from_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    to_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reason = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    resolution_notes = db.Column(db.Text)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    item = db.relationship('WorkJourneyItem', backref=db.backref('transfer_requests', lazy='dynamic'))
    from_employee = db.relationship('Employee', foreign_keys=[from_employee_id])
    to_employee = db.relationship('Employee', foreign_keys=[to_employee_id])

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'item_id': self.item_id,
            'from_employee_id': self.from_employee_id,
            'to_employee_id': self.to_employee_id,
            'requested_by_user_id': self.requested_by_user_id,
            'approved_by_user_id': self.approved_by_user_id,
            'reason': self.reason,
            'status': self.status,
            'resolution_notes': self.resolution_notes,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyAgenda(db.Model):
    __tablename__ = 'work_journey_agendas'
    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', 'anchor_date', 'scope', name='uq_work_journey_agendas_scope'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    anchor_date = db.Column(db.Date, nullable=False, index=True)
    scope = db.Column(db.String(20), nullable=False, default='day', index=True)
    status = db.Column(db.String(30), nullable=False, default='suggested', index=True)
    engine_version = db.Column(db.String(30), nullable=False, default='agendas-v1')
    summary_json = db.Column(db.JSON, nullable=False, default=dict)
    generated_at = db.Column(db.DateTime, nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('work_journey_agendas', lazy='dynamic'))
    locked_by_user = db.relationship('User', foreign_keys=[locked_by_user_id])
    items = db.relationship('WorkJourneyAgendaItem', backref='agenda', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'anchor_date': self.anchor_date.isoformat() if self.anchor_date else None,
            'scope': self.scope,
            'status': self.status,
            'engine_version': self.engine_version,
            'summary_json': dict(self.summary_json or {}),
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'locked_by_user_id': self.locked_by_user_id,
            'locked_by_name': (
                getattr(self.locked_by_user, 'name', None)
                or getattr(self.locked_by_user, 'full_name', None)
                or getattr(self.locked_by_user, 'username', None)
                or getattr(self.locked_by_user, 'email', None)
            ) if self.locked_by_user else None,
            'locked': self.status == 'locked',
            'is_locked': self.status == 'locked',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkJourneyAgendaItem(db.Model):
    __tablename__ = 'work_journey_agenda_items'
    __table_args__ = (
        db.Index('ix_work_journey_agenda_items_agenda_day_position', 'agenda_id', 'planned_date', 'position_index'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('work_journey_agendas.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    journey_item_id = db.Column(db.Integer, db.ForeignKey('work_journey_items.id', ondelete='SET NULL'), nullable=True, index=True)
    block_id = db.Column(db.Integer, db.ForeignKey('work_journey_blocks.id', ondelete='SET NULL'), nullable=True, index=True)
    planned_date = db.Column(db.Date, nullable=False, index=True)
    position_index = db.Column(db.Integer, nullable=False, default=0)
    allocated_minutes = db.Column(db.Integer, nullable=False, default=0)
    planned_start_minutes = db.Column(db.Integer, nullable=True)
    planned_end_minutes = db.Column(db.Integer, nullable=True)
    overflow_minutes = db.Column(db.Integer, nullable=False, default=0)
    is_fixed = db.Column(db.Boolean, nullable=False, default=False)
    is_over_capacity = db.Column(db.Boolean, nullable=False, default=False)
    manual_override = db.Column(db.Boolean, nullable=False, default=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    journey_item = db.relationship('WorkJourneyItem', foreign_keys=[journey_item_id])
    block = db.relationship('WorkJourneyBlock', foreign_keys=[block_id])
    employee = db.relationship('Employee', foreign_keys=[employee_id])

    def to_dict(self):
        return {
            'id': self.id,
            'agenda_id': self.agenda_id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'journey_item_id': self.journey_item_id,
            'block_id': self.block_id,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'position_index': int(self.position_index or 0),
            'allocated_minutes': int(self.allocated_minutes or 0),
            'planned_start_minutes': self.planned_start_minutes,
            'planned_end_minutes': self.planned_end_minutes,
            'overflow_minutes': int(self.overflow_minutes or 0),
            'is_fixed': bool(self.is_fixed),
            'is_over_capacity': bool(self.is_over_capacity),
            'manual_override': bool(self.manual_override),
            'metadata_json': dict(self.metadata_json or {}),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkCalendarEvent(db.Model):
    __tablename__ = 'work_calendar_events'
    __table_args__ = (
        db.Index('ix_work_calendar_events_company_employee_date', 'company_id', 'employee_id', 'event_date'),
        db.Index('ix_work_calendar_events_company_source', 'company_id', 'source_type', 'source_id'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    source_type = db.Column(db.String(40), nullable=False, default='manual', index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='planned', index=True)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    execution_notes = db.Column(db.Text)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', foreign_keys=[employee_id])
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])
    updated_by_user = db.relationship('User', foreign_keys=[updated_by_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'created_by_user_id': self.created_by_user_id,
            'updated_by_user_id': self.updated_by_user_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'title': self.title,
            'description': self.description,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'status': self.status,
            'priority': self.priority,
            'execution_notes': self.execution_notes,
            'metadata_json': dict(self.metadata_json or {}),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
