"""Persist selected MCP harness per user token.

Revision ID: 20260718_1200
Revises: 20260702_1800
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa

revision = "20260718_1200"
down_revision = "20260702_1800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_mcp_tokens", sa.Column("last_harness_key", sa.String(length=120), nullable=True))
    op.create_index("ix_user_mcp_tokens_last_harness_key", "user_mcp_tokens", ["last_harness_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_mcp_tokens_last_harness_key", table_name="user_mcp_tokens")
    op.drop_column("user_mcp_tokens", "last_harness_key")
