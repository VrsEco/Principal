"""create financial domain enablements

Revision ID: 20260320_1100
Revises: 20260319_0400
Create Date: 2026-03-20 11:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260320_1100"
down_revision = "20260319_0400"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_domain_enablements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("domain_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "domain_type", "source_id", name="uq_financial_domain_enablements_source"),
        sa.CheckConstraint("domain_type IN ('project', 'process')", name="ck_financial_domain_enablements_domain_type"),
    )
    op.create_index(op.f("ix_financial_domain_enablements_company_id"), "financial_domain_enablements", ["company_id"], unique=False)
    op.create_index(op.f("ix_financial_domain_enablements_domain_type"), "financial_domain_enablements", ["domain_type"], unique=False)
    op.create_index(op.f("ix_financial_domain_enablements_source_id"), "financial_domain_enablements", ["source_id"], unique=False)
    op.create_index(op.f("ix_financial_domain_enablements_is_enabled"), "financial_domain_enablements", ["is_enabled"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_financial_domain_enablements_is_enabled"), table_name="financial_domain_enablements")
    op.drop_index(op.f("ix_financial_domain_enablements_source_id"), table_name="financial_domain_enablements")
    op.drop_index(op.f("ix_financial_domain_enablements_domain_type"), table_name="financial_domain_enablements")
    op.drop_index(op.f("ix_financial_domain_enablements_company_id"), table_name="financial_domain_enablements")
    op.drop_table("financial_domain_enablements")
