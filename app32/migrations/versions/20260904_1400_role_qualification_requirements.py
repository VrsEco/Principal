"""Requisitos descritivos do cargo, preservando cargos e ocupantes existentes.

Revision ID: 20260904_1400
Revises: 20260903_1300
"""
from alembic import op

revision = "20260904_1400"
down_revision = "20260903_1300"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS qualification_requirements TEXT")


def downgrade():
    # Requer exportação dos requisitos antes do rollback em produção.
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS qualification_requirements")
