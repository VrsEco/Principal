from datetime import datetime
from . import db


class Portfolio(db.Model):
    """Portfolio model - strategic grouping of projects"""

    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    responsible_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    company = db.relationship("Company", backref="portfolios")
    responsible = db.relationship("Employee", backref="portfolios")

    def to_dict(self, include_project_count=False):
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "responsible_id": self.responsible_id,
            "responsible_name": self.responsible.name if self.responsible else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }

        if include_project_count:
            # Count projects associated with this portfolio
            from models.project import Project
            result["project_count"] = Project.query.filter_by(
                portfolio_id=self.id
            ).count()

        return result

    def __json__(self):
        """Allow Flask's tojson filter to serialize the model."""
        return self.to_dict()

    def __repr__(self):
        return f"<Portfolio {self.code} - {self.name}>"
