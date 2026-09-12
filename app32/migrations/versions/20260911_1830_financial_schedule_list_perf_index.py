"""Índice tenant-safe para a leitura ordenada da lista de títulos financeiros."""

from alembic import op
import sqlalchemy as sa


revision = "20260911_1830"
down_revision = "20260909_1000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_financial_schedules_company_status_due_active",
        "financial_schedules",
        ["company_id", "status", "next_due_date", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    op.drop_index("ix_financial_schedules_company_status_due_active", table_name="financial_schedules")
