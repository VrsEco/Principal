"""add video metadata to process steps

Revision ID: 20260520_1500
Revises: 20260519_1200
Create Date: 2026-05-20 15:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_1500"
down_revision = "20260519_1200"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("process_steps")}

    if "video_path" not in columns:
        op.add_column("process_steps", sa.Column("video_path", sa.String(length=255), nullable=True))
    if "video_duration_seconds" not in columns:
        op.add_column("process_steps", sa.Column("video_duration_seconds", sa.Integer(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("process_steps")}

    if "video_duration_seconds" in columns:
        op.drop_column("process_steps", "video_duration_seconds")
    if "video_path" in columns:
        op.drop_column("process_steps", "video_path")
