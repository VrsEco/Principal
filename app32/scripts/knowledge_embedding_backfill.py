"""Backfill MANUAL da projeção vetorial do manual do produto (product_help).

Padrão = simulação (não chama a OpenAI). Para executar de verdade:
  KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED=true KNOWLEDGE_EMBEDDING_MODEL=text-embedding-3-small \
  KNOWLEDGE_EMBEDDING_VERSION=v1 KNOWLEDGE_EMBEDDING_INDEX_GENERATION=1 OPENAI_API_KEY=... \
  python scripts/knowledge_embedding_backfill.py --execute --max-chunks 50
Nunca agendar; nunca rodar em produção sem autorização explícita.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--execute", action="store_true", help="Chama o provedor e grava (padrão: simulação).")
    parser.add_argument("--max-chunks", type=int, default=50)
    args = parser.parse_args(argv)

    load_dotenv()
    from app import create_app
    from services.knowledge.embedding_backfill_service import BackfillRefused, EmbeddingBackfillService
    from services.knowledge.openai_embedding_provider import OpenAIEmbeddingProvider, resolve_embedding_api_key
    from services.knowledge.retrieval_strategy import VectorRetrievalConfig

    config = VectorRetrievalConfig.from_env()
    if config.embedding is None:
        print("Configuração incompleta: defina a flag, modelo, versão e geração (ver docstring).", file=sys.stderr)
        return 2
    app = create_app()
    with app.app_context():
        embedder = None
        if args.execute:
            # Mesma ordem de chave do runtime: KNOWLEDGE_OPENAI_API_KEY, integrações do app, OPENAI_API_KEY.
            available, api_key = resolve_embedding_api_key()
            if not available:
                print(
                    "Sem chave de embeddings (KNOWLEDGE_OPENAI_API_KEY, integrações do app ou OPENAI_API_KEY).",
                    file=sys.stderr,
                )
                return 4
            embedder = OpenAIEmbeddingProvider(model=config.embedding.model, api_key=api_key).embed_many
        try:
            report = EmbeddingBackfillService(embedder=embedder).run(
                config.embedding, max_chunks=args.max_chunks, dry_run=not args.execute
            )
        except BackfillRefused as exc:
            print(f"Recusado: {exc}", file=sys.stderr)
            return 3
    print(json.dumps(report.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
