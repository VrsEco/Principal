from datetime import datetime

from . import db


class UserPresenceSession(db.Model):
    """Sessão observável de presença, sempre vinculada a uma empresa."""

    __tablename__ = "user_presence_sessions"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "user_id",
            "session_hash",
            name="uq_user_presence_company_user_session",
        ),
        db.Index("ix_user_presence_company_last_seen", "company_id", "last_seen_at"),
        db.Index("ix_user_presence_user_company", "user_id", "company_id"),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_hash = db.Column(db.String(64), nullable=False)
    login_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    logout_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    device_type = db.Column(db.String(32))
    browser = db.Column(db.String(64))
    ip_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<UserPresenceSession company={self.company_id} "
            f"user={self.user_id} last_seen={self.last_seen_at}>"
        )
