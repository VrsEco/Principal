"""
Company Model - Represents a company/client in the system.
Compatible with APP31 legacy schema (industry, legal_name, cnpj, etc).
"""

from datetime import datetime
from . import db


class Company(db.Model):
    """
    Company model for storing client/company information.
    """

    __tablename__ = "companies"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    name = db.Column(db.String(200), nullable=False, index=True)
    legal_name = db.Column(db.String(200))
    cnpj = db.Column(db.String(18), unique=True, index=True)
    client_code = db.Column(db.String(50), unique=True, index=True)
    description = db.Column(db.Text)

    # Industry/Segment (no APP31 a coluna era industry; manter o nome lógico segment)
    segment = db.Column("industry", db.String(100))
    size = db.Column(db.String(50))  # Pequeno, Médio, Grande
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    coverage_physical = db.Column(db.String(50))
    coverage_online = db.Column(db.String(50))
    experience_total = db.Column(db.String(50))
    experience_segment = db.Column(db.String(50))
    mission = db.Column("mvv_mission", db.Text)
    vision = db.Column("mvv_vision", db.Text)
    values = db.Column("mvv_values", db.Text)

    # Logos
    logo_primary = db.Column(db.String(500))
    logo_secondary = db.Column(db.String(500))
    logo_icon = db.Column(db.String(500))

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Relationships
    # plans will be added via backref in Plan model

    def __repr__(self):
        return f"<Company {self.id}: {self.name}>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "cnpj": self.cnpj,
            "client_code": self.client_code,
            "description": self.description,
            "segment": self.segment,
            "size": self.size,
            "city": self.city,
            "state": self.state,
            "coverage_physical": self.coverage_physical,
            "coverage_online": self.coverage_online,
            "experience_total": self.experience_total,
            "experience_segment": self.experience_segment,
            "mission": self.mission,
            "vision": self.vision,
            "values": self.values,
            "logo_primary": self.logo_primary,
            "logo_secondary": self.logo_secondary,
            "logo_icon": self.logo_icon,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
            "is_active": self.is_active,
            "logo_count": self.logo_count,
        }

    def __json__(self):
        """Allow Flask's tojson filter to serialize the model."""
        return self.to_dict()

    @property
    def logo_count(self):
        """Count how many logos are configured."""
        count = 0
        if self.logo_primary:
            count += 1
        if self.logo_secondary:
            count += 1
        if self.logo_icon:
            count += 1
        return count
