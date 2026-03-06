"""add_user_employee_assignments

Revision ID: 02ede27b3c02
Revises: 8b5f24df2b1c
Create Date: 2026-03-06 10:39:40.539940

Observação:
    A tabela já existe em ambientes com schema regularizado por criação manual
    ou `db.create_all()`. Esta migration foi ajustada para ser idempotente.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "02ede27b3c02"
down_revision = "8b5f24df2b1c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.user_employee_assignments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES public.users(id),
            employee_id INTEGER NOT NULL REFERENCES public.employees(id),
            start_date DATE NOT NULL,
            end_date DATE NULL,
            is_active BOOLEAN DEFAULT true,
            status VARCHAR(20) DEFAULT 'active',
            notes TEXT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
        );
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.user_employee_assignments;")
