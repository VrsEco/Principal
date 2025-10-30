from datetime import datetime
from . import db

class OKRArea(db.Model):
    """Area OKR model"""
    __tablename__ = 'okrs_area'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    linked_okr_ids = db.Column(db.JSON)  # List of global OKR IDs
    type = db.Column(db.String(20), nullable=False)  # estruturante, aceleracao
    department = db.Column(db.String(200))
    owner = db.Column(db.String(200))
    deadline = db.Column(db.Date)
    observations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    key_results = db.relationship('KeyResultArea', backref='okr_area', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'objective': self.objective,
            'linked_okr_ids': self.linked_okr_ids,
            'type': self.type,
            'department': self.department,
            'owner': self.owner,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'observations': self.observations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<OKRArea {self.objective[:50]}...>'

class KeyResultArea(db.Model):
    """Area Key Result model"""
    __tablename__ = 'key_results_area'
    
    id = db.Column(db.Integer, primary_key=True)
    okr_area_id = db.Column(db.Integer, db.ForeignKey('okrs_area.id'), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    metric = db.Column(db.String(200))
    target = db.Column(db.String(200))
    deadline = db.Column(db.Date)
    owner = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'okr_area_id': self.okr_area_id,
            'label': self.label,
            'metric': self.metric,
            'target': self.target,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'owner': self.owner,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<KeyResultArea {self.label}>'
