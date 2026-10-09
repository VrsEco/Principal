"""Relatório do contrato de mutações do mcp-versus (modo relatório; não altera nada).

Uso (na pasta app32):
    python scripts/qa/mcp_mutation_report.py            # resumo por código
    python scripts/qa/mcp_mutation_report.py --tools    # lista cada ferramenta com suas violações
    python scripts/qa/mcp_mutation_report.py --write-baseline   # regrava a linha de base (só para REDUZIR)
"""
from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")

BASELINE = ROOT / "tests" / "data" / "mcp_mutation_violations_baseline.json"


def main(argv: list[str]) -> int:
    from src.core.mcp_cohort_contract import probe_registered_tools
    from src.core.mcp_mutation_contract import as_codes, survey_mutations
    from src.intelligence.tool_catalog import catalog

    report = survey_mutations(probe_registered_tools(), list(catalog.iter_capabilities()))
    codes = as_codes(report)
    if "--write-baseline" in argv:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(codes, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"linha de base gravada: {len(codes)} ferramentas com violação em {BASELINE}")
        return 0

    by_code = collections.Counter(code for found in codes.values() for code in found)
    print(f"mutações: {len(report)}  com violação: {len(codes)}  limpas: {len(report) - len(codes)}")
    for code, n in sorted(by_code.items()):
        print(f"  {code}: {n}")
    if "--tools" in argv:
        for name, found in codes.items():
            print(f"{name}: {', '.join(found)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
