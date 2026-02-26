"""create_company_projects_view_fallback

Revision ID: 20260225_1000
Revises: 20260205_2000
Create Date: 2026-02-25 20:30:00

Description:
    Garante que a VIEW 'company_projects' exista no banco de dados.

    Contexto: O service my_work_service.py usa SQL direto referenciando
    'company_projects'. Em producao, essa tabela existe como tabela legada.
    Em bancos locais/novos, pode nao existir.

    Esta migration cria uma VIEW company_projects somente se a tabela
    nao existir, espelhando a tabela 'projects' com o schema esperado
    pelo service.

    Em producao onde a tabela real existe, a migration nao faz nada.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "20260225_1000"
down_revision = "20260205_2000"
branch_labels = None
depends_on = None

# SQL da VIEW que espelha projects -> company_projects (schema legado)
VIEW_SQL = """
CREATE OR REPLACE VIEW company_projects AS
SELECT
    p.id,
    p.company_id,
    p.plan_id,
    p.title                               AS title,
    p.notes                               AS description,
    COALESCE(p.status, 'planned')         AS status,
    COALESCE(p.priority, 'normal')        AS priority,
    NULL::integer                         AS responsible_id,
    NULL::integer                         AS executor_id,
    NULL::date                            AS start_date,
    p.deadline                            AS end_date,
    NULL::numeric                         AS estimated_hours,
    0::numeric                            AS worked_hours,
    p.created_at,
    p.updated_at,
    NULL::text                            AS code,
    NULL::integer                         AS code_sequence,
    NULL::text                            AS plan_type,
    FALSE::boolean                        AS is_archived,
    NULL::text                            AS okr_area_ref,
    NULL::text                            AS okr_reference,
    NULL::text                            AS indicator_reference,
    NULL::text                            AS activities
FROM projects p
"""

CHECK_TABLE_SQL = """
SELECT 1
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'company_projects'
  AND table_type = 'BASE TABLE'
"""


def upgrade():
    """
    Cria VIEW company_projects somente se a tabela real nao existir.
    Em producao onde a tabela existe, nao faz nada.
    """
    conn = op.get_bind()

    result = conn.execute(sa.text(CHECK_TABLE_SQL))
    table_exists = result.fetchone() is not None

    if table_exists:
        print("\n" + "=" * 60)
        print("INFO: Tabela 'company_projects' ja existe como tabela real.")
        print("      Nenhuma VIEW sera criada (producao).")
        print("=" * 60 + "\n")
        return

    conn.execute(sa.text(VIEW_SQL))

    print("\n" + "=" * 60)
    print("OK: VIEW 'company_projects' criada com sucesso!")
    print("    Espelha a tabela 'projects' com schema legado.")
    print("=" * 60 + "\n")


def downgrade():
    """Remove a VIEW se ela existir como VIEW (nao remove tabela real)."""
    conn = op.get_bind()

    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='company_projects' AND table_type='VIEW'"
    ))
    is_view = result.fetchone() is not None

    if is_view:
        conn.execute(sa.text("DROP VIEW IF EXISTS company_projects"))
        print("\nOK: VIEW company_projects removida.\n")
    else:
        print("\nINFO: company_projects nao e VIEW, downgrade ignorado.\n")
