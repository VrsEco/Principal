from datetime import datetime

from . import db


class AgentActionBacklogLink(db.Model):
    """Vínculo formal entre AgentAction (HITL/engenharia) e card do backlog AA.J.31."""

    __tablename__ = "agent_action_backlog_links"
    __table_args__ = (
        db.UniqueConstraint(
            "agent_action_id",
            name="uq_agent_action_backlog_links_agent_action_id",
        ),
        db.UniqueConstraint(
            "project_task_id",
            name="uq_agent_action_backlog_links_project_task_id",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    agent_action_id = db.Column(
        db.Integer, db.ForeignKey("agent_actions.id"), nullable=False, index=True
    )
    project_task_id = db.Column(
        db.Integer, db.ForeignKey("project_tasks.id"), nullable=False, index=True
    )
    link_type = db.Column(db.String(50), nullable=False, default="agent_action")
    backlog_project_code = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    action = db.relationship(
        "AgentAction",
        backref=db.backref("backlog_link", uselist=False),
        foreign_keys=[agent_action_id],
    )
    task = db.relationship(
        "ProjectTask",
        backref=db.backref("agent_action_backlog_link", uselist=False),
        foreign_keys=[project_task_id],
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "agent_action_id": self.agent_action_id,
            "project_task_id": self.project_task_id,
            "link_type": self.link_type,
            "backlog_project_code": self.backlog_project_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<AgentActionBacklogLink action={self.agent_action_id} "
            f"task={self.project_task_id}>"
        )
