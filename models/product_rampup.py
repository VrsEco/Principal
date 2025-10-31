"""
Ramp-up scheduling entries for plan products.
"""

from datetime import datetime
from typing import Dict, Any

from models import db


class ProductRampUpEntry(db.Model):
    """Stores month-by-month ramp-up percentages for products."""

    __tablename__ = "plan_product_rampup_entries"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("plan_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_month = db.Column(db.Date, nullable=False)
    percentage = db.Column(db.Numeric(6, 2), nullable=False, default=100.00)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "product_id", "reference_month", name="uq_product_rampup_month"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialized representation."""
        reference_key = (
            self.reference_month.strftime("%Y-%m")
            if self.reference_month is not None
            else None
        )
        percentage_value = float(self.percentage or 0)
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "product_id": self.product_id,
            "reference_month": reference_key,
            "percentage": percentage_value,
            "notes": self.notes or "",
        }

