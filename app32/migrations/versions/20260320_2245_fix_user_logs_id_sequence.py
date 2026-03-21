"""repair user_logs id default sequence

Revision ID: 20260320_2245
Revises: 20260320_1200
Create Date: 2026-03-20 22:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_2245"
down_revision = "20260320_1200"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            CREATE SEQUENCE IF NOT EXISTS public.user_logs_id_seq
            """
        )
    )

    bind.execute(
        sa.text(
            """
            ALTER TABLE public.user_logs
            ALTER COLUMN id SET DEFAULT nextval('public.user_logs_id_seq')
            """
        )
    )

    bind.execute(
        sa.text(
            """
            SELECT setval(
                'public.user_logs_id_seq',
                COALESCE((SELECT MAX(id) FROM public.user_logs), 0) + 1,
                false
            )
            """
        )
    )


def downgrade():
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            ALTER TABLE public.user_logs
            ALTER COLUMN id DROP DEFAULT
            """
        )
    )

    bind.execute(
        sa.text(
            """
            DROP SEQUENCE IF EXISTS public.user_logs_id_seq
            """
        )
    )
