"""Merge published identity and audit migration branches without changing data.

Revision ID: 20260923_1200
Revises: 20260922_1100, 20260917_1000

The production snapshot preserves 20260919_0001 -> 20260916_1000.
Do not rewrite that deployed ancestry to hide the separate audit head.
"""

revision = "20260923_1200"
down_revision = ("20260922_1100", "20260917_1000")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
