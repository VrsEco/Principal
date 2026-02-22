from . import db
from datetime import datetime

class Meeting(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    scheduled_date = db.Column(db.Date)
    scheduled_time = db.Column(db.String(10))
    actual_date = db.Column(db.Date)
    actual_time = db.Column(db.String(10))
    status = db.Column(db.String(50), default='draft')
    invite_notes = db.Column(db.Text)
    meeting_notes = db.Column(db.Text)
    guests_json = db.Column(db.Text)      # Storing JSON as text for compatibility with existing data
    agenda_json = db.Column(db.Text)
    participants_json = db.Column(db.Text)
    discussions_json = db.Column(db.Text)
    activities_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('meetings', lazy=True))
    project = db.relationship('Project', backref=db.backref('linked_meetings', lazy=True))

    def to_dict(self):
        import json
        
        def safe_json_loads(val):
            if not val:
                return None
            try:
                return json.loads(val) if isinstance(val, str) else val
            except:
                return None

        return {
            'id': self.id,
            'company_id': self.company_id,
            'project_id': self.project_id,
            'title': self.title,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'scheduled_time': self.scheduled_time,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'actual_time': self.actual_time,
            'status': self.status,
            'invite_notes': self.invite_notes,
            'meeting_notes': self.meeting_notes,
            'guests': safe_json_loads(self.guests_json),
            'agenda': safe_json_loads(self.agenda_json),
            'participants': safe_json_loads(self.participants_json),
            'discussions': safe_json_loads(self.discussions_json),
            'activities': safe_json_loads(self.activities_json),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Extra fields often needed in UI
            'project_title': self.project.name if self.project else None
        }

class MeetingAgendaItem(db.Model):
    __tablename__ = 'meeting_agenda_items'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'title': self.title,
            'description': self.description,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
