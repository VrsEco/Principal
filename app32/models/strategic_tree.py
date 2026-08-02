from __future__ import annotations

from datetime import datetime

from . import db


class StrategicTree(db.Model):
    __tablename__ = "strategic_trees"
    __table_args__ = (
        db.Index("ix_strategic_trees_company_status", "company_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    purpose = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="active", index=True)
    visibility_scope = db.Column(db.String(40), nullable=False, default="company_authorized")
    root_node_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "strategic_tree_nodes.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_strategic_trees_root_node",
        ),
        nullable=True,
        index=True,
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = db.Column(db.DateTime, nullable=True)

    nodes = db.relationship(
        "StrategicTreeNode",
        back_populates="tree",
        cascade="all, delete-orphan",
        foreign_keys="StrategicTreeNode.tree_id",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "purpose": self.purpose,
            "status": self.status,
            "visibility_scope": self.visibility_scope,
            "root_node_id": self.root_node_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StrategicTreeNode(db.Model):
    __tablename__ = "strategic_tree_nodes"
    __table_args__ = (
        db.Index("ix_strategic_tree_nodes_company_tree", "company_id", "tree_id"),
        db.Index("ix_strategic_tree_nodes_tree_parent", "tree_id", "parent_node_id"),
        db.CheckConstraint(
            "node_type IN ('root','theme','subtheme','investigation','decision','unfolding','parked')",
            name="ck_strategic_tree_nodes_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("strategic_trees.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_node_id = db.Column(db.Integer, db.ForeignKey("strategic_tree_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    node_type = db.Column(db.String(30), nullable=False, default="theme")
    title = db.Column(db.String(220), nullable=False)
    summary = db.Column(db.Text)
    visible_status = db.Column(db.String(30), nullable=False, default="collecting", index=True)
    technical_status = db.Column(db.String(30), nullable=False, default="captured", index=True)
    sensitivity_level = db.Column(db.String(20), nullable=False, default="internal")
    visibility_scope = db.Column(db.String(40), nullable=False, default="company_authorized")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)

    tree = db.relationship("StrategicTree", back_populates="nodes", foreign_keys=[tree_id])
    parent = db.relationship("StrategicTreeNode", remote_side=[id], backref="children")
    contributions = db.relationship(
        "StrategicTreeContribution",
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="StrategicTreeContribution.created_at.desc()",
    )

    def to_dict(self, *, include_children: bool = False) -> dict:
        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "tree_id": self.tree_id,
            "parent_node_id": self.parent_node_id,
            "node_type": self.node_type,
            "title": self.title,
            "summary": self.summary,
            "visible_status": self.visible_status,
            "technical_status": self.technical_status,
            "sensitivity_level": self.sensitivity_level,
            "visibility_scope": self.visibility_scope,
            "sort_order": self.sort_order,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            payload["children"] = [
                child.to_dict(include_children=True)
                for child in sorted(self.children, key=lambda item: (item.sort_order, item.id))
                if child.archived_at is None
            ]
        return payload


class StrategicTreeContribution(db.Model):
    __tablename__ = "strategic_tree_contributions"
    __table_args__ = (
        db.UniqueConstraint("company_id", "idempotency_key", name="uq_strategic_tree_contribution_idempotency"),
        db.Index("ix_strategic_tree_contributions_company_node", "company_id", "node_id"),
        db.CheckConstraint(
            "attribution_mode IN ('identified','confidential','pseudonymized')",
            name="ck_strategic_tree_contributions_attribution",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("strategic_trees.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = db.Column(db.Integer, db.ForeignKey("strategic_tree_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    contribution_type = db.Column(db.String(40), nullable=False, default="human_statement", index=True)
    source_type = db.Column(db.String(40), nullable=False, default="app32", index=True)
    source_ref = db.Column(db.String(240), nullable=True)
    attribution_mode = db.Column(db.String(30), nullable=False, default="identified")
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    participant_ref = db.Column(db.String(180), nullable=True)
    raw_content = db.Column(db.Text, nullable=False)
    sanitized_content = db.Column(db.Text, nullable=True)
    classification_json = db.Column(db.JSON, nullable=False, default=dict)
    confidence_state = db.Column(db.String(30), nullable=False, default="unverified")
    sensitivity_level = db.Column(db.String(20), nullable=False, default="internal")
    visibility_scope = db.Column(db.String(40), nullable=False, default="company_authorized")
    status = db.Column(db.String(30), nullable=False, default="active", index=True)
    idempotency_key = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    node = db.relationship("StrategicTreeNode", back_populates="contributions")

    def to_dict(self, *, content: str | None = None) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "tree_id": self.tree_id,
            "node_id": self.node_id,
            "contribution_type": self.contribution_type,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "attribution_mode": self.attribution_mode,
            "author_user_id": self.author_user_id if self.attribution_mode == "identified" else None,
            "content": self.raw_content if content is None else content,
            "classification": dict(self.classification_json or {}),
            "confidence_state": self.confidence_state,
            "sensitivity_level": self.sensitivity_level,
            "visibility_scope": self.visibility_scope,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StrategicTreeAuditEvent(db.Model):
    __tablename__ = "strategic_tree_audit_events"
    __table_args__ = (
        db.Index("ix_strategic_tree_audit_company_created", "company_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("strategic_trees.id", ondelete="SET NULL"), nullable=True, index=True)
    node_id = db.Column(db.Integer, db.ForeignKey("strategic_tree_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    contribution_id = db.Column(db.Integer, db.ForeignKey("strategic_tree_contributions.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    surface = db.Column(db.String(30), nullable=False, default="app32")
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
