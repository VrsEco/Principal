"""add company performance settings table

Revision ID: 20251201_2100
Revises: 20251201_1900
Create Date: 2025-12-01 21:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251201_2100"
down_revision = "20251201_1900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_performance_settings",
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("on_time_score", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("late_score", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "daily_delay_penalty", sa.Numeric(10, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "late_registration_penalty",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="-1",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id"),
    )


def downgrade():
    op.drop_table("company_performance_settings")
