"""Evidências de qualificação do colaborador, sem avaliação automática de aderência."""
from alembic import op
import sqlalchemy as sa

revision = '20260904_1800'
down_revision = '20260904_1600'  # RACI fica deliberadamente fora desta linha de produto.
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'employee_qualification_evidences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('qualification_name', sa.String(255), nullable=False),
        sa.Column('level', sa.String(80)),
        sa.Column('evidence_source', sa.String(30), nullable=False, server_default='declared'),
        sa.Column('evidence_reference', sa.String(500)),
        sa.Column('expires_on', sa.Date()),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id', 'employee_id'], ['employees.company_id', 'employees.id'], name='fk_qualification_tenant_employee'),
        sa.CheckConstraint("evidence_source IN ('declared', 'documented', 'verified')", name='ck_qualification_source'),
        sa.UniqueConstraint('company_id', 'employee_id', 'qualification_name', 'level', name='uq_employee_qualification'),
    )
    op.create_index('ix_qualification_company_employee', 'employee_qualification_evidences', ['company_id', 'employee_id'])


def downgrade():
    op.drop_table('employee_qualification_evidences')
