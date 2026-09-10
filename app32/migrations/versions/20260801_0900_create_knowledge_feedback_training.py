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


def _assert_existing_contract(inspector: sa.Inspector, table_name: str, columns: tuple[str, ...], constraints: tuple[str, ...]) -> None:
    actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
    actual_constraints = {
        constraint["name"]
        for constraint in (*inspector.get_check_constraints(table_name), *inspector.get_unique_constraints(table_name))
        if constraint.get("name")
    }
    missing_columns = sorted(set(columns) - actual_columns)
    missing_constraints = sorted(set(constraints) - actual_constraints)
    if missing_columns or missing_constraints:
        raise RuntimeError(
            f"{table_name} já existe, mas não atende ao contrato da revision 20260801_0900; "
            f"colunas ausentes={missing_columns}, constraints ausentes={missing_constraints}."
        )


def _create_index_if_needed(name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    """Preserva índice equivalente legado, mesmo sob nome anterior."""

    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    if any(tuple(index.get("column_names") or ()) == tuple(columns) and bool(index.get("unique")) == unique for index in indexes):
        return
    op.create_index(name, table_name, columns, unique=unique, if_not_exists=True)


def upgrade():
    inspector = sa.inspect(op.get_bind())
    contracts = (
        ("knowledge_interactions", ("id", "interaction_uuid", "company_id", "user_id", "employee_id", "requested_scope", "knowledge_scope", "question", "normalized_question", "answer_preview", "understanding_json", "query_plan_json", "citations_json", "actions_json", "warnings_json", "engine_version", "rating_status", "created_at", "updated_at"), ("ck_knowledge_interactions_rating_status",)),
        ("knowledge_feedback", ("id", "interaction_id", "company_id", "user_id", "rating", "reason", "comment", "expected_answer", "metadata_json", "created_at"), ("ck_knowledge_feedback_rating", "ck_knowledge_feedback_reason")),
        ("knowledge_training_proposals", ("id", "proposal_uuid", "company_id", "proposal_scope", "pattern", "suggested_intent", "suggested_domain", "suggestion_type", "evidence_count", "evidence_json", "sources_json", "recommendation_json", "status", "created_by", "created_at", "updated_at"), ("ck_knowledge_training_proposals_status",)),
    )
    for table_name, columns, constraints in contracts:
        if inspector.has_table(table_name):
            _assert_existing_contract(inspector, table_name, columns, constraints)

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
        if_not_exists=True,
    )
    _create_index_if_needed("uq_knowledge_interactions_uuid", "knowledge_interactions", ["interaction_uuid"], unique=True)
    _create_index_if_needed("ix_knowledge_interactions_company_created", "knowledge_interactions", ["company_id", "created_at"])
    _create_index_if_needed("ix_knowledge_interactions_normalized_question", "knowledge_interactions", ["normalized_question"])
    _create_index_if_needed("ix_knowledge_interactions_rating_status", "knowledge_interactions", ["rating_status"])

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
        if_not_exists=True,
    )
    _create_index_if_needed("ix_knowledge_feedback_interaction_id", "knowledge_feedback", ["interaction_id"])
    _create_index_if_needed("ix_knowledge_feedback_company_rating", "knowledge_feedback", ["company_id", "rating"])
    _create_index_if_needed("ix_knowledge_feedback_reason", "knowledge_feedback", ["reason"])

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
        if_not_exists=True,
    )
    _create_index_if_needed("uq_knowledge_training_proposals_uuid", "knowledge_training_proposals", ["proposal_uuid"], unique=True)
    _create_index_if_needed("ix_knowledge_training_company_status", "knowledge_training_proposals", ["company_id", "status"])
    _create_index_if_needed("ix_knowledge_training_pattern", "knowledge_training_proposals", ["pattern"])


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
