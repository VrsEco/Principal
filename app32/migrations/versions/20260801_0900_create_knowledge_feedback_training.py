"""create knowledge feedback and training tables

Revision ID: 20260801_0900
Revises: 20260730_1800
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_0900"
down_revision = "20260730_1800"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_uuid", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_scope", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("knowledge_scope", sa.String(length=20), nullable=False, server_default="company"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("normalized_question", sa.String(length=600), nullable=False),
        sa.Column("answer_preview", sa.Text(), nullable=True),
        sa.Column("understanding_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("query_plan_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("citations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("actions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("warnings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("engine_version", sa.String(length=60), nullable=False, server_default="knowledge-v1"),
        sa.Column("rating_status", sa.String(length=20), nullable=False, server_default="unrated"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rating_status IN ('unrated', 'correct', 'partial', 'wrong')", name="ck_knowledge_interactions_rating_status"),
    )
    op.create_index("uq_knowledge_interactions_uuid", "knowledge_interactions", ["interaction_uuid"], unique=True)
    op.create_index("ix_knowledge_interactions_company_created", "knowledge_interactions", ["company_id", "created_at"])
    op.create_index("ix_knowledge_interactions_normalized_question", "knowledge_interactions", ["normalized_question"])
    op.create_index("ix_knowledge_interactions_rating_status", "knowledge_interactions", ["rating_status"])

    op.create_table(
        "knowledge_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_id", sa.Integer(), sa.ForeignKey("knowledge_interactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rating IN ('correct', 'partial', 'wrong')", name="ck_knowledge_feedback_rating"),
        sa.CheckConstraint("reason IS NULL OR reason IN ('wrong_subject', 'too_technical', 'missing_path', 'wrong_source', 'incomplete', 'not_found', 'outdated')", name="ck_knowledge_feedback_reason"),
    )
    op.create_index("ix_knowledge_feedback_interaction_id", "knowledge_feedback", ["interaction_id"])
    op.create_index("ix_knowledge_feedback_company_rating", "knowledge_feedback", ["company_id", "rating"])
    op.create_index("ix_knowledge_feedback_reason", "knowledge_feedback", ["reason"])

    op.create_table(
        "knowledge_training_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proposal_uuid", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("proposal_scope", sa.String(length=20), nullable=False, server_default="company"),
        sa.Column("pattern", sa.String(length=240), nullable=False),
        sa.Column("suggested_intent", sa.String(length=60), nullable=True),
        sa.Column("suggested_domain", sa.String(length=80), nullable=True),
        sa.Column("suggestion_type", sa.String(length=40), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("sources_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("recommendation_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending_review"),
        sa.Column("created_by", sa.String(length=80), nullable=False, server_default="sapiens_training_robot"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending_review', 'approved', 'rejected', 'applied')", name="ck_knowledge_training_proposals_status"),
    )
    op.create_index("uq_knowledge_training_proposals_uuid", "knowledge_training_proposals", ["proposal_uuid"], unique=True)
    op.create_index("ix_knowledge_training_company_status", "knowledge_training_proposals", ["company_id", "status"])
    op.create_index("ix_knowledge_training_pattern", "knowledge_training_proposals", ["pattern"])


def downgrade():
    op.drop_index("ix_knowledge_training_pattern", table_name="knowledge_training_proposals")
    op.drop_index("ix_knowledge_training_company_status", table_name="knowledge_training_proposals")
    op.drop_index("uq_knowledge_training_proposals_uuid", table_name="knowledge_training_proposals")
    op.drop_table("knowledge_training_proposals")

    op.drop_index("ix_knowledge_feedback_reason", table_name="knowledge_feedback")
    op.drop_index("ix_knowledge_feedback_company_rating", table_name="knowledge_feedback")
    op.drop_index("ix_knowledge_feedback_interaction_id", table_name="knowledge_feedback")
    op.drop_table("knowledge_feedback")

    op.drop_index("ix_knowledge_interactions_rating_status", table_name="knowledge_interactions")
    op.drop_index("ix_knowledge_interactions_normalized_question", table_name="knowledge_interactions")
    op.drop_index("ix_knowledge_interactions_company_created", table_name="knowledge_interactions")
    op.drop_index("uq_knowledge_interactions_uuid", table_name="knowledge_interactions")
    op.drop_table("knowledge_interactions")
