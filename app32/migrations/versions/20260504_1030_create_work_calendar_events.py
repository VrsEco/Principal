"""create work calendar events

Revision ID: 20260504_1030
Revises: 20260501_2245
Create Date: 2026-05-04 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260504_1030"
down_revision = "20260501_2245"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _create_index_if_missing(inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        return
    op.create_index(index_name, table_name, columns)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "work_calendar_events"):
        op.create_table(
            "work_calendar_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("source_type", sa.String(length=40), nullable=False, server_default="manual"),
            sa.Column("source_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=True),
            sa.Column("end_time", sa.Time(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="planned"),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
            sa.Column("execution_notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )

    inspector = inspect(bind)
    _create_index_if_missing(inspector, "work_calendar_events", "ix_work_calendar_events_company_id", ["company_id"])
    _create_index_if_missing(inspector, "work_calendar_events", "ix_work_calendar_events_employee_id", ["employee_id"])
    _create_index_if_missing(inspector, "work_calendar_events", "ix_work_calendar_events_event_date", ["event_date"])
    _create_index_if_missing(inspector, "work_calendar_events", "ix_work_calendar_events_source_type", ["source_type"])
    _create_index_if_missing(inspector, "work_calendar_events", "ix_work_calendar_events_source_id", ["source_id"])
    _create_index_if_missing(
        inspector,
        "work_calendar_events",
        "ix_work_calendar_events_company_employee_date",
        ["company_id", "employee_id", "event_date"],
    )
    _create_index_if_missing(
        inspector,
        "work_calendar_events",
        "ix_work_calendar_events_company_source",
        ["company_id", "source_type", "source_id"],
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "work_calendar_events"):
        op.drop_table("work_calendar_events")
