from datetime import datetime

from . import db


class PasswordResetToken(db.Model):
    """Token opaco, de uso único, para redefinição de senha local."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    requested_ip_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True, index=True)

    user = db.relationship("User", backref=db.backref("password_reset_tokens", lazy="dynamic"))

    def __repr__(self):
        return f"<PasswordResetToken user_id={self.user_id} used={self.used_at is not None}>"
