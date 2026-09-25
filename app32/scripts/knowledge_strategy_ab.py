"""Avaliação A/B MANUAL de estratégias de recuperação do conhecimento (padrão: full_text x hybrid).

Roda as MESMAS perguntas em cada estratégia, para uma empresa, e compara a fonte citada com a
esperada. Serve para decidir com dados se a busca híbrida ajuda (ou atrapalha) antes de ampliar
o piloto. Não escreve conteúdo nem muda configuração; a estratégia é passada por consulta, então
o piloto (`KNOWLEDGE_VECTOR_PILOT_COMPANY_IDS`) não interfere. Único efeito no banco: cada consulta
híbrida registra 1 evento `query` de consumo de embedding (~10 tokens, custo desprezível).

Exemplo no servidor (a flag vale só para este processo):
  KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED=true FLASK_CONFIG=production APP_BOOTSTRAP_DB_SCHEMA=0 \
  APP_BOOTSTRAP_RUNTIME_SERVICES=0 python scripts/knowledge_strategy_ab.py --company-id 9

Casos: por padrão o golden set (`knowledge/golden_sets/sapiens_fase1_product_help_pt_br.json`) e o
arquivo `knowledge/golden_sets/ab_perguntas_pt_br.tsv`. Use `--cases` (JSON) e `--questions` (TSV
`pergunta<TAB>esperado1|esperado2`, esperado opcional) para outros. Um esperado casa por
`source_ref` exato ou por trecho do título (sem diferenciar maiúsculas).
Nunca agendar; rodar só com autorização do operador.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_GOLDEN = BASE_DIR / "knowledge" / "golden_sets" / "sapiens_fase1_product_help_pt_br.json"
DEFAULT_QUESTIONS = BASE_DIR / "knowledge" / "golden_sets" / "ab_perguntas_pt_br.tsv"
DEFAULT_STRATEGIES = ("full_text", "hybrid")
EXIT_OK, EXIT_NO_PROVIDER, EXIT_NO_CASES = 0, 4, 5
ABSTAIN = "-"  # esperado "-": a resposta correta é a abstenção (nenhuma fonte citada)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split("|") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def load_golden_cases(path: Path) -> list[dict[str, Any]]:
    """Casos do golden set JSON (lista, ou objeto com `questions`/`cases`/`items`)."""

    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else next(
        (data[key] for key in ("questions", "cases", "items") if isinstance(data.get(key), list)), [data]
    )
    cases = []
    for index, item in enumerate(items, start=1):
        question = str(item.get("question") or "").strip()
        if question:
            cases.append(
                {
                    "id": str(item.get("id") or f"G-{index:03d}"),
                    "question": question,
                    "expected": _as_list(item.get("expected_source_refs") or item.get("expected")),
                }
            )
    return cases


def load_question_cases(path: Path) -> list[dict[str, Any]]:
    """TSV `pergunta<TAB>esperado1|esperado2`; linhas vazias e iniciadas em `#` são ignoradas."""

    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        question, _, expected = line.partition("\t")
        if question.strip():
            cases.append(
                {"id": f"Q-{len(cases) + 1:03d}", "question": question.strip(), "expected": _as_list(expected)}
            )
    return cases


def matches_expected(hit: Mapping[str, Any], expected: Sequence[str]) -> bool:
    ref = str(hit.get("source_ref") or "")
    title = str(hit.get("title") or "").lower()
    return any(token == ref or token.lower() in title for token in expected)


def _hits(response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list(response.get("results") or response.get("citations") or [])


def run_case(
    service: Any,
    case: Mapping[str, Any],
    *,
    strategy: str,
    company_id: int,
    limit: int,
    mode: str,
    user_id: int | None = None,
    employee_id: int | None = None,
) -> dict[str, Any]:
    """Executa uma pergunta em uma estratégia; falhas viram registro (`error`), nunca abortam a rodada."""

    call = getattr(service, mode)
    try:
        response = call(
            case["question"],
            company_id=company_id,
            limit=limit,
            strategy=strategy,
            user_id=user_id,
            employee_id=employee_id,
        )
    except Exception as exc:  # noqa: BLE001 - registrar e seguir; o relatório mostra o erro
        return {"strategy": strategy, "error": f"{type(exc).__name__}: {exc}", "hits": [], "rank": None}
    hits = _hits(response)
    expected = list(case.get("expected") or [])
    if expected == [ABSTAIN]:
        rank = 1 if not hits else None  # o correto é não citar nada
    else:
        rank = next((i for i, hit in enumerate(hits, start=1) if matches_expected(hit, expected)), None) if expected else None
    plan = response.get("query_plan") or {}
    return {
        "strategy": strategy,
        "error": None,
        "hits": [{"source_ref": h.get("source_ref"), "title": h.get("title"), "score": h.get("score")} for h in hits],
        "rank": rank,
        "fallback_reason": plan.get("fallback_reason"),
        "executed": list(plan.get("strategies") or []),
        "abstained": not hits,
    }


def summarize(results: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]], limit: int) -> dict[str, Any]:
    scored = [(r, c) for r, c in zip(results, cases) if c.get("expected")]
    n = len(scored)
    ranks = [r["rank"] for r, _ in scored]
    return {
        "perguntas": len(results),
        "com_esperado": n,
        "acerto_1": sum(1 for x in ranks if x == 1),
        "acerto_topk": sum(1 for x in ranks if x is not None),
        "mrr": round(sum(1 / x for x in ranks if x) / n, 3) if n else None,
        "abstencoes": sum(1 for r in results if r.get("abstained")),
        "erros": sum(1 for r in results if r.get("error")),
        "topk": limit,
    }


def evaluate(
    service: Any,
    cases: Sequence[Mapping[str, Any]],
    *,
    strategies: Sequence[str],
    company_id: int,
    limit: int = 5,
    mode: str = "answer",
    user_id: int | None = None,
    employee_id: int | None = None,
) -> dict[str, Any]:
    per_strategy: dict[str, list[dict[str, Any]]] = {name: [] for name in strategies}
    for case in cases:
        for name in strategies:
            per_strategy[name].append(
                run_case(
                    service, case, strategy=name, company_id=company_id, limit=limit, mode=mode,
                    user_id=user_id, employee_id=employee_id,
                )
            )
    summary = {name: summarize(results, cases, limit) for name, results in per_strategy.items()}
    baseline = strategies[0]
    differences = []
    for index, case in enumerate(cases):
        tops = {name: (per_strategy[name][index]["hits"][:1] or [{}])[0].get("source_ref") for name in strategies}
        if len(set(tops.values())) > 1:
            differences.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected": list(case.get("expected") or []),
                    "topo": {
                        name: (per_strategy[name][index]["hits"][:1] or [{}])[0].get("title") or "(sem resultado)"
                        for name in strategies
                    },
                    "rank": {name: per_strategy[name][index]["rank"] for name in strategies},
                }
            )
    return {
        "company_id": company_id,
        "mode": mode,
        "limit": limit,
        "baseline": baseline,
        "resumo": summary,
        "divergencias": differences,
        "casos": [
            {"id": c["id"], "question": c["question"], "expected": list(c.get("expected") or []),
             "resultados": {name: per_strategy[name][i] for name in strategies}}
            for i, c in enumerate(cases)
        ],
    }


def render_text(report: Mapping[str, Any]) -> str:
    lines = [
        f"A/B de recuperação | empresa {report['company_id']} | modo {report['mode']} | top-{report['limit']}",
        "",
        f"{'estratégia':<12} {'perg':>5} {'c/esp':>6} {'acerto@1':>9} {'acerto@k':>9} {'MRR':>6} {'abst':>5} {'erros':>6}",
    ]
    for name, s in report["resumo"].items():
        mrr = "-" if s["mrr"] is None else f"{s['mrr']:.3f}"
        lines.append(
            f"{name:<12} {s['perguntas']:>5} {s['com_esperado']:>6} {s['acerto_1']:>9} {s['acerto_topk']:>9} "
            f"{mrr:>6} {s['abstencoes']:>5} {s['erros']:>6}"
        )
    diffs = report["divergencias"]
    lines += ["", f"Divergências no 1º resultado: {len(diffs)}"]
    for d in diffs:
        lines.append(f"- {d['id']} {d['question']}")
        if d["expected"]:
            lines.append(f"    esperado: {' | '.join(d['expected'])}")
        for name, title in d["topo"].items():
            rank = d["rank"][name]
            lines.append(f"    {name:<10} -> {title}" + (f"  (esperado na posição {rank})" if rank else ""))
    errors = [(c["id"], n, r["error"]) for c in report["casos"] for n, r in c["resultados"].items() if r["error"]]
    if errors:
        lines += ["", "Erros:"] + [f"- {i} [{n}]: {e}" for i, n, e in errors]
    return "\n".join(lines)


def build_service(strategies: Iterable[str], factory: Callable[[], Any] | None = None) -> tuple[Any | None, str | None]:
    """Serviço com provedor do ambiente; devolve `(None, motivo)` se `hybrid` for pedido sem provedor."""

    from services.knowledge.openai_embedding_provider import build_default_embedding_provider
    from services.knowledge.query_service import KnowledgeQueryService

    provider = build_default_embedding_provider()
    if provider is None and any(name in {"hybrid", "vector"} for name in strategies):
        return None, (
            "Sem provedor de embeddings: defina KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED=true (inline), modelo, "
            "versão e geração no ambiente e garanta uma chave (integrações do app, KNOWLEDGE_OPENAI_API_KEY "
            "ou OPENAI_API_KEY)."
        )
    return (factory or (lambda: KnowledgeQueryService(embedding_provider=provider)))(), None


def collect_cases(cases_path: Path | None, questions_path: Path | None) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path, loader in ((cases_path or DEFAULT_GOLDEN, load_golden_cases), (questions_path or DEFAULT_QUESTIONS, load_question_cases)):
        if path.is_file():
            cases.extend(loader(path))
    return cases


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--company-id", type=int, required=True, help="Empresa da consulta (ex.: 9, a piloto).")
    parser.add_argument("--strategies", default=",".join(DEFAULT_STRATEGIES), help="Lista separada por vírgula; a 1ª é a base.")
    parser.add_argument("--limit", type=int, default=5, help="Top-k considerado.")
    parser.add_argument("--mode", choices=("answer", "search"), default="answer", help="answer = o que o usuário vê.")
    parser.add_argument("--cases", type=Path, default=None, help="Golden set JSON.")
    parser.add_argument("--questions", type=Path, default=None, help="TSV pergunta<TAB>esperado1|esperado2.")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--employee-id", type=int, default=None)
    parser.add_argument("--json", dest="as_json", action="store_true", help="Saída em JSON.")
    args = parser.parse_args(argv)

    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]
    cases = collect_cases(args.cases, args.questions)
    if not cases:
        print("Nenhum caso encontrado (golden set e TSV vazios ou ausentes).", file=sys.stderr)
        return EXIT_NO_CASES

    from dotenv import load_dotenv

    load_dotenv()
    from app import create_app

    app = create_app()
    with app.app_context():
        service, reason = build_service(strategies)
        if service is None:
            print(reason, file=sys.stderr)
            return EXIT_NO_PROVIDER
        report = evaluate(
            service, cases, strategies=strategies, company_id=args.company_id, limit=args.limit,
            mode=args.mode, user_id=args.user_id, employee_id=args.employee_id,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.as_json else render_text(report))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
