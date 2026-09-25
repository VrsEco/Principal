"""Projeção vetorial pgvector para o conhecimento corporativo (desligada por padrão).

Cria somente ``knowledge_chunk_embeddings``: uma projeção derivada e descartável.
``knowledge_sources`` e ``knowledge_chunks`` (fonte soberana: company_id, grants,
status, vigência, origem e checksum) não são alterados. Nenhum backfill aqui.

Revision ID: 20260924_1400
Revises: 20260924_1300
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_1400"
down_revision = "20260924_1300"
branch_labels = None
depends_on = None

TABLE = "knowledge_chunk_embeddings"
EMBEDDING_DIMENSIONS = 1536  # espelha KNOWLEDGE_EMBEDDING_DIMENSIONS


def _require_pgvector(bind) -> None:
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "A projeção vetorial do conhecimento exige PostgreSQL com a extensão pgvector."
        )
    available = bind.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ).first()
    if available is None:
        raise RuntimeError(
            "Extensão pgvector ('vector') indisponível neste PostgreSQL. Instale o pacote "
            "pgvector no servidor (ex.: postgresql-<versão>-pgvector) e reexecute a "
            "migration; nenhuma tabela foi alterada."
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(TABLE):
        return
    _require_pgvector(bind)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE {TABLE} (
            id SERIAL PRIMARY KEY,
            knowledge_chunk_id INTEGER NOT NULL
                REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
            knowledge_source_id INTEGER NOT NULL
                REFERENCES knowledge_sources(id) ON DELETE CASCADE,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            knowledge_scope VARCHAR(20) NOT NULL,
            source_type VARCHAR(80) NOT NULL,
            chunk_checksum VARCHAR(64) NOT NULL,
            embedding_model VARCHAR(120) NOT NULL,
            embedding_version VARCHAR(40) NOT NULL,
            index_generation INTEGER NOT NULL,
            embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_knowledge_chunk_embeddings_scope_company CHECK (
                (knowledge_scope = 'company' AND company_id IS NOT NULL) OR
                (knowledge_scope = 'product' AND company_id IS NULL)
            ),
            CONSTRAINT uq_knowledge_chunk_embeddings_generation UNIQUE (
                knowledge_chunk_id, embedding_model, embedding_version, index_generation
            )
        )
        """
    )
    op.create_index(
        "ix_knowledge_chunk_embeddings_tenant_generation",
        TABLE,
        ["company_id", "knowledge_scope", "index_generation"],
    )
    op.create_index("ix_knowledge_chunk_embeddings_source", TABLE, ["knowledge_source_id"])
    # Sem índice ANN de propósito: com filtro de tenant, o ANN pós-filtra e perde
    # recall; a busca exata dentro do universo autorizado é a linha de base segura.
    # Um índice HNSW por geração só entra após medição no golden set (piloto).


def downgrade() -> None:
    """Remove apenas a projeção vetorial; a extensão e o conhecimento permanecem."""

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(TABLE):
        op.drop_table(TABLE)
