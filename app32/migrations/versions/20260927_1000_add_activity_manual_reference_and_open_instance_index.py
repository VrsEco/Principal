"""add activity manual reference json and open/overdue instance index

Revision ID: 20260927_1000
Revises: 20260924_1500
Create Date: 2026-09-27 10:00:00

Contexto (handoff_squad_cliente_2026-09-27_expansao_mcp_versus_manual_ia.md):
- Aprovacao de Fabiano Diretor (2026-09-27): adicionar manual_reference_json em
  process_activity_execution_contracts (referencia a feature_catalog/domain_playbook,
  sem backfill -- default '{}' autopreenche) e um indice composto em
  process_instances (company_id, status, due_date) para listar instancias
  abertas/atrasadas sem full scan.
- Decisao explicita de Fabiano: o indice deve ser criado com CONCURRENTLY, por
  seguranca, mesmo divergindo do padrao atual do repo (migracoes anteriores nao
  usam CONCURRENTLY), pois o tamanho real de process_instances em producao nao
  foi medido. CREATE/DROP INDEX CONCURRENTLY nao podem rodar dentro de uma
  transacao -- por isso este arquivo usa `op.get_context().autocommit_block()`
  (mecanismo nativo do Alembic para DDL que exige AUTOCOMMIT no Postgres) em vez
  do wrap transacional padrao usado pelas demais migracoes deste repositorio.
"""
from alembic import op


revision = "20260927_1000"
down_revision = "20260924_1500"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TABLE simples: roda normalmente dentro da transacao da migracao.
    op.execute(
        """
        ALTER TABLE public.process_activity_execution_contracts
            ADD COLUMN IF NOT EXISTS manual_reference_json JSONB NOT NULL DEFAULT '{}'::jsonb;
        """
    )

    # CREATE INDEX CONCURRENTLY exige execucao fora de bloco transacional.
    # autocommit_block() fecha a transacao corrente e roda em modo AUTOCOMMIT.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_process_instances_open_overdue
                ON public.process_instances (company_id, status, due_date);
            """
        )


def downgrade():
    # DROP INDEX CONCURRENTLY tambem exige execucao fora de bloco transacional.
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS public.ix_process_instances_open_overdue;
            """
        )

    op.execute(
        """
        ALTER TABLE public.process_activity_execution_contracts
            DROP COLUMN IF EXISTS manual_reference_json;
        """
    )
