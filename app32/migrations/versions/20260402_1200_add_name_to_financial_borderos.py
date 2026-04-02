"""add name to financial borderos

Revision ID: 20260402_1200
Revises: 78a065a7c3e2
Create Date: 2026-04-02 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260402_1200"
down_revision = "78a065a7c3e2"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    if not _has_column("financial_borderos", "name"):
        op.add_column(
            "financial_borderos",
            sa.Column("name", sa.String(length=160), nullable=True),
        )

    op.execute("UPDATE financial_borderos SET name = COALESCE(NULLIF(name, ''), description, bordero_code)")
    op.alter_column("financial_borderos", "name", existing_type=sa.String(length=160), nullable=False)


def downgrade():
    if _has_column("financial_borderos", "name"):
        op.drop_column("financial_borderos", "name")
