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
