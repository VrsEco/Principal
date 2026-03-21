"""create financial closings

Revision ID: 20260319_0130
Revises: 20260319_0100
Create Date: 2026-03-19 01:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0130"
down_revision = "20260319_0100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_closings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text()),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("closed_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("closed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.UniqueConstraint("company_id", "period_start", "period_end", name="uq_financial_closings_period"),
        sa.CheckConstraint("status IN ('draft', 'closed', 'reopened')", name="ck_financial_closings_status"),
    )
    op.create_index("ix_financial_closings_company_id", "financial_closings", ["company_id"])
    op.create_index("ix_financial_closings_period_start", "financial_closings", ["period_start"])
    op.create_index("ix_financial_closings_period_end", "financial_closings", ["period_end"])
    op.create_index("ix_financial_closings_status", "financial_closings", ["status"])


def downgrade():
    op.drop_index("ix_financial_closings_status", table_name="financial_closings")
    op.drop_index("ix_financial_closings_period_end", table_name="financial_closings")
    op.drop_index("ix_financial_closings_period_start", table_name="financial_closings")
    op.drop_index("ix_financial_closings_company_id", table_name="financial_closings")
    op.drop_table("financial_closings")
