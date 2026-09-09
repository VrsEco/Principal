from datetime import datetime

from . import db


class UserCompanyMembership(db.Model):
    """Vínculo de uma conta global com uma empresa, independente de colaborador."""

    __tablename__ = "user_company_memberships"
    __table_args__ = (
        db.UniqueConstraint("user_id", "company_id", name="uq_user_company_memberships_user_company"),
        db.CheckConstraint(
            "access_profile IN ('administrator', 'client', 'collaborator')",
            name="ck_user_company_memberships_access_profile",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    access_profile = db.Column(db.String(20), nullable=False, default="collaborator")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("company_memberships", lazy="dynamic"))
    company = db.relationship("Company", backref=db.backref("user_memberships", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "access_profile": self.access_profile,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
