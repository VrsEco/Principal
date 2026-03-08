from datetime import datetime

from . import db


class WorkflowGapCandidate(db.Model):
    """Registro de necessidade de novo fluxo detectada em conversa."""

    __tablename__ = "workflow_gap_candidates"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    channel = db.Column(db.String(50), nullable=False, default="web")
    thread_id = db.Column(db.String(120), nullable=True, index=True)
    source = db.Column(db.String(50), nullable=False, default="ai_fallback")
    status = db.Column(db.String(30), nullable=False, default="inbox")
    resolution_type = db.Column(db.String(30), nullable=False, default="resolved_by_ai")
    title = db.Column(db.String(255), nullable=False)
    user_request_text = db.Column(db.Text, nullable=False)
    normalized_intent = db.Column(db.String(255), nullable=True)
    suggested_flow_name = db.Column(db.String(255), nullable=True)
    business_outcome = db.Column(db.Text, nullable=True)
    matched_workflow_codes = db.Column(db.JSON, default=list)
    telemetry = db.Column(db.JSON, default=dict)
    app_project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    app_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id"), nullable=True)
    app_task_code = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", foreign_keys=[app_project_id])
    task = db.relationship("ProjectTask", foreign_keys=[app_task_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "thread_id": self.thread_id,
            "source": self.source,
            "status": self.status,
            "resolution_type": self.resolution_type,
            "title": self.title,
            "user_request_text": self.user_request_text,
            "normalized_intent": self.normalized_intent,
            "suggested_flow_name": self.suggested_flow_name,
            "business_outcome": self.business_outcome,
            "matched_workflow_codes": list(self.matched_workflow_codes or []),
            "telemetry": dict(self.telemetry or {}),
            "app_project_id": self.app_project_id,
            "app_task_id": self.app_task_id,
            "app_task_code": self.app_task_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<WorkflowGapCandidate {self.id}: {self.title[:60]}>"
