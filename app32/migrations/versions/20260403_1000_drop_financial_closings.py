"""drop financial closings

Revision ID: 20260403_1000
Revises: 20260402_1200
Create Date: 2026-04-03 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260403_1000"
down_revision = "20260402_1200"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("financial_closings"):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("financial_closings")}
    for index_name in (
        "ix_financial_closings_status",
        "ix_financial_closings_period_end",
        "ix_financial_closings_period_start",
        "ix_financial_closings_company_id",
    ):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="financial_closings")

    op.drop_table("financial_closings")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("financial_closings"):
        return

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
