from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import db
from models.company import Company
from models.knowledge import (
    KnowledgeChunk,
    KnowledgeEmbeddingUsageEvent,
    KnowledgeIndexRun,
    KnowledgeSource,
    KnowledgeSourceGrant,
)
from services.knowledge.embedding_backfill_service import (
    BackfillRefused,
    EmbeddingBackfillService,
)
from services.knowledge.openai_embedding_provider import OpenAIEmbeddingProvider
from services.knowledge.retrieval_strategy import EmbeddingSpec

SPEC = EmbeddingSpec("text-embedding-3-small", "v1", 1, dimensions=1536)


@pytest.fixture()
def backfill_app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                Company.__table__,
                KnowledgeSource.__table__,
                KnowledgeSourceGrant.__table__,
                KnowledgeChunk.__table__,
                KnowledgeIndexRun.__table__,
                KnowledgeEmbeddingUsageEvent.__table__,
            ],
        )
        # projeção simulada em SQLite (o tipo vector só existe no PostgreSQL)
        db.session.execute(
            text(
                "CREATE TABLE knowledge_chunk_embeddings (id INTEGER PRIMARY KEY, "
                "knowledge_chunk_id INT, knowledge_source_id INT, company_id INT, "
                "knowledge_scope TEXT, source_type TEXT, chunk_checksum TEXT, "
                "embedding_model TEXT, embedding_version TEXT, index_generation INT, "
                "embedding TEXT)"
            )
        )
        db.session.add_all([Company(id=1, name="A")])
        for ref, content in (("m1", "Como publicar um processo."), ("m2", "Como abrir títulos.")):
            source = KnowledgeSource(
                knowledge_scope="product",
                company_id=None,
                source_type="product_help",
                source_ref=ref,
                knowledge_kind="product_help",
                title=ref,
                canonical_uri=f"app-versus://help/{ref}",
                status="published",
                authority_level="official",
                version="v1",
                content_checksum=ref * 32,
            )
            source.chunks.append(
                KnowledgeChunk(
                    knowledge_scope="product",
                    company_id=None,
                    section_key="s",
                    content=content,
                    content_checksum=(ref + "c") * 16,
                )
            )
            db.session.add(source)
        company_source = KnowledgeSource(
            knowledge_scope="company",
            company_id=1,
            source_type="process_publication",
            source_ref="pop1",
            knowledge_kind="procedure",
            title="POP",
            canonical_uri="app-versus://pop/1",
            status="published",
            authority_level="internal",
            version="v1",
            content_checksum="p" * 64,
        )
        company_source.chunks.append(
            KnowledgeChunk(
                knowledge_scope="company",
                company_id=1,
                section_key="s",
                content="Segredo da empresa um.",
                content_checksum="q" * 64,
            )
        )
        db.session.add(company_source)
        db.session.commit()
        yield app
        db.session.remove()


def _writer_into_sqlite(rows):
    for row in rows:
        db.session.execute(
            text(
                "INSERT INTO knowledge_chunk_embeddings (knowledge_chunk_id, knowledge_source_id, "
                "company_id, knowledge_scope, source_type, chunk_checksum, embedding_model, "
                "embedding_version, index_generation, embedding) VALUES (:knowledge_chunk_id, "
                ":knowledge_source_id, NULL, 'product', :source_type, :chunk_checksum, "
                ":embedding_model, :embedding_version, :index_generation, :embedding)"
            ),
            row,
        )


def _fake_embedder(calls):
    def embed(texts):
        calls.append(list(texts))
        return [[0.0] * 3 for _ in texts], 10 * len(texts), False

    return embed


def _count_embeddings():
    return db.session.execute(text("SELECT count(*) FROM knowledge_chunk_embeddings")).scalar()


def test_dry_run_is_default_and_never_calls_provider_or_writes(backfill_app):
    calls = []
    report = EmbeddingBackfillService(embedder=_fake_embedder(calls), writer=_writer_into_sqlite).run(SPEC)
    assert report.dry_run and report.pending_chunks == 2 and report.estimated_tokens > 0
    assert calls == [] and db.session.query(KnowledgeIndexRun).count() == 0


