from datetime import datetime
from . import db


class Company(db.Model):
    """Company model"""

    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    legal_name = db.Column(db.String(200))
    cnpj = db.Column(db.String(18), unique=True, index=True)
    client_code = db.Column(db.String(16), index=True)  # Código interno único (ex: ABC)
    segment = db.Column("industry", db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    coverage_physical = db.Column(db.String(50))  # micro, local, regional, etc.
    coverage_online = db.Column(db.String(50))
    experience_total = db.Column(db.String(50))  # e.g., "12 anos"
    experience_segment = db.Column(db.String(50))  # e.g., "8 anos"
    mission = db.Column("mvv_mission", db.Text)
    vision = db.Column("mvv_vision", db.Text)
    values = db.Column("mvv_values", db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    # Relationship with Plan (bidirectional)
    plans = db.relationship("Plan", back_populates="company", lazy="dynamic")

    def to_dict(self):
        """Convert to dictionary"""
        # Usar getattr para colunas que podem não existir no banco
        return {
            "id": self.id,
            "name": getattr(self, 'name', None),
            "legal_name": getattr(self, 'legal_name', None),
            "cnpj": getattr(self, 'cnpj', None),
            "segment": getattr(self, 'segment', None),
            "city": getattr(self, 'city', None),
            "state": getattr(self, 'state', None),
            "coverage_physical": getattr(self, 'coverage_physical', None),
            "coverage_online": getattr(self, 'coverage_online', None),
            "experience_total": getattr(self, 'experience_total', None),
            "experience_segment": getattr(self, 'experience_segment', None),
            "mission": getattr(self, 'mission', None),
            "vision": getattr(self, 'vision', None),
            "values": getattr(self, 'values', None),
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
        }

    def __repr__(self):
        return f"<Company {self.name}>"
