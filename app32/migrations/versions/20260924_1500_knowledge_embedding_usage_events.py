"""Eventos de consumo de embeddings por empresa/data-hora (sem texto).

Revision ID: 20260924_1500
Revises: 20260924_1400
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_1500"
down_revision = "20260924_1400"
branch_labels = None
depends_on = None

TABLE = "knowledge_embedding_usage_events"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABLE):
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("knowledge_index_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query_id", sa.String(64), nullable=True),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("embedding_version", sa.String(40), nullable=False),
        sa.Column("index_generation", sa.Integer(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("kind IN ('index', 'query')", name="ck_knowledge_embedding_usage_kind"),
    )
    op.create_index("ix_knowledge_embedding_usage_events_occurred_at", TABLE, ["occurred_at"])
    op.create_index("ix_knowledge_embedding_usage_events_company_id", TABLE, ["company_id", "occurred_at"])
    op.create_index("ix_knowledge_embedding_usage_events_kind", TABLE, ["kind"])
    op.create_index("ix_knowledge_embedding_usage_events_run_id", TABLE, ["run_id"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABLE):
        op.drop_table(TABLE)
