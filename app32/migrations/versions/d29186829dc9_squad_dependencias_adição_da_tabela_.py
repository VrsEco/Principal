"""SQUAD: [DEPENDENCIAS] Adição da tabela project_task_dependencies

Revision ID: d29186829dc9
Revises: 6c9b3e8f4a21
Create Date: 2026-03-07 15:17:58.162857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd29186829dc9'
down_revision = '6c9b3e8f4a21'
branch_labels = None
depends_on = None


TABLE_NAME = 'project_task_dependencies'
INDEX_DEFINITIONS = {
    'idx_task_dep_company': ['company_id'],
    'idx_task_dep_predecessor': ['predecessor_task_id'],
    'idx_task_dep_project': ['project_id'],
    'idx_task_dep_successor': ['successor_task_id'],
}


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get('name') == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('predecessor_task_id', sa.Integer(), nullable=False, comment='Atividade que deve ser concluída primeiro'),
            sa.Column('successor_task_id', sa.Integer(), nullable=False, comment='Atividade que depende da predecessora'),
            sa.Column('dependency_type', sa.String(length=30), nullable=True, server_default='finish_to_start'),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('created_by_employee_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
            sa.ForeignKeyConstraint(['created_by_employee_id'], ['employees.id']),
            sa.ForeignKeyConstraint(['predecessor_task_id'], ['project_tasks.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.ForeignKeyConstraint(['successor_task_id'], ['project_tasks.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('predecessor_task_id', 'successor_task_id', name='uq_task_dependency'),
            comment='Dependências finish_to_start entre atividades do mesmo projeto',
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEX_DEFINITIONS.items():
        if not _index_exists(inspector, TABLE_NAME, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