def test_company_data_is_refused_and_never_sent(backfill_app):
    service = EmbeddingBackfillService(embedder=_fake_embedder([]), writer=_writer_into_sqlite)
    for types in (("process_publication",), ("product_help", "meeting"), ()):
        with pytest.raises(BackfillRefused):
            service.run(SPEC, source_types=types, dry_run=False)
    calls = []
    EmbeddingBackfillService(embedder=_fake_embedder(calls), writer=_writer_into_sqlite).run(SPEC, dry_run=False)
    assert calls and all("Segredo" not in t for batch in calls for t in batch)


def test_limits_and_missing_provider_fail_closed(backfill_app):
    with pytest.raises(BackfillRefused):
        EmbeddingBackfillService(writer=_writer_into_sqlite).run(SPEC, dry_run=False)
    with pytest.raises(BackfillRefused):
        EmbeddingBackfillService().run(SPEC, max_chunks=0)
    with pytest.raises(BackfillRefused):
        EmbeddingBackfillService().run(SPEC, max_chunks=10_000)


def test_execution_writes_ledger_usage_event_and_is_idempotent(backfill_app):
    calls = []
    service = EmbeddingBackfillService(embedder=_fake_embedder(calls), writer=_writer_into_sqlite)
    report = service.run(SPEC, dry_run=False, max_chunks=1)
    assert (report.embedded_chunks, report.pending_chunks, report.tokens) == (1, 2, 10)

    second = service.run(SPEC, dry_run=False)
    assert second.embedded_chunks == 1 and second.pending_chunks == 1
    third = service.run(SPEC, dry_run=False)
    assert third.embedded_chunks == 0 and third.run_id is None  # nada pendente: sem chamada

    runs = db.session.query(KnowledgeIndexRun).order_by(KnowledgeIndexRun.id).all()
    assert [r.status for r in runs] == ["completed", "completed"]
    assert runs[0].trigger_kind == "manual_embedding_backfill" and runs[0].company_id is None
    assert runs[0].metadata_json["embedding_usage"]["tokens"] == 10
    events = db.session.query(KnowledgeEmbeddingUsageEvent).all()
    assert [(e.kind, e.company_id, e.tokens) for e in events] == [("index", None, 10)] * 2
    assert _count_embeddings() == 2
    assert len(calls) == 2


def test_changed_chunk_checksum_replaces_stale_embedding(backfill_app):
    service = EmbeddingBackfillService(embedder=_fake_embedder([]), writer=_writer_into_sqlite)
    service.run(SPEC, dry_run=False)
    chunk = db.session.query(KnowledgeChunk).filter_by(knowledge_scope="product").first()
    chunk.content_checksum = "z" * 64
    db.session.commit()
    report = service.run(SPEC, dry_run=False)
    assert report.embedded_chunks == 1 and report.stale_removed == 1
    assert _count_embeddings() == 2


def test_provider_failure_marks_run_failed_without_leaking_detail(backfill_app):
    def boom(texts):
        raise RuntimeError("sk-segredo-da-chave")

    service = EmbeddingBackfillService(embedder=boom, writer=_writer_into_sqlite)
    with pytest.raises(RuntimeError):
        service.run(SPEC, dry_run=False)
    run = db.session.query(KnowledgeIndexRun).one()
    assert run.status == "failed" and "sk-segredo" not in (run.error_message or "")
    assert _count_embeddings() == 0


def _fake_client(dim=1536, total_tokens=7):
    def create(model, input):
        data = [SimpleNamespace(index=i, embedding=[0.1] * dim) for i in reversed(range(len(input)))]
        usage = SimpleNamespace(total_tokens=total_tokens) if total_tokens is not None else None
        return SimpleNamespace(data=data, usage=usage)

    return SimpleNamespace(embeddings=SimpleNamespace(create=create))


def test_openai_adapter_uses_reported_usage_and_validates_shape():
    provider = OpenAIEmbeddingProvider(client=_fake_client())
    vector = provider("olá")
    assert len(vector) == 1536 and (provider.last_tokens, provider.last_estimated) == (7, False)
    _, tokens, estimated = OpenAIEmbeddingProvider(client=_fake_client(total_tokens=None)).embed_many(["abcdefgh"])
    assert (tokens, estimated) == (2, True)
    with pytest.raises(RuntimeError):
        OpenAIEmbeddingProvider(client=_fake_client(dim=3)).embed_many(["x"])
    with pytest.raises(ValueError):
        provider.embed_many(["x"] * 65)


def test_provider_never_touches_network_at_construction(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIEmbeddingProvider()  # não deve levantar nem criar cliente
    assert provider._client is None
