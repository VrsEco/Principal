from datetime import datetime

from . import db


PROCESS_ARTIFACT_TYPES = ("pop", "form", "check", "ai", "data_in", "data_out")
PROCESS_ARTIFACT_DEFINITION_STATUSES = ("draft", "published", "archived")
PROCESS_ARTIFACT_EXECUTION_STATUSES = (
    "pending",
    "in_progress",
    "waiting_external",
    "waiting_human",
    "completed",
    "failed",
    "skipped",
)


class ProcessActivityArtifactDefinition(db.Model):
    """Definição versionada de um artefato operacional de atividade BPMN."""

    __tablename__ = "process_activity_artifact_definitions"
    __table_args__ = (
        db.CheckConstraint(
            "artifact_type IN ('pop', 'form', 'check', 'ai', 'data_in', 'data_out')",
            name="ck_process_artifact_definition_type",
        ),
        db.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_process_artifact_definition_status",
        ),
        db.CheckConstraint("version > 0", name="ck_process_artifact_definition_version_positive"),
        db.UniqueConstraint(
            "company_id",
            "process_id",
            "artifact_key",
            "version",
            name="uq_process_artifact_definition_version",
        ),
        db.UniqueConstraint(
            "company_id",
            "legacy_process_routine_id",
            "version",
            name="uq_process_artifact_definition_legacy_pop_version",
        ),
        db.Index(
            "ix_process_artifact_definition_company_process_type",
            "company_id",
            "process_id",
            "artifact_type",
        ),
        db.Index(
            "ix_process_artifact_definition_legacy_pop",
            "legacy_process_routine_id",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    artifact_key = db.Column(db.String(64), nullable=False)
    artifact_type = db.Column(db.String(30), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default="draft", index=True)
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)
    legacy_process_routine_id = db.Column(
        db.Integer,
        db.ForeignKey("process_routines.id"),
        nullable=True,
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process = db.relationship(
        "Process",
        backref=db.backref("activity_artifact_definitions", lazy="dynamic", cascade="all, delete-orphan"),
    )
    legacy_process_routine = db.relationship(
        "ProcessRoutine",
        backref=db.backref("artifact_definitions", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "artifact_key": self.artifact_key,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "configuration_json": self.configuration_json or {},
            "legacy_process_routine_id": self.legacy_process_routine_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessActivityArtifactLink(db.Model):
    """Associação externa entre uma definição publicada e um elemento BPMN."""

    __tablename__ = "process_activity_artifact_links"
    __table_args__ = (
        db.CheckConstraint("display_order >= 0", name="ck_process_artifact_link_order_non_negative"),
        db.UniqueConstraint(
            "company_id",
            "process_id",
            "bpmn_element_id",
            "artifact_definition_id",
            name="uq_process_artifact_link_activity_definition",
        ),
        db.Index(
            "ix_process_artifact_link_company_activity",
            "company_id",
            "process_id",
            "bpmn_element_id",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    bpmn_element_id = db.Column(db.String(255), nullable=False, index=True)
    artifact_definition_id = db.Column(
        db.Integer,
        db.ForeignKey("process_activity_artifact_definitions.id"),
        nullable=False,
        index=True,
    )
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    completion_policy_json = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process = db.relationship(
        "Process",
        backref=db.backref("activity_artifact_links", lazy="dynamic", cascade="all, delete-orphan"),
    )
    artifact_definition = db.relationship(
        "ProcessActivityArtifactDefinition",
        backref=db.backref("activity_links", lazy="dynamic", cascade="all, delete-orphan"),
    )

    def to_dict(self, *, include_definition=True):
        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "bpmn_element_id": self.bpmn_element_id,
            "artifact_definition_id": self.artifact_definition_id,
            "display_order": self.display_order,
            "is_required": bool(self.is_required),
            "completion_policy_json": self.completion_policy_json or {},
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_definition:
            payload["artifact"] = self.artifact_definition.to_dict() if self.artifact_definition else None
        return payload


class ProcessActivityArtifactExecution(db.Model):
    """Snapshot e estado de um artefato dentro de uma execução de atividade."""

    __tablename__ = "process_activity_artifact_executions"
    __table_args__ = (
        db.CheckConstraint(
            "artifact_type IN ('pop', 'form', 'check', 'ai', 'data_in', 'data_out')",
            name="ck_process_artifact_execution_type",
        ),
        db.CheckConstraint(
            "status IN ('pending', 'in_progress', 'waiting_external', 'waiting_human', 'completed', 'failed', 'skipped')",
            name="ck_process_artifact_execution_status",
        ),
        db.CheckConstraint("artifact_version > 0", name="ck_process_artifact_execution_version_positive"),
        db.UniqueConstraint(
            "company_id",
            "activity_execution_id",
            "artifact_definition_id",
            name="uq_process_artifact_execution_activity_definition",
        ),
        db.Index(
            "ix_process_artifact_execution_company_instance_status",
            "company_id",
            "process_instance_id",
            "status",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_instance_id = db.Column(
        db.Integer,
        db.ForeignKey("process_instances.id"),
        nullable=False,
        index=True,
    )
    activity_execution_id = db.Column(
        db.Integer,
        db.ForeignKey("process_instance_executions.id"),
        nullable=False,
        index=True,
    )
    artifact_definition_id = db.Column(
        db.Integer,
        db.ForeignKey("process_activity_artifact_definitions.id"),
        nullable=False,
        index=True,
    )
    artifact_key = db.Column(db.String(64), nullable=False)
    artifact_type = db.Column(db.String(30), nullable=False, index=True)
    artifact_version = db.Column(db.Integer, nullable=False)
    definition_snapshot_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    input_json = db.Column(db.JSON, nullable=False, default=dict)
    output_json = db.Column(db.JSON, nullable=False, default=dict)
    evidence_json = db.Column(db.JSON, nullable=False, default=dict)
    error_json = db.Column(db.JSON, nullable=False, default=dict)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process_instance = db.relationship(
        "ProcessInstance",
        backref=db.backref("artifact_executions", lazy="dynamic", cascade="all, delete-orphan"),
    )
    activity_execution = db.relationship(
        "ProcessInstanceExecution",
        backref=db.backref("artifact_executions", lazy="dynamic", cascade="all, delete-orphan"),
    )
    artifact_definition = db.relationship("ProcessActivityArtifactDefinition", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_instance_id": self.process_instance_id,
            "activity_execution_id": self.activity_execution_id,
            "artifact_definition_id": self.artifact_definition_id,
            "artifact_key": self.artifact_key,
            "artifact_type": self.artifact_type,
            "artifact_version": self.artifact_version,
            "definition_snapshot_json": self.definition_snapshot_json or {},
            "status": self.status,
            "input_json": self.input_json or {},
            "output_json": self.output_json or {},
            "evidence_json": self.evidence_json or {},
            "error_json": self.error_json or {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
