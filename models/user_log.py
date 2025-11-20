from datetime import datetime
from . import db


class UserLog(db.Model):
    """User activity log model for auditing all system operations"""

    __tablename__ = "user_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user_email = db.Column(
        db.String(120), nullable=False
    )  # Store email for historical reference
    user_name = db.Column(
        db.String(100), nullable=False
    )  # Store name for historical reference

    # Operation details
    action = db.Column(
        db.String(50), nullable=False
    )  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, VIEW
    entity_type = db.Column(
        db.String(50), nullable=False
    )  # company, plan, participant, etc.
    entity_id = db.Column(db.String(100))  # ID of the affected entity
    entity_name = db.Column(db.String(200))  # Name/title of the affected entity

    # Changes tracking
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values

    # Context
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.Text)  # Browser/client info
    endpoint = db.Column(db.String(200))  # API endpoint or page accessed
    method = db.Column(db.String(10))  # HTTP method (GET, POST, PUT, DELETE)

    # Additional info
    description = db.Column(db.Text)  # Human readable description
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id")
    )  # Related company if applicable
    plan_id = db.Column(
        db.Integer, db.ForeignKey("plans.id")
    )  # Related plan if applicable

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "method": self.method,
            "description": self.description,
            "company_id": self.company_id,
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<UserLog {self.user_email} - {self.action} {self.entity_type}>"
