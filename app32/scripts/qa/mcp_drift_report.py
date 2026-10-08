"""Imprime o relatório de drift do mcp-versus (somente leitura).

Uso (a partir de app32/):  python scripts/qa/mcp_drift_report.py [--json]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "not-needed-for-report")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.mcp_drift import compute_drift, render_report  # noqa: E402


def main(argv: list[str]) -> int:
    data = compute_drift()
    if "--json" in argv:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_report(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
