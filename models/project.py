from datetime import datetime
from . import db

class Project(db.Model):
    """Project model"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    okr_links = db.Column(db.JSON)  # List of OKR IDs
    kpis = db.Column(db.JSON)  # List of KPI names
    owner = db.Column(db.String(200))
    status = db.Column(db.String(50), default='planned')  # planned, in_progress, completed, cancelled
    deadline = db.Column(db.Date)
    budget = db.Column(db.String(100))  # e.g., "R$ 450k"
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tasks = db.relationship('ProjectTask', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'name': self.name,
            'okr_links': self.okr_links,
            'kpis': self.kpis,
            'owner': self.owner,
            'status': self.status,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'budget': self.budget,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectTask(db.Model):
    """Project task model"""
    __tablename__ = 'project_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    what = db.Column(db.Text, nullable=False)
    who = db.Column(db.String(200))
    due_date = db.Column(db.Date)
    how = db.Column(db.Text)
    amount = db.Column(db.String(100))  # e.g., "R$ 80k"
    status = db.Column(db.String(50), default='planned')  # planned, in_progress, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'what': self.what,
            'who': self.who,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'how': self.how,
            'amount': self.amount,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ProjectTask {self.what[:50]}...>'
