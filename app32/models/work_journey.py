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
