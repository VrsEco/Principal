from __future__ import annotations

from datetime import datetime

from . import db


class KnowledgeSource(db.Model):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        db.CheckConstraint(
            "(knowledge_scope = 'company' AND company_id IS NOT NULL) OR "
            "(knowledge_scope = 'product' AND company_id IS NULL)",
            name="ck_knowledge_sources_scope_company",
        ),
        db.Index(
            "uq_knowledge_sources_product_ref",
            "source_type",
            "source_ref",
            unique=True,
            postgresql_where=db.text("company_id IS NULL AND deleted_at IS NULL"),
            sqlite_where=db.text("company_id IS NULL AND deleted_at IS NULL"),
        ),
        db.Index(
            "uq_knowledge_sources_company_ref",
            "company_id",
            "source_type",
            "source_ref",
            unique=True,
            postgresql_where=db.text("company_id IS NOT NULL AND deleted_at IS NULL"),
            sqlite_where=db.text("company_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    knowledge_scope = db.Column(db.String(20), nullable=False, index=True)
    source_type = db.Column(db.String(80), nullable=False, index=True)
    source_ref = db.Column(db.String(180), nullable=False, index=True)
    knowledge_kind = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    canonical_uri = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="active", index=True)
    authority_level = db.Column(db.String(30), nullable=False, default="internal")
    version = db.Column(db.String(60), nullable=False, default="v1")
    product_version = db.Column(db.String(60), nullable=True, index=True)
    locale = db.Column(db.String(20), nullable=False, default="pt-BR")
    route_key = db.Column(db.String(160), nullable=True, index=True)
    module_key = db.Column(db.String(120), nullable=True, index=True)
    audience_json = db.Column(db.JSON, nullable=False, default=list)
    required_capabilities_json = db.Column(db.JSON, nullable=False, default=list)
    help_kind = db.Column(db.String(40), nullable=True, index=True)
    navigation_target = db.Column(db.String(240), nullable=True)
    tour_definition_id = db.Column(db.String(160), nullable=True)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    content_checksum = db.Column(db.String(64), nullable=False, index=True)
    valid_from = db.Column(db.DateTime, nullable=True)
    valid_to = db.Column(db.DateTime, nullable=True)
    source_updated_at = db.Column(db.DateTime, nullable=True)
    indexed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    company = db.relationship("Company", lazy="joined")
    chunks = db.relationship(
        "KnowledgeChunk",
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_order",
    )
    grants = db.relationship(
        "KnowledgeSourceGrant",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    def to_dict(self, *, include_chunks: bool = False) -> dict:
        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "knowledge_scope": self.knowledge_scope,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "knowledge_kind": self.knowledge_kind,
            "title": self.title,
            "canonical_uri": self.canonical_uri,
            "status": self.status,
            "authority_level": self.authority_level,
            "version": self.version,
            "product_version": self.product_version,
            "locale": self.locale,
            "route_key": self.route_key,
            "module_key": self.module_key,
            "audience": list(self.audience_json or []),
            "required_capabilities": list(self.required_capabilities_json or []),
            "help_kind": self.help_kind,
            "navigation_target": self.navigation_target,
            "tour_definition_id": self.tour_definition_id,
            "metadata": dict(self.metadata_json or {}),
            "content_checksum": self.content_checksum,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_updated_at": (
                self.source_updated_at.isoformat() if self.source_updated_at else None
            ),
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
        if include_chunks:
            payload["chunks"] = [chunk.to_dict() for chunk in self.chunks]
        return payload


class KnowledgeSourceGrant(db.Model):
    __tablename__ = "knowledge_source_grants"
    __table_args__ = (
        db.CheckConstraint(
            "(grant_scope = 'company' AND user_id IS NULL AND employee_id IS NULL) OR "
            "(grant_scope = 'user' AND user_id IS NOT NULL AND employee_id IS NULL) OR "
            "(grant_scope = 'employee' AND employee_id IS NOT NULL AND user_id IS NULL)",
            name="ck_knowledge_source_grants_scope_target",
        ),
        db.Index(
            "uq_knowledge_source_grants_company",
            "knowledge_source_id",
            unique=True,
            postgresql_where=db.text("grant_scope = 'company'"),
            sqlite_where=db.text("grant_scope = 'company'"),
        ),
        db.Index(
            "uq_knowledge_source_grants_user",
            "knowledge_source_id",
            "user_id",
            unique=True,
            postgresql_where=db.text("grant_scope = 'user'"),
            sqlite_where=db.text("grant_scope = 'user'"),
        ),
        db.Index(
            "uq_knowledge_source_grants_employee",
            "knowledge_source_id",
            "employee_id",
            unique=True,
            postgresql_where=db.text("grant_scope = 'employee'"),
            sqlite_where=db.text("grant_scope = 'employee'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    knowledge_source_id = db.Column(
        db.Integer,
        db.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grant_scope = db.Column(db.String(20), nullable=False, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    source = db.relationship("KnowledgeSource", back_populates="grants")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knowledge_source_id": self.knowledge_source_id,
            "company_id": self.company_id,
            "grant_scope": self.grant_scope,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "metadata": dict(self.metadata_json or {}),
        }


class KnowledgeChunk(db.Model):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        db.CheckConstraint(
            "(knowledge_scope = 'company' AND company_id IS NOT NULL) OR "
            "(knowledge_scope = 'product' AND company_id IS NULL)",
            name="ck_knowledge_chunks_scope_company",
        ),
        db.UniqueConstraint(
            "knowledge_source_id",
            "section_key",
            name="uq_knowledge_chunks_source_section",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    knowledge_source_id = db.Column(
        db.Integer,
        db.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    knowledge_scope = db.Column(db.String(20), nullable=False, index=True)
    section_key = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    chunk_order = db.Column(db.Integer, nullable=False, default=0)
    token_count = db.Column(db.Integer, nullable=False, default=0)
    content_checksum = db.Column(db.String(64), nullable=False, index=True)
    parent_chunk_id = db.Column(
        db.Integer,
        db.ForeignKey("knowledge_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_span = db.Column(db.String(240), nullable=True)
    adapter_version = db.Column(db.String(40), nullable=False, default="v1")
    parser_version = db.Column(db.String(40), nullable=False, default="v1")
    chunking_policy = db.Column(db.String(80), nullable=False, default="heading-v1")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    source = db.relationship("KnowledgeSource", back_populates="chunks")
    parent_chunk = db.relationship("KnowledgeChunk", remote_side=[id], lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knowledge_source_id": self.knowledge_source_id,
            "company_id": self.company_id,
            "knowledge_scope": self.knowledge_scope,
            "section_key": self.section_key,
            "content": self.content,
            "metadata": dict(self.metadata_json or {}),
            "chunk_order": self.chunk_order,
            "token_count": self.token_count,
            "content_checksum": self.content_checksum,
            "parent_chunk_id": self.parent_chunk_id,
            "source_span": self.source_span,
            "adapter_version": self.adapter_version,
            "parser_version": self.parser_version,
            "chunking_policy": self.chunking_policy,
        }


class KnowledgeIndexRun(db.Model):
    __tablename__ = "knowledge_index_runs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    knowledge_scope = db.Column(db.String(20), nullable=False, index=True)
    source_type = db.Column(db.String(80), nullable=False, index=True)
    trigger_kind = db.Column(db.String(30), nullable=False, default="scheduled", index=True)
    status = db.Column(db.String(30), nullable=False, default="running", index=True)
    discovered_count = db.Column(db.Integer, nullable=False, default=0)
    created_count = db.Column(db.Integer, nullable=False, default=0)
    updated_count = db.Column(db.Integer, nullable=False, default=0)
    unchanged_count = db.Column(db.Integer, nullable=False, default=0)
    deactivated_count = db.Column(db.Integer, nullable=False, default=0)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "knowledge_scope": self.knowledge_scope,
            "source_type": self.source_type,
            "trigger_kind": self.trigger_kind,
            "status": self.status,
            "discovered_count": self.discovered_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "deactivated_count": self.deactivated_count,
            "failed_count": self.failed_count,
            "error_message": self.error_message,
            "metadata": dict(self.metadata_json or {}),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class KnowledgeInteraction(db.Model):
    __tablename__ = "knowledge_interactions"
    __table_args__ = (
        db.CheckConstraint(
            "rating_status IN ('unrated', 'correct', 'partial', 'wrong')",
            name="ck_knowledge_interactions_rating_status",
        ),
        db.Index("ix_knowledge_interactions_company_created", "company_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    interaction_uuid = db.Column(db.String(64), nullable=False, unique=True, index=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_scope = db.Column(db.String(20), nullable=False, default="all", index=True)
    knowledge_scope = db.Column(db.String(20), nullable=False, default="company", index=True)
    question = db.Column(db.Text, nullable=False)
    normalized_question = db.Column(db.String(600), nullable=False, index=True)
    answer_preview = db.Column(db.Text, nullable=True)
    understanding_json = db.Column(db.JSON, nullable=False, default=dict)
    query_plan_json = db.Column(db.JSON, nullable=False, default=dict)
    citations_json = db.Column(db.JSON, nullable=False, default=list)
    actions_json = db.Column(db.JSON, nullable=False, default=list)
    warnings_json = db.Column(db.JSON, nullable=False, default=list)
    engine_version = db.Column(db.String(60), nullable=False, default="knowledge-v1")
    rating_status = db.Column(db.String(20), nullable=False, default="unrated", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    feedback_entries = db.relationship(
        "KnowledgeFeedback",
        back_populates="interaction",
        cascade="all, delete-orphan",
        order_by="KnowledgeFeedback.created_at",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "interaction_id": self.interaction_uuid,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "requested_scope": self.requested_scope,
            "knowledge_scope": self.knowledge_scope,
            "question": self.question,
            "normalized_question": self.normalized_question,
            "answer_preview": self.answer_preview,
            "understanding": dict(self.understanding_json or {}),
            "query_plan": dict(self.query_plan_json or {}),
            "citations": list(self.citations_json or []),
            "actions": list(self.actions_json or []),
            "warnings": list(self.warnings_json or []),
            "engine_version": self.engine_version,
            "rating_status": self.rating_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeFeedback(db.Model):
    __tablename__ = "knowledge_feedback"
    __table_args__ = (
        db.CheckConstraint(
            "rating IN ('correct', 'partial', 'wrong')",
            name="ck_knowledge_feedback_rating",
        ),
        db.CheckConstraint(
            "reason IS NULL OR reason IN ("
            "'wrong_subject', 'too_technical', 'missing_path', 'wrong_source', "
            "'incomplete', 'not_found', 'outdated')",
            name="ck_knowledge_feedback_reason",
        ),
        db.Index("ix_knowledge_feedback_company_rating", "company_id", "rating"),
    )

    id = db.Column(db.Integer, primary_key=True)
    interaction_id = db.Column(
        db.Integer,
        db.ForeignKey("knowledge_interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rating = db.Column(db.String(20), nullable=False, index=True)
    reason = db.Column(db.String(40), nullable=True, index=True)
    comment = db.Column(db.Text, nullable=True)
    expected_answer = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    interaction = db.relationship("KnowledgeInteraction", back_populates="feedback_entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "interaction_id": self.interaction.interaction_uuid if self.interaction else None,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "reason": self.reason,
            "comment": self.comment,
            "expected_answer": self.expected_answer,
            "metadata": dict(self.metadata_json or {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeTrainingProposal(db.Model):
    __tablename__ = "knowledge_training_proposals"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected', 'applied')",
            name="ck_knowledge_training_proposals_status",
        ),
        db.Index("ix_knowledge_training_company_status", "company_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    proposal_uuid = db.Column(db.String(64), nullable=False, unique=True, index=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    proposal_scope = db.Column(db.String(20), nullable=False, default="company", index=True)
    pattern = db.Column(db.String(240), nullable=False, index=True)
    suggested_intent = db.Column(db.String(60), nullable=True, index=True)
    suggested_domain = db.Column(db.String(80), nullable=True, index=True)
    suggestion_type = db.Column(db.String(40), nullable=False, index=True)
    evidence_count = db.Column(db.Integer, nullable=False, default=0)
    evidence_json = db.Column(db.JSON, nullable=False, default=list)
    sources_json = db.Column(db.JSON, nullable=False, default=list)
    recommendation_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(30), nullable=False, default="pending_review", index=True)
    created_by = db.Column(db.String(80), nullable=False, default="sapiens_training_robot")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "proposal_id": self.proposal_uuid,
            "company_id": self.company_id,
            "proposal_scope": self.proposal_scope,
            "pattern": self.pattern,
            "suggested_intent": self.suggested_intent,
            "suggested_domain": self.suggested_domain,
            "suggestion_type": self.suggestion_type,
            "evidence_count": self.evidence_count,
            "evidence": list(self.evidence_json or []),
            "sources": list(self.sources_json or []),
            "recommendation": dict(self.recommendation_json or {}),
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
