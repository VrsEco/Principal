"""Gera um handoff curto e determinístico entre tasks, modelos ou agentes."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def _clean(items: Iterable[str]) -> list[str]:
    return [item.strip() for item in items if item and item.strip()]


def render_handoff(*, objective: str, decisions: Iterable[str] = (), files: Iterable[str] = (), tests: Iterable[str] = (), pending: Iterable[str] = ()) -> str:
    objective = objective.strip()
    if not objective:
        raise ValueError("objective é obrigatório")
    sections = [("Objetivo", [objective]), ("Decisões", _clean(decisions)), ("Arquivos", _clean(files)), ("Testes e evidências", _clean(tests)), ("Pendências", _clean(pending))]
    lines = ["# Handoff compacto", ""]
    for heading, items in sections:
        if not items:
            continue
        lines.extend([f"## {heading}", *[f"- {item}" for item in items], ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--pending", action="append", default=[])
    parser.add_argument("--output", type=Path, help="arquivo destino; padrão: stdout")
    args = parser.parse_args()
    content = render_handoff(objective=args.objective, decisions=args.decision, files=args.file, tests=args.test, pending=args.pending)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
