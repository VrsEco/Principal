"""Create portfolios table

Revision ID: 20260205_2000_create_portfolios
Revises: 
Create Date: 2026-02-05 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260205_2000_create_portfolios'
down_revision = None  # Update this if there are previous migrations
branch_labels = None
depends_on = None


def upgrade():
    # Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('responsible_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['responsible_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on company_id for faster queries
    op.create_index('ix_portfolios_company_id', 'portfolios', ['company_id'])
    
    # Create unique constraint on company_id + code
    op.create_index('ix_portfolios_company_code', 'portfolios', ['company_id', 'code'], unique=True)

    # Add portfolio_id to projects table
    op.add_column('projects', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_projects_portfolio', 'projects', 'portfolios', ['portfolio_id'], ['id'])
    op.create_index('ix_projects_portfolio_id', 'projects', ['portfolio_id'])


def downgrade():
    op.drop_index('ix_projects_portfolio_id', table_name='projects')
    op.drop_constraint('fk_projects_portfolio', 'projects', type_='foreignkey')
    op.drop_column('projects', 'portfolio_id')
    op.drop_index('ix_portfolios_company_code', table_name='portfolios')
    op.drop_index('ix_portfolios_company_id', table_name='portfolios')
    op.drop_table('portfolios')
