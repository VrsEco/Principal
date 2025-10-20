from datetime import datetime
from . import db

class OKRGlobal(db.Model):
    """Global OKR model"""
    __tablename__ = 'okrs_global'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.String(100), db.ForeignKey('plans.id'), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # estruturante, aceleracao
    owner = db.Column(db.String(200))
    deadline = db.Column(db.Date)
    observations = db.Column(db.Text)
    directionals = db.Column(db.JSON)  # List of directional IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    key_results = db.relationship('KeyResult', backref='okr_global', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'objective': self.objective,
            'type': self.type,
            'owner': self.owner,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'observations': self.observations,
            'directionals': self.directionals,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<OKRGlobal {self.objective[:50]}...>'

class KeyResult(db.Model):
    """Key Result model"""
    __tablename__ = 'key_results'
    
    id = db.Column(db.Integer, primary_key=True)
    okr_global_id = db.Column(db.Integer, db.ForeignKey('okrs_global.id'), nullable=False)
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
            'okr_global_id': self.okr_global_id,
            'label': self.label,
            'metric': self.metric,
            'target': self.target,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'owner': self.owner,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<KeyResult {self.label}>'
