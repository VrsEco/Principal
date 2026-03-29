"""drop unused financial payment terms catalog

Revision ID: 20260328_2100
Revises: 20260328_1600
Create Date: 2026-03-28 21:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260328_2100"
down_revision = "20260328_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("financial_payment_terms")


def downgrade():
    op.create_table(
        "financial_payment_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_financial_payment_terms_company_code"),
    )
    op.create_index(op.f("ix_financial_payment_terms_company_id"), "financial_payment_terms", ["company_id"], unique=False)
    op.create_index(op.f("ix_financial_payment_terms_is_active"), "financial_payment_terms", ["is_active"], unique=False)
