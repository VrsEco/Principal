from datetime import datetime

from . import db


class CompanyRolePermissionPreset(db.Model):
    """Preset reutilizável de matriz RBAC por empresa."""

    __tablename__ = "company_role_permission_presets"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    preset_key = db.Column(db.String(140), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "preset_key",
            name="uq_company_role_permission_presets_company_key",
        ),
    )

    def to_dict(self):
        def format_dt(value):
            if value is None:
                return None
            try:
                return value.isoformat()
            except AttributeError:
                return str(value)

        return {
            "id": self.id,
            "company_id": self.company_id,
            "preset_key": self.preset_key,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions or {},
            "created_by_user_id": self.created_by_user_id,
            "created_at": format_dt(self.created_at),
            "updated_at": format_dt(self.updated_at),
        }
