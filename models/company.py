from datetime import datetime
from . import db

class Company(db.Model):
    """Company model"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    legal_name = db.Column(db.String(200))
    cnpj = db.Column(db.String(18), unique=True, index=True)
    segment = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    coverage_physical = db.Column(db.String(50))  # micro, local, regional, etc.
    coverage_online = db.Column(db.String(50))
    experience_total = db.Column(db.String(50))  # e.g., "12 anos"
    experience_segment = db.Column(db.String(50))  # e.g., "8 anos"
    mission = db.Column(db.Text)
    vision = db.Column(db.Text)
    values = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # Relationship with Plan (bidirectional)
    plans = db.relationship('Plan', back_populates='company', lazy='dynamic')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'legal_name': self.legal_name,
            'cnpj': self.cnpj,
            'segment': self.segment,
            'city': self.city,
            'state': self.state,
            'coverage_physical': self.coverage_physical,
            'coverage_online': self.coverage_online,
            'experience_total': self.experience_total,
            'experience_segment': self.experience_segment,
            'mission': self.mission,
            'vision': self.vision,
            'values': self.values,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Company {self.name}>'
