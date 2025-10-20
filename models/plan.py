from datetime import datetime
from . import db

class Plan(db.Model):
    """Strategic planning model"""
    __tablename__ = 'plans'
    
    id = db.Column(db.String(100), primary_key=True)  # e.g., "transformacao-digital-2025"
    name = db.Column(db.String(200), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    sponsor_name = db.Column(db.String(100))  # Fallback if no user
    owner_name = db.Column(db.String(100))   # Fallback if no user
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='draft')  # draft, active, completed, locked
    progress = db.Column(db.Integer, default=0)  # Overall progress percentage
    progress_overall = db.Column(db.Integer, default=0)  # Overall progress percentage
    participants_count = db.Column(db.Integer, default=0)
    directionals_count = db.Column(db.Integer, default=0)
    okr_global_count = db.Column(db.Integer, default=0)
    okr_area_count = db.Column(db.Integer, default=0)
    projects_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = db.relationship('Company', back_populates='plans')
    participants = db.relationship('Participant', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    company_data = db.relationship('CompanyData', backref='plan', uselist=False, cascade='all, delete-orphan')
    driver_topics = db.relationship('DriverTopic', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    okrs_global = db.relationship('OKRGlobal', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    okrs_area = db.relationship('OKRArea', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    projects = db.relationship('Project', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'company_id': self.company_id,
            'sponsor_id': self.sponsor_id,
            'owner_id': self.owner_id,
            'sponsor_name': self.sponsor_name,
            'owner_name': self.owner_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'progress': self.progress,
            'progress_overall': self.progress_overall,
            'participants_count': self.participants_count,
            'directionals_count': self.directionals_count,
            'okr_global_count': self.okr_global_count,
            'okr_area_count': self.okr_area_count,
            'projects_count': self.projects_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Plan {self.name}>'
