"""Outbox confiável para provisionamento automático APP32 -> Keycloak.

Revision ID: 20260922_1000
Revises: 20260919_0001
"""
from alembic import op
import sqlalchemy as sa


revision = "20260922_1000"
down_revision = "20260919_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("identity_provisioning_outbox"):
        return
    op.create_table(
        "identity_provisioning_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("external_subject", sa.String(512), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("operation IN ('upsert_user', 'disable_user')", name="ck_identity_outbox_operation"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'succeeded', 'failed')", name="ck_identity_outbox_status"),
        sa.UniqueConstraint("user_id", "operation", "dedupe_key", name="uq_identity_outbox_dedupe"),
    )
    op.create_index("ix_identity_outbox_user", "identity_provisioning_outbox", ["user_id"])
    op.create_index("ix_identity_outbox_status_next_attempt", "identity_provisioning_outbox", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_table("identity_provisioning_outbox")
