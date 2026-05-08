"""create_user_mcp_tokens

Revision ID: 20260507_1100
Revises: 20260504_1700, 20260506_0900
Create Date: 2026-05-07 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_1100"
down_revision = ("20260504_1700", "20260506_0900")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_mcp_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_prefix", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_client_name", sa.String(length=120), nullable=True),
        sa.Column("last_surface", sa.String(length=32), nullable=True),
        sa.Column("last_company_id", sa.Integer(), nullable=True),
        sa.Column("notice_d3_sent_at", sa.DateTime(), nullable=True),
        sa.Column("notice_d0_sent_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["last_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_user_mcp_tokens_expires_at"), "user_mcp_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_mcp_tokens_status"), "user_mcp_tokens", ["status"], unique=False)
    op.create_index(op.f("ix_user_mcp_tokens_token_hash"), "user_mcp_tokens", ["token_hash"], unique=False)
    op.create_index(op.f("ix_user_mcp_tokens_user_id"), "user_mcp_tokens", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_user_mcp_tokens_user_id"), table_name="user_mcp_tokens")
    op.drop_index(op.f("ix_user_mcp_tokens_token_hash"), table_name="user_mcp_tokens")
    op.drop_index(op.f("ix_user_mcp_tokens_status"), table_name="user_mcp_tokens")
    op.drop_index(op.f("ix_user_mcp_tokens_expires_at"), table_name="user_mcp_tokens")
    op.drop_table("user_mcp_tokens")
