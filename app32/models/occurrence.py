
from . import db
from datetime import datetime

class Occurrence(db.Model):
    __tablename__ = 'occurrences'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    # employee_id kept for compat/primary responsible, but nullable
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True) 
    
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=True)
    # Corrected FK to match Project model's table
    project_id = db.Column(db.Integer, db.ForeignKey('company_projects.id'), nullable=True)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)
    
    # New: JSON list of collaborator IDs involved
    collaborators_ids = db.Column(db.JSON) 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref='occurrences')
    employee = db.relationship('Employee', backref='occurrences')
    process = db.relationship('Process', backref='occurrences')
    project = db.relationship('Project', backref='occurrences')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'collaborators_ids': self.collaborators_ids,
            'process_id': self.process_id,
            'process_name': self.process.name if self.process else None,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None, # Project has .name property mapped to title
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'score': self.score,
            'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            'updated_at': self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at
        }
