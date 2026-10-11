"""Chaves de idempotência das mutações do mcp-versus (tabela nova, sem alterar dados).

Revision ID: 20261011_1000
Revises: 20261007_1000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261011_1000"
down_revision = "20261007_1000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mcp_idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("principal_id", sa.String(120), nullable=False),
        sa.Column("tool_name", sa.String(160), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "company_id", "principal_id", "tool_name", "idempotency_key", name="uq_mcp_idempotency_scope"
        ),
    )
    op.create_index("ix_mcp_idempotency_keys_expires_at", "mcp_idempotency_keys", ["expires_at"])


def downgrade():
    op.drop_index("ix_mcp_idempotency_keys_expires_at", table_name="mcp_idempotency_keys")
    op.drop_table("mcp_idempotency_keys")
