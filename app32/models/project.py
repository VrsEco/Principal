from datetime import datetime

from sqlalchemy import UniqueConstraint, event, func, select, text

from . import db


class Project(db.Model):
    """Project model"""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("company_id", "code_sequence", name="uq_projects_company_code_sequence"),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    # Map 'name' attribute to 'title' column in DB to match PostgreSQL schema
    name = db.Column("title", db.String(200), nullable=False)
    description = db.Column(db.Text)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=True)
    okr_links = db.Column(db.JSON)  # List of OKR IDs
    kpis = db.Column(db.JSON)  # List of KPI names
    owner = db.Column(db.String(200))
    status = db.Column(
        db.String(50), default="planned"
    )  # planned, in_progress, completed, cancelled
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    deadline = db.synonym("end_date")
    budget = db.Column(db.String(100))  # e.g., "R$ 450k"
    notes = db.Column(db.Text)
    progress = db.Column(db.Integer, default=0)
    priority = db.Column(db.String(20), default="medium") # low, medium, high
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    delete_reason = db.Column(db.Text)
    code_sequence = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    tasks = db.relationship(
        "ProjectTask", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    portfolio = db.relationship("Portfolio", backref="projects_list")

    @property
    def task_stats(self):
        """Calculate task statistics for this project"""
        # We can't use self.tasks.filter... because it's lazy="dynamic"
        # and we want to avoid multiple queries if possible, but for properties it's okay
        all_tasks = self.tasks.all()
        now = datetime.now().date()
        
        visible_tasks = [t for t in all_tasks if not getattr(t, "is_deleted", False)]
        total = len(visible_tasks)
        completed = len([t for t in visible_tasks if t.stage == 'completed'])
        open_tasks = total - completed
        
        delayed = len([t for t in visible_tasks 
                      if t.stage != 'completed' 
                      and t.due_date 
                      and (t.due_date.date() if isinstance(t.due_date, datetime) else t.due_date) < now])
        
        return {
            "total": total,
            "open": open_tasks,
            "completed": completed,
            "delayed": delayed,
            "progress": round((completed / total) * 100) if total > 0 else 0
        }

    def update_progress(self):
        """Update the persistent progress field based on task stats"""
        stats = self.task_stats
        self.progress = stats['progress']
        return self.progress

    @property
    def code(self):
        """Generates the project code in format: COMPANY.J.SEQUENCE."""
        sequence = self.code_sequence or self.id
        return f"{self.company_code}.J.{sequence}"

    @property
    def company_code(self):
        from models.company import Company

        company = Company.query.get(self.company_id)
        if company:
            raw_code = company.client_code or company.name[:2].upper()
            cleaned = "".join(ch for ch in str(raw_code or "").strip().upper() if ch.isalnum())
            if cleaned:
                return cleaned
        return str(self.company_id or "").zfill(2) or "00"

    def to_dict(self):
        """Convert to dictionary"""
        stats = self.task_stats
        return {
            "id": self.id,
            "code": self.code,
            "company_id": self.company_id,
            "portfolio_id": self.portfolio_id,
            "code_sequence": self.code_sequence,
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "okr_links": self.okr_links,
            "kpis": self.kpis,
            "owner": self.owner,
            "status": self.status,
            "priority": self.priority,
            "progress": self.progress,
            "start_date": self.start_date.isoformat() if hasattr(self.start_date, 'isoformat') else self.start_date,
            "end_date": self.end_date.isoformat() if hasattr(self.end_date, 'isoformat') else self.end_date,
            "deadline": self.deadline.isoformat() if hasattr(self.deadline, 'isoformat') else self.deadline,
            "budget": self.budget,
            "notes": self.notes,
            "is_deleted": bool(self.is_deleted),
            "deleted_at": self.deleted_at.isoformat() if hasattr(self.deleted_at, 'isoformat') else self.deleted_at,
            "deleted_by_user_id": self.deleted_by_user_id,
            "delete_reason": self.delete_reason,
            "task_stats": stats,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }

    def __json__(self):
        """Allow Flask's tojson filter to serialize the model."""
        return self.to_dict()

    def __repr__(self):
        return f"<Project {self.name}>"


class ProjectTask(db.Model):
    """Project task model"""

    __tablename__ = "project_tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "code_sequence", name="uq_project_tasks_project_code_sequence"),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    what = db.Column(db.Text, nullable=False)
    who = db.Column(db.String(200)) # Legacy field, keep for now
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id")) # New link to Employee
    due_date = db.Column(db.Date)
    how = db.Column(db.Text)
    amount = db.Column(db.String(100))  # e.g., "R$ 80k"
    status = db.Column(
        db.String(50), default="planned"
    )  # planned, in_progress, completed, cancelled
    stage = db.Column(db.String(50), default="inbox") # inbox, waiting, executing, pending, suspended, completed
    priority = db.Column(db.String(20), default="normal") # low, normal, high, urgent
    notes = db.Column(db.Text)
    score_weight = db.Column(db.Numeric(10, 2), default=1)
    estimated_hours = db.Column(db.Numeric(10, 2), default=0)
    worked_hours = db.Column(db.Numeric(10, 2), default=0)
    completion_date = db.Column(db.Date)
    logs = db.Column(db.JSON, default=list)  # Diary/journal entries
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    delete_reason = db.Column(db.Text)
    code_sequence = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    employee = db.relationship("Employee", backref="tasks_assigned")

    @property
    def employee_name(self):
        """Returns the name of the assigned employee or fallback to legacy 'who'"""
        if self.employee:
            return self.employee.name
        return self.who or "Sem responsável"

    @property
    def project_name(self):
        """Returns the name of the associated project"""
        return self.project.name if self.project else "Individual"

    @property
    def code(self):
        """Generates the activity code in format: COMPANY.J.PROJECT_SEQUENCE.TASK_SEQUENCE."""
        if not self.project:
            return f"IND.{self.id}"

        sequence = self.code_sequence or self.id
        return f"{self.project.code}.{sequence}"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "code": self.code,
            "project_id": self.project_id,
            "code_sequence": self.code_sequence,
            "what": self.what,
            "who": self.who,
            "employee_id": self.employee_id,
            "due_date": self.due_date.isoformat() if hasattr(self.due_date, 'isoformat') else self.due_date,
            "completion_date": self.completion_date.isoformat() if hasattr(self.completion_date, 'isoformat') else self.completion_date,
            "how": self.how,
            "amount": self.amount,
            "status": self.status,
            "stage": self.stage,
            "priority": self.priority,
            "employee_name": self.employee_name,
            "project_name": self.project_name,
            "notes": self.notes,
            "score_weight": float(self.score_weight) if self.score_weight is not None else 1.0,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours is not None else 0.0,
            "worked_hours": float(self.worked_hours) if self.worked_hours is not None else 0.0,
            "logs": self.logs or [],
            "is_deleted": bool(self.is_deleted),
            "deleted_at": self.deleted_at.isoformat() if hasattr(self.deleted_at, 'isoformat') else self.deleted_at,
            "deleted_by_user_id": self.deleted_by_user_id,
            "delete_reason": self.delete_reason,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }

    def __json__(self):
        """Allow Flask's tojson filter to serialize the model."""
        return self.to_dict()

    def __repr__(self):
        return f"<ProjectTask {self.what[:50]}...>"


