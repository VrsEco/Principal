"""add block to work calendar events

Revision ID: 20260504_1700
Revises: 20260504_1030
Create Date: 2026-05-04 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260504_1700"
down_revision = "20260504_1030"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_column(inspector, "work_calendar_events", "block_id"):
        op.add_column(
            "work_calendar_events",
            sa.Column("block_id", sa.Integer(), sa.ForeignKey("work_journey_blocks.id", ondelete="SET NULL"), nullable=True),
        )

    inspector = inspect(bind)
    if not _has_index(inspector, "work_calendar_events", "ix_work_calendar_events_block_id"):
        op.create_index("ix_work_calendar_events_block_id", "work_calendar_events", ["block_id"])
    if not _has_index(inspector, "work_calendar_events", "ix_work_calendar_events_company_block_date"):
        op.create_index(
            "ix_work_calendar_events_company_block_date",
            "work_calendar_events",
            ["company_id", "block_id", "event_date"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_index(inspector, "work_calendar_events", "ix_work_calendar_events_company_block_date"):
        op.drop_index("ix_work_calendar_events_company_block_date", table_name="work_calendar_events")
    if _has_index(inspector, "work_calendar_events", "ix_work_calendar_events_block_id"):
        op.drop_index("ix_work_calendar_events_block_id", table_name="work_calendar_events")
    inspector = inspect(bind)
    if _has_column(inspector, "work_calendar_events", "block_id"):
        op.drop_column("work_calendar_events", "block_id")
