from datetime import datetime

from sqlalchemy import text

from . import db


class ProcessExecutionAssignment(db.Model):
    """Destinatario canonico de uma atividade de instancia de processo."""

    __tablename__ = "process_execution_assignments"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_execution_id = db.Column(
        db.Integer,
        db.ForeignKey("process_instance_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_type = db.Column(db.String(20), nullable=False, default="employee")
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    role_key = db.Column(db.String(120), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="assigned", index=True)
    source = db.Column(db.String(40), nullable=False, default="instance_fallback")
    assigned_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    claimed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    activity_execution = db.relationship(
        "ProcessInstanceExecution",
        backref=db.backref("assignments", lazy="dynamic", cascade="all, delete-orphan"),
    )
    employee = db.relationship("Employee", foreign_keys=[employee_id])
    team = db.relationship("Team", foreign_keys=[team_id])

    __table_args__ = (
        db.CheckConstraint(
            "assignee_type IN ('employee', 'team', 'role')",
            name="ck_process_execution_assignment_type",
        ),
        db.CheckConstraint(
            "status IN ('assigned', 'claimed', 'completed', 'cancelled')",
            name="ck_process_execution_assignment_status",
        ),
        db.CheckConstraint(
            "(assignee_type = 'employee' AND employee_id IS NOT NULL AND team_id IS NULL AND role_key IS NULL) OR "
            "(assignee_type = 'team' AND employee_id IS NULL AND team_id IS NOT NULL AND role_key IS NULL) OR "
            "(assignee_type = 'role' AND employee_id IS NULL AND team_id IS NULL AND role_key IS NOT NULL)",
            name="ck_process_execution_assignment_target",
        ),
        db.Index(
            "ix_process_execution_assignment_company_activity_status",
            "company_id",
            "activity_execution_id",
            "status",
        ),
        db.Index(
            "ix_process_execution_assignment_company_employee_status",
            "company_id",
            "employee_id",
            "status",
        ),
        db.Index(
            "uq_process_execution_assignment_active",
            "company_id",
            "activity_execution_id",
            unique=True,
            postgresql_where=text("status IN ('assigned', 'claimed')"),
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "activity_execution_id": self.activity_execution_id,
            "assignee_type": self.assignee_type,
            "employee_id": self.employee_id,
            "team_id": self.team_id,
            "role_key": self.role_key,
            "status": self.status,
            "source": self.source,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
