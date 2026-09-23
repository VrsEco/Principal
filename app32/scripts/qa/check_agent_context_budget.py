"""Lint determinístico para impedir regressão de contexto nas instruções do APP32."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MANDATORY_FILES = {
    ".agent/skills/gestao_versus_core/SKILL.md": 600,
    ".agent/router/orchestrator.md": 300,
    ".agent/references/constitution.md": 250,
    ".agent/router/routing-matrix.md": 400,
}
SPEC_PATH = "docs/spec/politica_orcamento_contexto_v1.md"
WORD_RE = re.compile(r"\S+")
HEADING_RE = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")


def word_count(content: str) -> int:
    return len(WORD_RE.findall(content))


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    metrics: list[dict[str, Any]] = []
    violations: list[dict[str, str]] = []

    for relative_path, limit in MANDATORY_FILES.items():
        path = root / relative_path
        if not path.is_file():
            violations.append({"file": relative_path, "rule": "required_file", "message": "arquivo obrigatório ausente"})
            continue
        content = path.read_text(encoding="utf-8")
        words = word_count(content)
        metrics.append({"file": relative_path, "words": words, "limit": limit})
        if words > limit:
            violations.append({
                "file": relative_path,
                "rule": "word_budget",
                "message": f"{words} palavras excedem o limite de {limit}",
            })
        headings = [match.group(1).strip().casefold() for match in HEADING_RE.finditer(content)]
        duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
        for heading in duplicates:
            violations.append({"file": relative_path, "rule": "duplicate_heading", "message": f"heading duplicado: {heading}"})

    spec = root / SPEC_PATH
    if not spec.is_file():
        violations.append({"file": SPEC_PATH, "rule": "required_spec", "message": "SPEC de orçamento de contexto ausente"})

    core = root / ".agent/skills/gestao_versus_core/SKILL.md"
    if core.is_file() and SPEC_PATH not in core.read_text(encoding="utf-8"):
        violations.append({"file": str(core.relative_to(root)), "rule": "spec_reference", "message": "skill não referencia a SPEC canônica"})

    return {
        "ok": not violations,
        "mandatory_words": sum(row["words"] for row in metrics),
        "files": metrics,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="raiz app32")
    parser.add_argument("--json", action="store_true", help="emite resultado JSON")
    args = parser.parse_args()
    result = audit(args.root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"context-budget: {'OK' if result['ok'] else 'VIOLAÇÕES'}; palavras obrigatórias={result['mandatory_words']}")
        for violation in result["violations"]:
            print(f"- {violation['file']} [{violation['rule']}]: {violation['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