def _dialect_is_postgresql(connection) -> bool:
    return getattr(getattr(connection, "dialect", None), "name", "") == "postgresql"


def _allocate_scoped_sequence(connection, table_name: str, scope_column: str, scope_value: int) -> int:
    if _dialect_is_postgresql(connection):
        lock_key = 1001 if table_name == "projects" else 1002
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key, :scope_value)"),
            {"lock_key": lock_key, "scope_value": int(scope_value)},
        )

    table = Project.__table__ if table_name == "projects" else ProjectTask.__table__
    stmt = select(func.coalesce(func.max(table.c.code_sequence), 0) + 1).where(
        getattr(table.c, scope_column) == scope_value
    )
    return int(connection.execute(stmt).scalar() or 1)


@event.listens_for(Project, "before_insert")
def _assign_project_code_sequence(mapper, connection, target):
    if target.code_sequence or not target.company_id:
        return
    target.code_sequence = _allocate_scoped_sequence(connection, "projects", "company_id", target.company_id)


@event.listens_for(ProjectTask, "before_insert")
def _assign_project_task_code_sequence(mapper, connection, target):
    if target.code_sequence or not target.project_id:
        return
    target.code_sequence = _allocate_scoped_sequence(connection, "project_tasks", "project_id", target.project_id)


class ProjectActivityCollaborator(db.Model):
    """Collaborator for project activities/tasks"""

    __tablename__ = "project_activity_collaborators"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer, db.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )
    role = db.Column(db.String(32), default="executor")  # responsible, executor, observer
    estimated_hours = db.Column(db.Numeric(10, 2), default=0)
    worked_hours = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    employee = db.relationship("Employee", backref="project_activities")
    activity = db.relationship("ProjectTask", backref="collaborators")

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else "Unknown",
            "role": self.role,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else 0,
            "worked_hours": float(self.worked_hours) if self.worked_hours else 0,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProjectTaskHoursSummary(db.Model):
    """Aggregate hours summary for a project task"""
    __tablename__ = "project_task_hours_summary"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_estimated_hours = db.Column(db.Numeric(10, 2), default=0)
    total_worked_hours = db.Column(db.Numeric(10, 2), default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = db.relationship("ProjectTask", backref=db.backref("hours_summary", uselist=False))


class ProjectTaskDependency(db.Model):
    """Dependência finish_to_start entre atividades do mesmo projeto.

    Regra: a ``predecessor_task_id`` deve estar com stage='completed'
    para que a ``successor_task_id`` seja considerada desbloqueada.
    O bloqueio é SOFT — apenas visual, sem impedir a ação do usuário.
    """

    __tablename__ = "project_task_dependencies"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    predecessor_task_id = db.Column(
        db.Integer, db.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
    )
    successor_task_id = db.Column(
        db.Integer, db.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
    )
    created_by_employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relacionamentos para navegação do grafo
    predecessor = db.relationship(
        "ProjectTask",
        foreign_keys=[predecessor_task_id],
        backref=db.backref("successor_deps", cascade="all, delete-orphan", passive_deletes=True),
    )
    successor = db.relationship(
        "ProjectTask",
        foreign_keys=[successor_task_id],
        backref=db.backref("predecessor_deps", cascade="all, delete-orphan", passive_deletes=True),
    )
    created_by = db.relationship("Employee", foreign_keys=[created_by_employee_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "predecessor_task_id": self.predecessor_task_id,
            "predecessor_what": self.predecessor.what if self.predecessor else None,
            "predecessor_stage": self.predecessor.stage if self.predecessor else None,
            "successor_task_id": self.successor_task_id,
            "created_by_employee_id": self.created_by_employee_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<ProjectTaskDependency predecessor={self.predecessor_task_id}"
            f" → successor={self.successor_task_id}>"
        )
