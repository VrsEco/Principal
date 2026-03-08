from datetime import datetime

from . import db


class WorkflowExecutionLog(db.Model):
    """Ledger operacional de uso dos workflows."""

    __tablename__ = "workflow_execution_logs"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey("agent_menu_sessions.id"), nullable=True)
    workflow_option_id = db.Column(db.Integer, db.ForeignKey("agent_menu_options.id"), nullable=True)

    workflow_code = db.Column(db.String(40), nullable=False)
    action_key = db.Column(db.String(120), nullable=True)
    channel = db.Column(db.String(50), nullable=False, default="web")
    thread_id = db.Column(db.String(120), nullable=True)

    route_source = db.Column(db.String(40), nullable=True)
    intercept_stage = db.Column(db.String(60), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="selected")
    confidence_route = db.Column(db.String(30), nullable=True)

    request_text = db.Column(db.Text, nullable=True)
    response_text = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, default=dict)

    interaction_count = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    session = db.relationship("AgentMenuSession", lazy="joined")
    workflow_option = db.relationship("AgentMenuOption", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "workflow_option_id": self.workflow_option_id,
            "workflow_code": self.workflow_code,
            "action_key": self.action_key,
            "channel": self.channel,
            "thread_id": self.thread_id,
            "route_source": self.route_source,
            "intercept_stage": self.intercept_stage,
            "status": self.status,
            "confidence_route": self.confidence_route,
            "request_text": self.request_text,
            "response_text": self.response_text,
            "metadata_json": self.metadata_json or {},
            "interaction_count": self.interaction_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return (
            f"<WorkflowExecutionLog {self.workflow_code} "
            f"user={self.user_id} status={self.status}>"
        )
