from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import db
from models.company import Company
from models.knowledge import KnowledgeIndexRun
from services.knowledge.embedding_usage import (
    EmbeddingUsage,
    MeteredEmbeddingProvider,
    estimate_tokens,
    record_embedding_usage,
    summarize_embedding_usage,
)


@pytest.fixture()
def usage_app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[Company.__table__, KnowledgeIndexRun.__table__])
        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        db.session.commit()
        yield app
        db.session.remove()


def _run(company_id, scope="company"):
    run = KnowledgeIndexRun(
        company_id=company_id, knowledge_scope=scope, source_type="process_publication",
        trigger_kind="manual", status="completed", metadata_json={"keep": "me"},
    )
    db.session.add(run)
    db.session.commit()
    return run


def test_metered_provider_counts_estimated_and_reported_tokens_without_storing_text():
    provider = MeteredEmbeddingProvider(lambda text: [0.0, 1.0])
    provider("a" * 40)
    assert provider.usage == EmbeddingUsage(requests=1, tokens=10, estimated=True)
    reported = MeteredEmbeddingProvider(lambda t: [0.0], tokens_of=lambda t: 7)
    reported("qualquer")
    assert reported.usage.tokens == 7 and reported.usage.estimated is False
    assert "a" * 40 not in repr(provider.usage)
    assert estimate_tokens("") == 1


def test_record_accumulates_per_run_and_preserves_existing_metadata(usage_app):
    run = _run(1)
    record_embedding_usage(run.id, EmbeddingUsage(2, 100, False), model="m", version="v1", index_generation=1)
    record_embedding_usage(run.id, EmbeddingUsage(1, 50, True), model="m", version="v1", index_generation=1)
    stored = db.session.get(KnowledgeIndexRun, run.id).metadata_json
    assert stored["keep"] == "me"
    assert stored["embedding_usage"] == {
        "model": "m", "version": "v1", "index_generation": 1,
        "requests": 3, "tokens": 150, "estimated": True,
    }
    with pytest.raises(RuntimeError):
        record_embedding_usage(9999, EmbeddingUsage(), model="m", version="v1", index_generation=1)


def test_summary_is_per_company_isolated_and_cost_only_with_configured_price(usage_app, monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD", raising=False)
    for company, tokens in ((1, 3_000_000), (2, 500_000), (None, 200_000)):
        run = _run(company, scope="company" if company else "product")
        record_embedding_usage(run.id, EmbeddingUsage(10, tokens, False), model="m", version="v1", index_generation=1)
    _run(1)  # execução sem consumo é ignorada

    rows = {r["company_id"]: r for r in summarize_embedding_usage()}
    assert rows[1]["tokens"] == 3_000_000 and rows[1]["runs"] == 1
    assert rows[None]["tokens"] == 200_000
    assert all(r["estimated_cost_usd"] is None for r in rows.values())

    only_two = summarize_embedding_usage(company_id=2)
    assert [r["company_id"] for r in only_two] == [2]

    priced = {r["company_id"]: r for r in summarize_embedding_usage(price_per_million_usd=0.5)}
    assert priced[1]["estimated_cost_usd"] == 1.5

    monkeypatch.setenv("KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD", "abc")
    assert summarize_embedding_usage()[0]["estimated_cost_usd"] is None
    assert summarize_embedding_usage(since=datetime.utcnow() + timedelta(days=1)) == []


def _spec():
    from services.knowledge import retrieval_strategy as rs

    return rs.EmbeddingSpec("m", "v1", 1, dimensions=2)


def test_events_are_timestamped_without_text_and_filterable(usage_app):
    from models.knowledge import KnowledgeEmbeddingUsageEvent
    from services.knowledge.embedding_usage import query_usage_events, record_usage_event

    db.metadata.create_all(bind=db.engine, tables=[KnowledgeEmbeddingUsageEvent.__table__])
    t1, t2 = datetime(2026, 9, 24, 10, 30), datetime(2026, 9, 25, 8, 0)
    kwargs = dict(model="m", version="v1", index_generation=1, estimated=True)
    assert record_usage_event(kind="query", company_id=1, user_id=5, tokens=20, occurred_at=t1, **kwargs)
    assert record_usage_event(kind="query", company_id=1, user_id=6, tokens=30, occurred_at=t1, **kwargs)
    assert record_usage_event(kind="query", company_id=2, user_id=7, tokens=99, occurred_at=t2, **kwargs)
    assert record_usage_event(kind="index", company_id=1, user_id=None, tokens=1000, occurred_at=t2, **kwargs)
    with pytest.raises(ValueError):
        record_usage_event(kind="x", company_id=1, user_id=None, tokens=1, **kwargs)

    company_one = query_usage_events(company_id=1, kind="query", price_per_million_usd=1.0)
    assert len(company_one) == 1
    assert company_one[0]["tokens"] == 50 and company_one[0]["requests"] == 2
    assert company_one[0]["day"] == "2026-09-24" and company_one[0]["first_at"].startswith("2026-09-24T10:30")
    assert company_one[0]["estimated_cost_usd"] == 0.00005
    day_two = query_usage_events(since=datetime(2026, 9, 25), until=datetime(2026, 9, 26))
    assert {(r["company_id"], r["kind"]) for r in day_two} == {(2, "query"), (1, "index")}
    assert not hasattr(KnowledgeEmbeddingUsageEvent, "question")


def test_measurement_failure_never_breaks_the_caller(usage_app):
    from services.knowledge.embedding_usage import record_usage_event

    # tabela de eventos inexistente neste banco: retorna False em vez de levantar
    assert record_usage_event(
        kind="query", company_id=1, user_id=1, model="m", version="v", index_generation=1,
        tokens=1, estimated=True,
    ) is False


def test_hybrid_query_records_one_event_per_embedding_call(usage_app):
    from models.knowledge import (
        KnowledgeChunk,
        KnowledgeEmbeddingUsageEvent,
        KnowledgeSource,
        KnowledgeSourceGrant,
    )
    from services.knowledge import retrieval_strategy as rs
    from services.knowledge.embedding_usage import MeteredEmbeddingProvider
    from services.knowledge.query_service import KnowledgeQueryService

    db.metadata.create_all(
        bind=db.engine,
        tables=[
            KnowledgeSource.__table__,
            KnowledgeSourceGrant.__table__,
            KnowledgeChunk.__table__,
            KnowledgeEmbeddingUsageEvent.__table__,
        ],
    )
    provider = MeteredEmbeddingProvider(lambda q: [0.1, 0.2], tokens_of=lambda q: 12)
    service = KnowledgeQueryService(
        embedding_provider=provider,
        vector_config=rs.VectorRetrievalConfig(enabled=True, embedding=_spec()),
        vector_fetcher=lambda *a, **k: [],
    )
    result = service.search("pergunta sobre reembolso", company_id=1, user_id=9, strategy="hybrid")

    events = db.session.query(KnowledgeEmbeddingUsageEvent).all()
    assert len(events) == 1
    event = events[0]
    assert (event.kind, event.company_id, event.user_id, event.tokens, event.estimated) == (
        "query", 1, 9, 12, False,
    )
    assert event.occurred_at is not None
    assert "reembolso" not in repr(result["warnings"])
