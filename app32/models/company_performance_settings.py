from datetime import datetime
from . import db


class CompanyPerformanceSettings(db.Model):
    """Stores performance score weights per company."""

    __tablename__ = "company_performance_settings"

    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), primary_key=True, nullable=False
    )
    on_time_score = db.Column(db.Numeric(10, 2), nullable=False, default=5)
    late_score = db.Column(db.Numeric(10, 2), nullable=False, default=-5)
    daily_delay_penalty = db.Column(db.Numeric(10, 2), nullable=False, default=-1)
    late_registration_penalty = db.Column(db.Numeric(10, 2), nullable=False, default=-1)
    postpone_penalty_points = db.Column(db.Numeric(10, 2), nullable=False, default=-1)
    allow_postpone_after_due_date = db.Column(
        db.Boolean, nullable=False, default=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize numeric values to floats for easier JSON usage."""
        def format_dt(dt):
            if dt is None: return None
            try:
                return dt.isoformat()
            except AttributeError:
                return str(dt)

        return {
            "company_id": self.company_id,
            "on_time_score": float(self.on_time_score or 0),
            "late_score": float(self.late_score or 0),
            "daily_delay_penalty": float(self.daily_delay_penalty or 0),
            "late_registration_penalty": float(self.late_registration_penalty or 0),
            "postpone_penalty_points": float(self.postpone_penalty_points or 0),
            "allow_postpone_after_due_date": bool(
                self.allow_postpone_after_due_date
            ),
            "updated_at": format_dt(self.updated_at),
            "created_at": format_dt(self.created_at),
        }
