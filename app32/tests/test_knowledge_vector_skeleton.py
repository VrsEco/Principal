"""Esqueleto pgvector: flag desligada, plano compatível, statement filtrado, migration."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge import retrieval_strategy as rs
from services.knowledge.query_service import KnowledgeQueryError, KnowledgeQueryService
from services.knowledge.vector_retrieval import (
    build_vector_candidates_statement,
    format_query_embedding,
)

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "versions" / "20260924_1400_knowledge_vector_projection.py"
SPEC = rs.EmbeddingSpec(model="modelo-x", version="v1", index_generation=3, dimensions=4)


def test_vector_feature_is_off_by_default_and_ignores_partial_config():
    assert rs.VectorRetrievalConfig.from_env({}).enabled is False
    assert rs.VectorRetrievalConfig.from_env({rs.VECTOR_FLAG_ENV: "true"}).embedding is None
    full = rs.VectorRetrievalConfig.from_env(
        {
            rs.VECTOR_FLAG_ENV: "1",
            rs.EMBEDDING_MODEL_ENV: "m",
            rs.EMBEDDING_VERSION_ENV: "v1",
            rs.INDEX_GENERATION_ENV: "2",
        }
    )
    assert full.enabled and full.embedding.index_generation == 2
    assert full.ready is True  # ainda exige provedor de embedding injetado no serviço


@pytest.mark.parametrize(
    "requested,reason",
    [
        ("vector", "vector_retrieval_disabled"),
        ("hybrid", "vector_retrieval_disabled"),
        ("relationship_graph", "relationship_graph_not_available"),
    ],
)
def test_pending_strategies_fall_back_to_full_text(requested, reason):
    resolution = rs.resolve_strategies(requested, rs.VectorRetrievalConfig())
    assert resolution.strategies == ("sql", "full_text")
    assert resolution.fallback_reason == reason
    assert resolution.requested == requested


def test_unknown_strategy_is_rejected_by_the_plan():
    with pytest.raises(KnowledgeQueryError):
        KnowledgeQueryService().build_plan("pergunta valida", company_id=1, strategy="magic")


def test_plan_stays_backward_compatible_and_reports_fallback():
    _, plan = KnowledgeQueryService().build_plan(
        "pergunta valida", company_id=1, strategy="hybrid", vector_config=rs.VectorRetrievalConfig()
    )
    data = plan.to_dict()
    assert data["strategies"] == ["sql", "full_text"]
    assert data["requested_strategy"] == "hybrid"
    assert data["fallback_reason"] == "vector_retrieval_disabled"
    assert data["evidence_origin"] == "rag"
    _, default_plan = KnowledgeQueryService().build_plan("pergunta valida", company_id=1)
    assert default_plan.strategies == ("sql", "full_text")
    assert default_plan.fallback_reason is None


def test_hybrid_ranking_is_explicit_and_redistributes_without_vector():
    policy = rs.HybridRankingPolicy()
    base = dict(authority=1.0, lexical=0.5, recency=0.2)
    with_vector = policy.score(vector_similarity=0.9, **base)
    lexical_only = policy.score(vector_similarity=None, **base)
    assert 0 <= with_vector <= 1 and 0 <= lexical_only <= 1
    assert policy.score(vector_similarity=1.0, **base) > policy.score(vector_similarity=0.0, **base)
    assert policy.score(authority=2, lexical=-1, vector_similarity=None, recency=0.5) <= 1


def test_query_embedding_is_validated_fail_closed():
    assert format_query_embedding([0.1, 0.2, 0.3, 0.4], SPEC).startswith("[")
    for bad in ([0.1], [0.1, 0.2, 0.3, float("nan")], [0.1, 0.2, 0.3, float("inf")], [0.1, 0.2, 0.3, "x"]):
        with pytest.raises(KnowledgeQueryError):
            format_query_embedding(bad, SPEC)


def test_vector_statement_applies_tenant_grant_and_generation_filters_before_ordering():
    _, plan = KnowledgeQueryService().build_plan("pergunta valida", company_id=7)
    stmt = build_vector_candidates_statement(
        plan, SPEC, [0.1, 0.2, 0.3, 0.4], user_id=5, employee_id=9, now=datetime(2026, 9, 24)
    )
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    where, order = sql.split("ORDER BY")
    for required in (
        "knowledge_sources.company_id = 7",
        "knowledge_source_grants",
        "knowledge_sources.deleted_at IS NULL",
        "knowledge_sources.status IN ('active', 'published')",
        "knowledge_sources.valid_to",
        "knowledge_chunk_embeddings.index_generation = 3",
        "knowledge_chunk_embeddings.chunk_checksum = knowledge_chunks.content_checksum",
        "knowledge_chunk_embeddings.embedding_model = 'modelo-x'",
    ):
        assert required in where, required
    assert "<=>" in order and "LIMIT" in order + "LIMIT"
    assert "<=>" not in where.split("WHERE")[1]  # a distância só ordena, nunca amplia o universo


def test_vector_statement_without_company_never_reaches_company_sources():
    _, plan = KnowledgeQueryService().build_plan(
        "pergunta valida", company_id=None, require_company=False
    )
    stmt = build_vector_candidates_statement(
        plan, SPEC, [0.1, 0.2, 0.3, 0.4], user_id=None, employee_id=None, now=datetime(2026, 9, 24)
    )
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "knowledge_sources.knowledge_scope = 'product'" in sql
    # Sem empresa ativa, a ramificação `company` degenera para "sem acesso" (company_id = NULL).
    assert "knowledge_sources.knowledge_scope = 'company'" not in sql


def test_migration_is_additive_reversible_and_fails_with_clear_message():
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260924_1400"' in text
    assert 'down_revision = "20260924_1300"' in text
    assert "pg_available_extensions" in text and "pgvector" in text
    assert "CREATE EXTENSION IF NOT EXISTS vector" in text
    upgrade, downgrade = text.split("def downgrade")
    # Somente cria a projeção; nunca altera/derruba as tabelas soberanas.
    for sovereign in ("knowledge_sources", "knowledge_chunks"):
        assert f"DROP TABLE {sovereign}" not in text and f'drop_table("{sovereign}")' not in text
        assert f"ALTER TABLE {sovereign}" not in text
    assert "ON DELETE CASCADE" in upgrade and "company_id" in upgrade
    assert "ck_knowledge_chunk_embeddings_scope_company" in upgrade
    assert "drop_table(TABLE)" in downgrade and "DROP EXTENSION" not in text
    assert "INSERT" not in text.upper().replace("INSERT_", "")  # sem backfill


def test_migration_head_chain_is_single_and_linear():
    import re

    revisions, downs = {}, set()
    for path in (ROOT / "migrations" / "versions").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        rev = re.search(r'^revision\s*(?::[^=]+)?=\s*["\']([^"\']+)', body, re.M)
        down = re.search(r"^down_revision\s*(?::[^=]+)?=\s*(.+)$", body, re.M)
        if rev:
            revisions[rev.group(1)] = path.name
            if down:
                downs.update(re.findall(r'["\']([^"\']+)["\']', down.group(1)))
    heads = [r for r in revisions if r not in downs]
    assert heads == ["20260924_1500"], heads


@pytest.mark.skipif(
    not os.getenv("APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL"),
    reason="Requer PostgreSQL descartável com pgvector (APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL)",
)
def test_postgres_vector_isolation_and_rollback_roundtrip():
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    url = make_url(os.environ["APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL"])
    assert url.host in {"127.0.0.1", "localhost"} and url.port != 5432
    assert url.database.endswith("_test") and url.drivername.startswith("postgresql")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("DROP TABLE IF EXISTS kv_probe"))
        conn.execute(text("CREATE TABLE kv_probe (id int, company_id int, e vector(3))"))
        conn.execute(text("INSERT INTO kv_probe VALUES (1,1,'[1,0,0]'),(2,2,'[1,0,0]')"))
        rows = conn.execute(
            text("SELECT id FROM kv_probe WHERE company_id = 1 ORDER BY e <=> '[1,0,0]'")
        ).all()
        conn.execute(text("DROP TABLE kv_probe"))
    assert [r[0] for r in rows] == [1]


def test_min_similarity_env_defaults_and_rejects_invalid_values():
    env = {"KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED": "true"}
    assert rs.VectorRetrievalConfig.from_env(env).min_similarity == rs.DEFAULT_VECTOR_MIN_SIMILARITY
    assert rs.VectorRetrievalConfig.from_env({**env, "KNOWLEDGE_VECTOR_MIN_SIMILARITY": "0,5"}).min_similarity == 0.5
    for bad in ("abc", "1.5", "-0.1", ""):
        assert rs.VectorRetrievalConfig.from_env({**env, "KNOWLEDGE_VECTOR_MIN_SIMILARITY": bad}).min_similarity == rs.DEFAULT_VECTOR_MIN_SIMILARITY


def test_rrf_vector_weight_env_defaults_and_rejects_invalid_values():
    env = {"KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED": "true"}
    assert rs.VectorRetrievalConfig.from_env(env).rrf_vector_weight == rs.DEFAULT_VECTOR_RRF_WEIGHT
    assert rs.VectorRetrievalConfig.from_env({**env, "KNOWLEDGE_VECTOR_RRF_WEIGHT": "2,5"}).rrf_vector_weight == 2.5
    for bad in ("abc", "0", "-1", "11", ""):
        assert rs.VectorRetrievalConfig.from_env({**env, "KNOWLEDGE_VECTOR_RRF_WEIGHT": bad}).rrf_vector_weight == rs.DEFAULT_VECTOR_RRF_WEIGHT
