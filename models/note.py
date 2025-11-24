from sqlalchemy import func
from sqlalchemy.orm import relationship
from . import db


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(256))
    status = db.Column(db.String(32), nullable=False, server_default="ativa")
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notes")
