from __future__ import annotations

from datetime import datetime

from . import db


class ProcessPortalPublication(db.Model):
    __tablename__ = "process_portal_publications"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    source_bpmn_diagram_id = db.Column(db.Integer, db.ForeignKey("process_bpmn_diagrams.id"), nullable=True, index=True)
    publication_version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default="draft")  # draft, published, archived
    visibility_scope = db.Column(db.String(30), nullable=False, default="linked_process")  # company, linked_process, restricted
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    content_snapshot_json = db.Column(db.JSON, nullable=False, default=dict)
    published_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process = db.relationship(
        "Process",
        backref=db.backref("portal_publications", lazy="dynamic", cascade="all, delete-orphan"),
    )
    source_bpmn_diagram = db.relationship(
        "ProcessBpmnDiagram",
        foreign_keys=[source_bpmn_diagram_id],
        backref=db.backref("portal_publications", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "source_bpmn_diagram_id": self.source_bpmn_diagram_id,
            "publication_version": self.publication_version,
            "status": self.status,
            "visibility_scope": self.visibility_scope,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "content_snapshot_json": self.content_snapshot_json or {},
            "published_by_user_id": self.published_by_user_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessPortalPublicationGrant(db.Model):
    __tablename__ = "process_portal_publication_grants"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    publication_id = db.Column(
        db.Integer,
        db.ForeignKey("process_portal_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grant_scope = db.Column(db.String(30), nullable=False, default="user")  # company, user, employee, process, activity
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=True, index=True)
    process_routine_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), nullable=True, index=True)
    bpmn_element_id = db.Column(db.String(255), nullable=True, index=True)
    can_view = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    publication = db.relationship(
        "ProcessPortalPublication",
        backref=db.backref("grants", lazy="dynamic", cascade="all, delete-orphan"),
    )
    employee = db.relationship("Employee", foreign_keys=[employee_id])
    process = db.relationship("Process", foreign_keys=[process_id])
    process_routine = db.relationship("ProcessRoutine", foreign_keys=[process_routine_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "publication_id": self.publication_id,
            "grant_scope": self.grant_scope,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "process_id": self.process_id,
            "process_routine_id": self.process_routine_id,
            "bpmn_element_id": self.bpmn_element_id,
            "can_view": bool(self.can_view),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
