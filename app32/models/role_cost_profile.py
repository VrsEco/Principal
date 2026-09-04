from datetime import datetime
from decimal import Decimal
from . import db


COST_COMPONENTS = ("base_salary", "charges", "benefits", "other_costs")


class RoleCostProfile(db.Model):
    """Estimativa por FTE, não folha individual; leitura exige autorização econômica."""
    __tablename__ = "role_cost_profiles"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    role_id = db.Column(db.Integer, nullable=False)
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date)
    currency = db.Column(db.String(3), nullable=False)
    base_salary = db.Column(db.Numeric(14, 2))
    charges = db.Column(db.Numeric(14, 2))
    benefits = db.Column(db.Numeric(14, 2))
    other_costs = db.Column(db.Numeric(14, 2))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(["company_id", "role_id"], ["roles.company_id", "roles.id"], name="fk_role_cost_tenant_role"),
        db.CheckConstraint("ends_on IS NULL OR ends_on > starts_on", name="ck_role_cost_dates"),
        db.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_role_cost_currency"),
        *(db.CheckConstraint(f"{field} IS NULL OR ({field} >= 0 AND {field} <= 999999999999.99)", name=f"ck_role_cost_{field}") for field in COST_COMPONENTS),
        db.UniqueConstraint("company_id", "role_id", "starts_on", name="uq_role_cost_start"),
    )

    def amounts(self):
        values = [getattr(self, field) for field in COST_COMPONENTS]
        known = [Decimal(str(value)) for value in values if value is not None]
        subtotal = sum(known, Decimal("0.00"))
        return {"known_subtotal": subtotal, "known_components": len(known),
                "monthly_cost_per_fte": subtotal if len(known) == len(COST_COMPONENTS) else None}
