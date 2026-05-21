"""add video narration to process steps

Revision ID: 20260520_1700
Revises: 20260520_1500
Create Date: 2026-05-20 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_1700"
down_revision = "20260520_1500"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("process_steps")}

    if "video_narration" not in columns:
        op.add_column("process_steps", sa.Column("video_narration", sa.Text(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("process_steps")}

    if "video_narration" in columns:
        op.drop_column("process_steps", "video_narration")
