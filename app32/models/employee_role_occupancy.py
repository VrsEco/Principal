from datetime import datetime
from . import db


class EmployeeRoleOccupancy(db.Model):
    """Ocupação estrutural; nunca fonte automática de permissões RBAC."""
    __tablename__ = "employee_role_occupancies"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    employee_id = db.Column(db.Integer, nullable=False)
    role_id = db.Column(db.Integer, nullable=False)
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date, nullable=True)
    weekly_hours = db.Column(db.Numeric(5, 2), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ended_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(["company_id", "employee_id"], ["employees.company_id", "employees.id"], name="fk_occupancy_tenant_employee"),
        db.ForeignKeyConstraint(["company_id", "role_id"], ["roles.company_id", "roles.id"], name="fk_occupancy_tenant_role"),
        db.CheckConstraint("ends_on IS NULL OR ends_on > starts_on", name="ck_occupancy_dates"),
        db.CheckConstraint("weekly_hours IS NULL OR (weekly_hours > 0 AND weekly_hours <= 168)", name="ck_occupancy_hours"),
        db.UniqueConstraint("company_id", "employee_id", "role_id", "starts_on", name="uq_occupancy_start"),
        db.Index("ix_occupancy_company_employee", "company_id", "employee_id"),
        db.Index("ix_occupancy_company_role", "company_id", "role_id"),
    )

    def to_dict(self):
        return {
            "id": self.id, "company_id": self.company_id,
            "employee_id": self.employee_id, "role_id": self.role_id,
            "starts_on": self.starts_on.isoformat(),
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
            "weekly_hours": str(self.weekly_hours) if self.weekly_hours is not None else None,
            "created_by_user_id": self.created_by_user_id,
            "ended_by_user_id": self.ended_by_user_id,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }
