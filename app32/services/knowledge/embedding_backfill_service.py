from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from sqlalchemy import and_, delete, exists, select, text

from models import db
from models.knowledge import KnowledgeChunk, KnowledgeSource
from services.knowledge.embedding_usage import (
    EmbeddingUsage,
    estimate_tokens,
    record_embedding_usage,
)
from services.knowledge.repository import KnowledgeRepository
from services.knowledge.retrieval_strategy import EMBEDDINGS_TABLE, EmbeddingSpec
from services.knowledge.vector_retrieval import embeddings

logger = logging.getLogger(__name__)

# Enquanto a decisão de privacidade/contrato não for tomada, só conteúdo não confidencial
# do produto pode ser enviado ao provedor. Dado de empresa NÃO é indexável por este job.
ALLOWED_SOURCE_TYPES = ("product_help",)
DEFAULT_MAX_CHUNKS = 50
HARD_MAX_CHUNKS = 500
BATCH_SIZE = 32

BatchEmbedder = Callable[[Sequence[str]], tuple[list[list[float]], int, bool]]
RowWriter = Callable[[list[dict[str, Any]]], None]


class BackfillRefused(ValueError):
    """Pedido fora da política do backfill (fail closed)."""


@dataclass(frozen=True)
class BackfillReport:
    dry_run: bool
    pending_chunks: int
    embedded_chunks: int
    estimated_tokens: int
    tokens: int
    run_id: int | None
    stale_removed: int = 0


def _pending_query(spec: EmbeddingSpec, source_types: tuple[str, ...]):
    current = and_(
        embeddings.c.knowledge_chunk_id == KnowledgeChunk.id,
        embeddings.c.embedding_model == spec.model,
        embeddings.c.embedding_version == spec.version,
        embeddings.c.index_generation == spec.index_generation,
        embeddings.c.chunk_checksum == KnowledgeChunk.content_checksum,
    )
    return (
        select(KnowledgeSource, KnowledgeChunk)
        .join(KnowledgeChunk, KnowledgeChunk.knowledge_source_id == KnowledgeSource.id)
        .where(
            KnowledgeSource.knowledge_scope == "product",
            KnowledgeSource.company_id.is_(None),
            KnowledgeChunk.knowledge_scope == "product",
            KnowledgeChunk.company_id.is_(None),
            KnowledgeSource.source_type.in_(source_types),
            KnowledgeSource.deleted_at.is_(None),
            KnowledgeSource.status.in_(("active", "published")),
            ~exists(select(embeddings.c.knowledge_chunk_id).where(current)),
        )
        .order_by(KnowledgeChunk.id)
    )


def _postgres_writer(rows: list[dict[str, Any]]) -> None:
    if db.session.get_bind().dialect.name != "postgresql":
        raise BackfillRefused("Gravação vetorial exige PostgreSQL com pgvector.")
    statement = text(
        f"INSERT INTO {EMBEDDINGS_TABLE} (knowledge_chunk_id, knowledge_source_id, company_id, "
        "knowledge_scope, source_type, chunk_checksum, embedding_model, embedding_version, "
        "index_generation, embedding) VALUES (:knowledge_chunk_id, :knowledge_source_id, NULL, "
        "'product', :source_type, :chunk_checksum, :embedding_model, :embedding_version, "
        "CAST(:index_generation AS INTEGER), CAST(:embedding AS vector))"
    )
    db.session.execute(statement, rows)


class EmbeddingBackfillService:
    """Backfill MANUAL e limitado da projeção vetorial (nunca agendado, nunca em massa).

    Padrão: `dry_run=True` (não chama o provedor; só conta e estima). Só executa com
    `dry_run=False`, provedor injetado e limite de chunks; registra tudo no ledger
    (`knowledge_index_runs`) e no consumo por data/hora.
    """

    def __init__(
        self,
        *,
        embedder: BatchEmbedder | None = None,
        writer: RowWriter | None = None,
        repository: KnowledgeRepository | None = None,
    ) -> None:
        self._embedder = embedder
        self._writer = writer or _postgres_writer
        self._repository = repository or KnowledgeRepository()

    def run(
        self,
        spec: EmbeddingSpec,
        *,
        source_types: Sequence[str] = ALLOWED_SOURCE_TYPES,
        max_chunks: int = DEFAULT_MAX_CHUNKS,
        dry_run: bool = True,
    ) -> BackfillReport:
        types = tuple(dict.fromkeys(str(t).strip().lower() for t in source_types))
        if not types or not set(types) <= set(ALLOWED_SOURCE_TYPES):
            raise BackfillRefused(
                f"Fonte fora da política do backfill; permitido: {list(ALLOWED_SOURCE_TYPES)}."
            )
        if not 1 <= int(max_chunks) <= HARD_MAX_CHUNKS:
            raise BackfillRefused(f"max_chunks deve estar entre 1 e {HARD_MAX_CHUNKS}.")

        pending = [
            (source, chunk)
            for source, chunk in db.session.execute(_pending_query(spec, types)).all()
        ]
        pending_total = len(pending)
        batch = pending[: int(max_chunks)]
        estimated = sum(estimate_tokens(chunk.content) for _, chunk in batch)
        if dry_run:
            return BackfillReport(True, pending_total, 0, estimated, 0, None)
        if self._embedder is None:
            raise BackfillRefused("Execução real exige um provedor de embeddings explícito.")
        if not batch:
            return BackfillReport(False, 0, 0, 0, 0, None)

        run = self._repository.start_run(
            knowledge_scope="product",
            source_type=types[0],
            company_id=None,
            trigger_kind="manual_embedding_backfill",
            metadata={
                "embedding_model": spec.model,
                "embedding_version": spec.version,
                "index_generation": spec.index_generation,
                "max_chunks": int(max_chunks),
            },
        )
        usage = EmbeddingUsage()
        embedded = stale_removed = 0
        try:
            for start in range(0, len(batch), BATCH_SIZE):
                part = batch[start : start + BATCH_SIZE]
                vectors, tokens, was_estimated = self._embedder([chunk.content for _, chunk in part])
                usage.add(tokens, estimated=was_estimated)
                # Substitui a linha obsoleta da mesma geração (checksum antigo), se houver.
                chunk_ids = [chunk.id for _, chunk in part]
                stale_removed += db.session.execute(
                    delete(embeddings).where(
                        embeddings.c.knowledge_chunk_id.in_(chunk_ids),
                        embeddings.c.embedding_model == spec.model,
                        embeddings.c.embedding_version == spec.version,
                        embeddings.c.index_generation == spec.index_generation,
                    )
                ).rowcount or 0
                self._writer(
                    [
                        {
                            "knowledge_chunk_id": chunk.id,
                            "knowledge_source_id": source.id,
                            "source_type": source.source_type,
                            "chunk_checksum": chunk.content_checksum,
                            "embedding_model": spec.model,
                            "embedding_version": spec.version,
                            "index_generation": spec.index_generation,
                            "embedding": "[" + ",".join(repr(float(v)) for v in vector) + "]",
                        }
                        for (source, chunk), vector in zip(part, vectors)
                    ]
                )
                db.session.commit()
                embedded += len(part)
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.exception("knowledge embedding backfill failed run_id=%s", run.id)
            record_embedding_usage(
                run.id, usage, model=spec.model, version=spec.version, index_generation=spec.index_generation
            )
            self._repository.complete_run(
                run.id,
                status="failed",
                counts={"discovered": pending_total, "created": embedded},
                error_message=f"{type(exc).__name__} (detalhe no log do servidor)",
            )
            raise
        record_embedding_usage(
            run.id, usage, model=spec.model, version=spec.version, index_generation=spec.index_generation
        )
        self._repository.complete_run(
            run.id, status="completed", counts={"discovered": pending_total, "created": embedded}
        )
        return BackfillReport(False, pending_total, embedded, estimated, usage.tokens, run.id, stale_removed)


__all__ = ["ALLOWED_SOURCE_TYPES", "BackfillRefused", "BackfillReport", "EmbeddingBackfillService"]
