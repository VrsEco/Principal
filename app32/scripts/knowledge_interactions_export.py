"""Exporta perguntas REAIS de `knowledge_interactions` como candidatas ao conjunto do A/B (SOMENTE LEITURA).

Gera um TSV `pergunta<TAB>esperado<TAB>avaliacao<TAB>ocorrencias<TAB>fontes_citadas` compatível com
`scripts/knowledge_strategy_ab.py --questions` (o A/B lê só as duas primeiras colunas). O esperado só é
preenchido quando a avaliação do usuário é `correct` (a citação foi confirmada); para as demais a coluna fica
vazia e a linha precisa de revisão humana: citar X não prova que X é a resposta certa (viés a favor do
full_text, que foi quem respondeu). Use `-` no esperado para "deve abster" (ex.: pergunta fora do produto).

Exemplo no servidor (mesma forma do A/B; nunca agendar, rodar só com autorização do operador):
  FLASK_CONFIG=production APP_BOOTSTRAP_DB_SCHEMA=0 APP_BOOTSTRAP_RUNTIME_SERVICES=0 \
  python scripts/knowledge_interactions_export.py --company-id 9 --out /tmp/perguntas_empresa9.tsv
"""
from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

CONFIRMED = "correct"
MIN_QUESTION_CHARS = 8


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def build_candidates(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa por pergunta normalizada; esperado = 1ª fonte citada, só se alguma ocorrência foi `correct`."""

    grouped: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for row in rows:
        question = _clean(row.get("question"))
        if len(question) < MIN_QUESTION_CHARS:
            continue
        key = _clean(row.get("normalized_question") or question).lower()
        item = grouped.setdefault(
            key, {"question": question, "expected": "", "rating": "unrated", "count": 0, "cited": []}
        )
        item["count"] += 1
        citations = [c for c in (row.get("citations") or []) if isinstance(c, Mapping)]
        for citation in citations:
            ref = _clean(citation.get("source_ref"))
            if ref and ref not in item["cited"]:
                item["cited"].append(ref)
        status = row.get("rating_status")
        if status == CONFIRMED and citations and not item["expected"]:
            item["expected"] = _clean(citations[0].get("source_ref"))
            item["rating"] = CONFIRMED
        elif item["rating"] != CONFIRMED and status in {"partial", "wrong"}:
            item["rating"] = str(status)
    return sorted(grouped.values(), key=lambda i: (-i["count"], i["question"]))


def render_tsv(candidates: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Perguntas reais (knowledge_interactions). Colunas: pergunta, esperado, avaliacao, ocorrencias, fontes_citadas.",
        "# esperado vazio = REVISAR (nao entra no A/B com esperado); '-' = deve abster. Preencher com source_ref exato.",
    ]
    for c in candidates:
        cited = " | ".join(c["cited"][:3])
        lines.append(f"{c['question']}\t{c['expected']}\t{c['rating']}\t{c['count']}\t{cited}")
    return "\n".join(lines) + "\n"


def fetch_rows(company_id: int, since_days: int | None) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta

    from models.knowledge import KnowledgeInteraction

    query = KnowledgeInteraction.query.filter(KnowledgeInteraction.company_id == company_id)
    if since_days:
        query = query.filter(KnowledgeInteraction.created_at >= datetime.utcnow() - timedelta(days=since_days))
    return [
        {
            "question": i.question,
            "normalized_question": i.normalized_question,
            "rating_status": i.rating_status,
            "citations": list(i.citations_json or []),
        }
        for i in query.order_by(KnowledgeInteraction.created_at.desc()).all()
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--company-id", type=int, required=True)
    parser.add_argument("--since-days", type=int, default=None, help="Só interações dos últimos N dias.")
    parser.add_argument("--out", type=Path, default=None, help="Arquivo TSV; sem isso imprime na saída padrão.")
    args = parser.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()
    from app import create_app

    with create_app().app_context():
        candidates = build_candidates(fetch_rows(args.company_id, args.since_days))
    text = render_tsv(candidates)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        confirmed = sum(1 for c in candidates if c["expected"])
        print(f"{len(candidates)} perguntas distintas ({confirmed} com esperado confirmado) -> {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
