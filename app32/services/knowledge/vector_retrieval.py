from __future__ import annotations

import math
from datetime import datetime
from typing import Sequence

from sqlalchemy import Float, Integer, String, cast, column, literal, select, table
from sqlalchemy.types import UserDefinedType

from models.knowledge import KnowledgeChunk, KnowledgeSource
from services.knowledge.query_service import (
    KnowledgeQueryError,
    KnowledgeQueryPlan,
    authorized_universe_conditions,
)
from services.knowledge.retrieval_strategy import EMBEDDINGS_TABLE, EmbeddingSpec


class _Vector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_kw) -> str:
        return "vector"


embeddings = table(
    EMBEDDINGS_TABLE,
    column("knowledge_chunk_id", Integer),
    column("knowledge_source_id", Integer),
    column("company_id", Integer),
    column("knowledge_scope", String),
    column("chunk_checksum", String),
    column("embedding_model", String),
    column("embedding_version", String),
    column("index_generation", Integer),
    column("embedding", _Vector),
)


def format_query_embedding(values: Sequence[float], spec: EmbeddingSpec) -> str:
    """Valida dimensão/finitude (falha fechada) e serializa no formato pgvector."""

    if len(values) != spec.dimensions:
        raise KnowledgeQueryError("Embedding da consulta com dimensão incompatível.")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise KnowledgeQueryError("Embedding da consulta contém valores inválidos.")
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


def build_vector_candidates_statement(
    plan: KnowledgeQueryPlan,
    spec: EmbeddingSpec,
    query_embedding: Sequence[float],
    *,
    user_id: int | None,
    employee_id: int | None,
    now: datetime,
):
    """SELECT (source, chunk, similaridade) cosseno restrito ao universo autorizado.

    A ordenação por distância só existe *depois* de aplicados os mesmos filtros do
    FTS (``authorized_universe_conditions``); o vetor nunca amplia o conjunto.
    Embeddings de outra geração/modelo, com checksum divergente do chunk (stale) ou
    com tenant/escopo divergente da fonte soberana são descartados.
    """

    vector_literal = cast(literal(format_query_embedding(query_embedding, spec), type_=String()), _Vector)
    distance = embeddings.c.embedding.op("<=>", return_type=Float)(vector_literal)
    similarity = (1 - distance).label("vector_similarity")
    return (
        select(KnowledgeSource, KnowledgeChunk, similarity)
        .join(KnowledgeChunk, KnowledgeChunk.knowledge_source_id == KnowledgeSource.id)
        .join(embeddings, embeddings.c.knowledge_chunk_id == KnowledgeChunk.id)
        .where(
            *authorized_universe_conditions(
                plan, user_id=user_id, employee_id=employee_id, now=now
            ),
            embeddings.c.knowledge_source_id == KnowledgeSource.id,
            embeddings.c.knowledge_scope == KnowledgeSource.knowledge_scope,
            embeddings.c.chunk_checksum == KnowledgeChunk.content_checksum,
            embeddings.c.embedding_model == spec.model,
            embeddings.c.embedding_version == spec.version,
            embeddings.c.index_generation == spec.index_generation,
            (embeddings.c.company_id == KnowledgeSource.company_id)
            | (embeddings.c.company_id.is_(None) & KnowledgeSource.company_id.is_(None)),
        )
        .order_by(distance.asc())
        .limit(plan.candidate_limit)
    )


__all__ = ["build_vector_candidates_statement", "embeddings", "format_query_embedding"]
