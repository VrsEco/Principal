"""Auditoria da recuperação self-service da conexão OAuth.

Revision ID: 20260922_1100
Revises: 20260922_1000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260922_1100"
down_revision = "20260922_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("oauth_connection_recovery_audits"):
        return
    op.create_table(
        "oauth_connection_recovery_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="processing"),
        sa.Column("external_subject", sa.String(512), nullable=True),
        sa.Column("company_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_oauth_connection_recovery_audit_status"),
    )
    op.create_index("ix_oauth_connection_recovery_audit_user_created", "oauth_connection_recovery_audits", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("oauth_connection_recovery_audits")
