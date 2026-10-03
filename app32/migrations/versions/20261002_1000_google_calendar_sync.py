"""Conexões OAuth (uma por usuário) e vínculos de eventos do Google Calendar.

Revision ID: 20261002_1000
Revises: 20260923_1200
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20261002_1000"
down_revision = "20260923_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("google_calendar_connections"):
        op.create_table(
            "google_calendar_connections",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("google_email", sa.String(255)),
            sa.Column("refresh_token_enc", sa.Text(), nullable=False),
            sa.Column("access_token_enc", sa.Text()),
            sa.Column("token_expires_at", sa.DateTime()),
            sa.Column("scope", sa.Text()),
            sa.Column("calendar_id", sa.String(255), nullable=False, server_default="primary"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("last_error", sa.String(500)),
            sa.Column("last_synced_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("user_id", name="uq_google_calendar_conn_user"),
        )
    if not inspector.has_table("google_calendar_event_links"):
        op.create_table(
            "google_calendar_event_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "connection_id",
                sa.Integer(),
                sa.ForeignKey("google_calendar_connections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("google_event_id", sa.String(255), nullable=False),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("last_synced_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("connection_id", "source_type", "source_id", name="uq_google_calendar_link_source"),
        )
        op.create_index(
            "ix_google_calendar_links_company_date", "google_calendar_event_links", ["company_id", "event_date"]
        )


def downgrade() -> None:
    op.drop_table("google_calendar_event_links")
    op.drop_table("google_calendar_connections")
