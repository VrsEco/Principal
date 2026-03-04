from datetime import datetime
from sqlalchemy import UniqueConstraint
from . import db


class AgentMenuOption(db.Model):
    """
    Opções de menu hierárquicas para orientar ações do agente por código.
    Permite menu global (company_id NULL) e menu específico por empresa.
    """
    __tablename__ = "agent_menu_options"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_agent_menu_options_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("agent_menu_options.id"), nullable=True)

    code = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    action_key = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Lista de objetos: [{"key": "...", "label": "..."}]
    required_fields = db.Column(db.JSON, default=list)
    keywords = db.Column(db.JSON, default=list)

    confirmation_template = db.Column(db.Text, nullable=True)
    execution_template = db.Column(db.Text, nullable=True)

    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    children = db.relationship(
        "AgentMenuOption",
        backref=db.backref("parent", remote_side=[id]),
        lazy="selectin"
    )

    def to_dict(self, include_children: bool = False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "title": self.title,
            "action_key": self.action_key,
            "description": self.description,
            "required_fields": self.required_fields or [],
            "keywords": self.keywords or [],
            "confirmation_template": self.confirmation_template,
            "execution_template": self.execution_template,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            data["children"] = [
                child.to_dict(include_children=False)
                for child in sorted(self.children, key=lambda c: (c.sort_order, c.code))
                if child.is_active
            ]
        return data

    def __repr__(self):
        return f"<AgentMenuOption {self.code}: {self.title}>"


class AgentMenuSession(db.Model):
    """
    Estado conversacional do menu para cada contexto de usuário/canal/thread.
    """
    __tablename__ = "agent_menu_sessions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "company_id",
            "channel",
            "thread_id",
            name="uq_agent_menu_sessions_context"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    channel = db.Column(db.String(40), nullable=False, default="web")
    thread_id = db.Column(db.String(120), nullable=False)

    status = db.Column(db.String(40), nullable=False, default="idle")
    selected_option_id = db.Column(db.Integer, db.ForeignKey("agent_menu_options.id"), nullable=True)

    collected_data = db.Column(db.JSON, default=dict)
    missing_fields = db.Column(db.JSON, default=list)
    last_user_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    selected_option = db.relationship("AgentMenuOption", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "channel": self.channel,
            "thread_id": self.thread_id,
            "status": self.status,
            "selected_option_id": self.selected_option_id,
            "collected_data": self.collected_data or {},
            "missing_fields": self.missing_fields or [],
            "last_user_message": self.last_user_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AgentMenuSession user={self.user_id} thread={self.thread_id} status={self.status}>"
