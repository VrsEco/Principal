"""Ensaio da projeção pgvector em PostgreSQL DESCARTÁVEL (nunca produção/dev).

Uso:
  set APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL=postgresql+psycopg2://postgres:SENHA@127.0.0.1:55432/knowledge_vector_test
  python scripts/knowledge_vector_rehearsal.py

Guardas: host local, porta diferente de 5432 e nome de banco terminado em `_test`.
Valida: migrations 1400/1500 (upgrade), isolamento por tenant na consulta vetorial,
descarte de vetor obsoleto e rollback que preserva knowledge_sources/knowledge_chunks.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import Flask
from sqlalchemy import text
from sqlalchemy.engine import make_url

ENV = "APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL"
DIM = 1536


def _load(name: str):
    path = BASE_DIR / "migrations" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vec(*head: float) -> str:
    values = list(head) + [0.0] * (DIM - len(head))
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


def _check(label: str, condition: bool) -> None:
    print(("OK   " if condition else "FALHA"), label)
    if not condition:
        raise SystemExit(1)


def main() -> int:
    url_text = os.getenv(ENV, "")
    if not url_text:
        print(f"Defina {ENV} (ver runbook_pgvector_banco_teste_conhecimento_v1.md).", file=sys.stderr)
        return 2
    url = make_url(url_text)
    if not (url.drivername.startswith("postgresql") and url.host in {"127.0.0.1", "localhost"}
            and url.port not in (None, 5432) and str(url.database).endswith("_test")):
        print("Recusado: exige PostgreSQL local, porta != 5432 e banco terminado em _test.", file=sys.stderr)
        return 3

    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI=url_text, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    from models import db
    from models.company import Company
    from models.knowledge import (
        KnowledgeChunk,
        KnowledgeEmbeddingUsageEvent,
        KnowledgeIndexRun,
        KnowledgeSource,
        KnowledgeSourceGrant,
    )

    db.init_app(app)
    with app.app_context():
        # Banco descartável (guardas acima): recria o schema public do zero.
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        import models  # noqa: F401  registra todos os modelos (FKs para users/employees)

        needed, queue = set(), [
            "companies", "knowledge_sources", "knowledge_source_grants", "knowledge_chunks",
            "knowledge_index_runs",
        ]
        while queue:  # fecho de dependências por chave estrangeira
            name = queue.pop()
            if name in needed:
                continue
            needed.add(name)
            queue.extend(fk.column.table.name for fk in db.metadata.tables[name].foreign_keys)
        db.metadata.create_all(
            bind=db.engine, tables=[db.metadata.tables[n] for n in needed],
            checkfirst=True,
        )

        m_vector = _load("20260924_1400_knowledge_vector_projection")
        m_usage = _load("20260924_1500_knowledge_embedding_usage_events")
        with db.engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                m_vector.upgrade()
                m_usage.upgrade()
        _check("upgrade 1400 + 1500 aplicado (extensão vector criada)", True)

        # dados: dois tenants com o MESMO vetor, mais um chunk obsoleto e um do produto
        def source(company_id, ref, scope="company"):
            s = KnowledgeSource(
                knowledge_scope=scope, company_id=company_id, source_type="process_publication",
                source_ref=ref, knowledge_kind="procedure", title=ref, canonical_uri=f"app://{ref}",
                status="published", authority_level="internal", version="v1", content_checksum=ref * 8,
            )
            s.chunks.append(KnowledgeChunk(
                knowledge_scope=scope, company_id=company_id, section_key="s",
                content=f"conteudo {ref}", content_checksum=(ref + "c") * 8,
            ))
            if scope == "company":
                s.grants.append(KnowledgeSourceGrant(company_id=company_id, grant_scope="company"))
            db.session.add(s)
            return s

        db.session.add_all([Company(id=1, name="A"), Company(id=2, name="B")])
        a, b, stale = source(1, "alfa"), source(2, "beta"), source(1, "velho")
        db.session.commit()
        for s, checksum in ((a, None), (b, None), (stale, "checksum-antigo")):
            chunk = s.chunks[0]
            db.session.execute(text(
                "INSERT INTO knowledge_chunk_embeddings (knowledge_chunk_id, knowledge_source_id, company_id, "
                "knowledge_scope, source_type, chunk_checksum, embedding_model, embedding_version, "
                "index_generation, embedding) VALUES (:c, :s, :co, 'company', 'process_publication', :ck, "
                "'m', 'v1', 1, CAST(:e AS vector))"
            ), {"c": chunk.id, "s": s.id, "co": s.company_id,
                "ck": checksum or chunk.content_checksum, "e": _vec(1.0)})
        db.session.commit()

        from services.knowledge.query_service import KnowledgeQueryService
        from services.knowledge.retrieval_strategy import EmbeddingSpec
        from services.knowledge.vector_retrieval import build_vector_candidates_statement

        spec = EmbeddingSpec("m", "v1", 1)
        _, plan = KnowledgeQueryService().build_plan("pergunta valida", company_id=1)
        rows = db.session.execute(build_vector_candidates_statement(
            plan, spec, [1.0] + [0.0] * (DIM - 1), user_id=None, employee_id=None, now=datetime.utcnow(),
        )).all()
        refs = sorted(row[0].source_ref for row in rows)
        _check(f"vetor: empresa 1 enxerga somente 'alfa' (obteve {refs})", refs == ["alfa"])
        _, plan2 = KnowledgeQueryService().build_plan("pergunta valida", company_id=2)
        rows2 = db.session.execute(build_vector_candidates_statement(
            plan2, spec, [1.0] + [0.0] * (DIM - 1), user_id=None, employee_id=None, now=datetime.utcnow(),
        )).all()
        _check("vetor: empresa 2 enxerga somente 'beta'", [r[0].source_ref for r in rows2] == ["beta"])
        _check("vetor: embedding com checksum obsoleto é descartado", "velho" not in refs)

        db.session.remove()  # libera locks da sessão de leitura antes do rollback
        with db.engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                m_usage.downgrade()
                m_vector.downgrade()
        db.session.remove()
        with db.engine.connect() as conn:
            has_projection = conn.execute(text(
                "SELECT to_regclass('knowledge_chunk_embeddings') IS NOT NULL")).scalar()
            sources = conn.execute(text("SELECT count(*) FROM knowledge_sources")).scalar()
            chunks = conn.execute(text("SELECT count(*) FROM knowledge_chunks")).scalar()
            extension = conn.execute(text("SELECT count(*) FROM pg_extension WHERE extname='vector'")).scalar()
        _check("rollback: projeção vetorial removida", not has_projection)
        _check("rollback: knowledge_sources/chunks intactos (3/3)", (sources, chunks) == (3, 3))
        _check("rollback: extensão vector preservada", extension == 1)
    print("Ensaio concluído com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
