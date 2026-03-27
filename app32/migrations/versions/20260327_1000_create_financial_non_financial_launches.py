"""create financial non financial launches

Revision ID: 20260327_1000
Revises: 20260326_1400
Create Date: 2026-03-27 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260327_1000"
down_revision = "20260326_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_non_financial_launches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("launch_code", sa.String(length=30), nullable=False),
        sa.Column("launch_status", sa.String(length=20), nullable=False, server_default="posted"),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("title_number", sa.String(length=80), nullable=True),
        sa.Column("installment_number", sa.String(length=30), nullable=True),
        sa.Column("launch_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("counterparty_id", sa.Integer(), nullable=False),
        sa.Column("debit_chart_account_id", sa.Integer(), nullable=False),
        sa.Column("debit_cost_center_id", sa.Integer(), nullable=False),
        sa.Column("debit_domain_type", sa.String(length=20), nullable=True),
        sa.Column("debit_domain_source_id", sa.Integer(), nullable=True),
        sa.Column("credit_chart_account_id", sa.Integer(), nullable=False),
        sa.Column("credit_cost_center_id", sa.Integer(), nullable=False),
        sa.Column("credit_domain_type", sa.String(length=20), nullable=True),
        sa.Column("credit_domain_source_id", sa.Integer(), nullable=True),
        sa.Column("debit_entry_id", sa.Integer(), nullable=True),
        sa.Column("credit_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
        sa.Column("created_by_agent", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["counterparty_id"], ["financial_counterparties.id"]),
        sa.ForeignKeyConstraint(["debit_chart_account_id"], ["financial_chart_accounts.id"]),
        sa.ForeignKeyConstraint(["debit_cost_center_id"], ["financial_cost_centers.id"]),
        sa.ForeignKeyConstraint(["credit_chart_account_id"], ["financial_chart_accounts.id"]),
        sa.ForeignKeyConstraint(["credit_cost_center_id"], ["financial_cost_centers.id"]),
        sa.ForeignKeyConstraint(["debit_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["credit_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "launch_code", name="uq_financial_non_financial_launches_company_code"),
        sa.CheckConstraint(
            "launch_status IN ('posted', 'cancelled')",
            name="ck_financial_non_financial_launches_status",
        ),
        sa.CheckConstraint(
            "(debit_domain_type IS NULL) OR (debit_domain_type IN ('project', 'process'))",
            name="ck_financial_non_financial_launches_debit_domain_type",
        ),
        sa.CheckConstraint(
            "(credit_domain_type IS NULL) OR (credit_domain_type IN ('project', 'process'))",
            name="ck_financial_non_financial_launches_credit_domain_type",
        ),
    )
    op.create_index(op.f("ix_financial_non_financial_launches_company_id"), "financial_non_financial_launches", ["company_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_launch_status"), "financial_non_financial_launches", ["launch_status"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_launch_date"), "financial_non_financial_launches", ["launch_date"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_counterparty_id"), "financial_non_financial_launches", ["counterparty_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_debit_chart_account_id"), "financial_non_financial_launches", ["debit_chart_account_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_debit_cost_center_id"), "financial_non_financial_launches", ["debit_cost_center_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_debit_domain_type"), "financial_non_financial_launches", ["debit_domain_type"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_debit_domain_source_id"), "financial_non_financial_launches", ["debit_domain_source_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_credit_chart_account_id"), "financial_non_financial_launches", ["credit_chart_account_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_credit_cost_center_id"), "financial_non_financial_launches", ["credit_cost_center_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_credit_domain_type"), "financial_non_financial_launches", ["credit_domain_type"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_credit_domain_source_id"), "financial_non_financial_launches", ["credit_domain_source_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_debit_entry_id"), "financial_non_financial_launches", ["debit_entry_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_credit_entry_id"), "financial_non_financial_launches", ["credit_entry_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_created_by_user_id"), "financial_non_financial_launches", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_financial_non_financial_launches_created_by_employee_id"), "financial_non_financial_launches", ["created_by_employee_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_financial_non_financial_launches_created_by_employee_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_created_by_user_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_credit_entry_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_debit_entry_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_credit_domain_source_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_credit_domain_type"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_credit_cost_center_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_credit_chart_account_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_debit_domain_source_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_debit_domain_type"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_debit_cost_center_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_debit_chart_account_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_counterparty_id"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_launch_date"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_launch_status"), table_name="financial_non_financial_launches")
    op.drop_index(op.f("ix_financial_non_financial_launches_company_id"), table_name="financial_non_financial_launches")
    op.drop_table("financial_non_financial_launches")
