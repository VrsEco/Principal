"""create financial reconciliation playbooks

Revision ID: 20260919_0001
Revises: 20260916_1000
Create Date: 2026-09-19 23:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260919_0001"
down_revision = "20260916_1000"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("financial_reconciliation_playbooks"):
        return
    op.create_table(
        "financial_reconciliation_playbooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("playbook_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("source_type", sa.String(length=20)),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False, server_default="contains"),
        sa.Column("match_value", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("confirmation_policy", sa.String(length=20), nullable=False, server_default="always"),
        sa.Column("action_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", sa.Integer()),
        sa.Column("created_by_agent", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("company_id", "playbook_code", name="uq_financial_reconciliation_playbooks_company_code"),
        sa.CheckConstraint("operator IN ('contains', 'equals', 'starts_with')", name="ck_financial_reconciliation_playbooks_operator"),
        sa.CheckConstraint("action_type IN ('classify_only', 'transfer', 'schedule_settlement', 'direct_entry', 'bordero')", name="ck_financial_reconciliation_playbooks_action"),
        sa.CheckConstraint("confirmation_policy IN ('always', 'suggest', 'never')", name="ck_financial_reconciliation_playbooks_confirmation"),
    )
    op.create_index("ix_financial_reconciliation_playbooks_company_active", "financial_reconciliation_playbooks", ["company_id", "is_active"])
    op.create_index("ix_financial_reconciliation_playbooks_company_priority", "financial_reconciliation_playbooks", ["company_id", "priority"])


def downgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("financial_reconciliation_playbooks"):
        op.drop_table("financial_reconciliation_playbooks")
