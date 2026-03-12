"""fix_workflow_gap_fk_set_null

Revision ID: 20260312_1018
Revises: 20260310_1945
Create Date: 2026-03-12 10:18:00.000000

Descrição:
    Ajusta as FKs de workflow_gap_candidates para ON DELETE SET NULL,
    preservando o histórico de gaps quando projeto/atividade são removidos.
"""

from alembic import op
import sqlalchemy as sa


revision = '20260312_1018'
down_revision = '20260310_1945'
branch_labels = None
depends_on = None


def _fk_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return any(fk.get('name') == constraint_name for fk in inspector.get_foreign_keys(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('workflow_gap_candidates'):
        return

    task_fk = 'workflow_gap_candidates_app_task_id_fkey'
    project_fk = 'workflow_gap_candidates_app_project_id_fkey'

    if _fk_exists(inspector, 'workflow_gap_candidates', task_fk):
        op.drop_constraint(task_fk, 'workflow_gap_candidates', type_='foreignkey')
    if _fk_exists(inspector, 'workflow_gap_candidates', project_fk):
        op.drop_constraint(project_fk, 'workflow_gap_candidates', type_='foreignkey')

    op.create_foreign_key(
        task_fk,
        'workflow_gap_candidates',
        'project_tasks',
        ['app_task_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        project_fk,
        'workflow_gap_candidates',
        'projects',
        ['app_project_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('workflow_gap_candidates'):
        return

    task_fk = 'workflow_gap_candidates_app_task_id_fkey'
    project_fk = 'workflow_gap_candidates_app_project_id_fkey'

    if _fk_exists(inspector, 'workflow_gap_candidates', task_fk):
        op.drop_constraint(task_fk, 'workflow_gap_candidates', type_='foreignkey')
    if _fk_exists(inspector, 'workflow_gap_candidates', project_fk):
        op.drop_constraint(project_fk, 'workflow_gap_candidates', type_='foreignkey')

    op.create_foreign_key(
        task_fk,
        'workflow_gap_candidates',
        'project_tasks',
        ['app_task_id'],
        ['id'],
    )
    op.create_foreign_key(
        project_fk,
        'workflow_gap_candidates',
        'projects',
        ['app_project_id'],
        ['id'],
    )
