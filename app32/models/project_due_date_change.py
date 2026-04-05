from datetime import datetime

from . import db


class ProjectTaskDueDateChangeRequest(db.Model):
    """Solicitações e histórico de alteração de prazo de atividades."""

    __tablename__ = "project_task_due_date_change_requests"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    task_id = db.Column(
        db.Integer, db.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
    )
    request_type = db.Column(db.String(20), nullable=False, default="postpone")
    old_due_date = db.Column(db.Date, nullable=True)
    requested_due_date = db.Column(db.Date, nullable=True)
    approved_due_date = db.Column(db.Date, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    requested_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    requested_by_name = db.Column(db.String(200), nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_name = db.Column(db.String(200), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_note = db.Column(db.Text, nullable=True)
    was_after_due_date_when_requested = db.Column(
        db.Boolean, nullable=False, default=False
    )
    penalty_points = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project = db.relationship("Project", backref="due_date_change_requests")
    task = db.relationship(
        "ProjectTask",
        backref=db.backref(
            "due_date_change_requests",
            cascade="all, delete-orphan",
            passive_deletes=True,
            lazy="dynamic",
        ),
    )

    def to_dict(self) -> dict:
        def _fmt_date(value):
            return value.isoformat() if value else None

        def _fmt_dt(value):
            return value.isoformat() if value else None

        return {
            "id": self.id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "request_type": self.request_type,
            "old_due_date": _fmt_date(self.old_due_date),
            "requested_due_date": _fmt_date(self.requested_due_date),
            "approved_due_date": _fmt_date(self.approved_due_date),
            "reason": self.reason,
            "status": self.status,
            "requested_by_user_id": self.requested_by_user_id,
            "requested_by_name": self.requested_by_name,
            "requested_at": _fmt_dt(self.requested_at),
            "approved_by_user_id": self.approved_by_user_id,
            "approved_by_name": self.approved_by_name,
            "approved_at": _fmt_dt(self.approved_at),
            "approval_note": self.approval_note,
            "was_after_due_date_when_requested": bool(
                self.was_after_due_date_when_requested
            ),
            "penalty_points": float(self.penalty_points or 0),
            "created_at": _fmt_dt(self.created_at),
            "updated_at": _fmt_dt(self.updated_at),
        }

    def __repr__(self) -> str:
        return (
            f"<ProjectTaskDueDateChangeRequest id={self.id} task_id={self.task_id} "
            f"status={self.status} type={self.request_type}>"
        )
