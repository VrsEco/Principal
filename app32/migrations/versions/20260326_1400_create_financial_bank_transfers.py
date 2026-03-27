"""create financial bank transfers

Revision ID: 20260326_1400
Revises: 20260320_1200
Create Date: 2026-03-26 14:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260326_1400"
down_revision = "20260320_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_bank_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("transfer_code", sa.String(length=30), nullable=False),
        sa.Column("transfer_status", sa.String(length=20), nullable=False, server_default="posted"),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("document_number", sa.String(length=80), nullable=True),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("origin_bank_account_id", sa.Integer(), nullable=False),
        sa.Column("destination_bank_account_id", sa.Integer(), nullable=False),
        sa.Column("origin_entry_id", sa.Integer(), nullable=True),
        sa.Column("destination_entry_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["origin_bank_account_id"], ["financial_bank_accounts.id"]),
        sa.ForeignKeyConstraint(["destination_bank_account_id"], ["financial_bank_accounts.id"]),
        sa.ForeignKeyConstraint(["origin_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["destination_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "transfer_code", name="uq_financial_bank_transfers_company_code"),
        sa.CheckConstraint(
            "transfer_status IN ('posted', 'cancelled')",
            name="ck_financial_bank_transfers_status",
        ),
    )
    op.create_index(op.f("ix_financial_bank_transfers_company_id"), "financial_bank_transfers", ["company_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_transfer_status"), "financial_bank_transfers", ["transfer_status"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_competence_date"), "financial_bank_transfers", ["competence_date"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_transfer_date"), "financial_bank_transfers", ["transfer_date"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_origin_bank_account_id"), "financial_bank_transfers", ["origin_bank_account_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_destination_bank_account_id"), "financial_bank_transfers", ["destination_bank_account_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_origin_entry_id"), "financial_bank_transfers", ["origin_entry_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_destination_entry_id"), "financial_bank_transfers", ["destination_entry_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_created_by_user_id"), "financial_bank_transfers", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_financial_bank_transfers_created_by_employee_id"), "financial_bank_transfers", ["created_by_employee_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_financial_bank_transfers_created_by_employee_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_created_by_user_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_destination_entry_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_origin_entry_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_destination_bank_account_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_origin_bank_account_id"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_transfer_date"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_competence_date"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_transfer_status"), table_name="financial_bank_transfers")
    op.drop_index(op.f("ix_financial_bank_transfers_company_id"), table_name="financial_bank_transfers")
    op.drop_table("financial_bank_transfers")
