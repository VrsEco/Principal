from __future__ import annotations

import html
import json
from typing import Any, Dict, List

from .reporting import build_catalog_report
from .smoke_assisted import build_smoke_assisted_plan


def build_operational_report(catalog: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    return {
        "summary": build_catalog_report(catalog),
        "smoke_plan": build_smoke_assisted_plan(catalog),
    }


def render_operational_report_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def render_operational_report_html(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    smoke = report.get("smoke_plan") or {}
    chapter_cards = []
    for chapter, chapter_data in (summary.get("chapters") or {}).items():
        chapter_cards.append(
            "<section>"
            f"<h2>{html.escape(chapter)}</h2>"
            f"<p>Total: {chapter_data.get('total_cases', 0)}</p>"
            f"<p>Tipos: {html.escape(json.dumps(chapter_data.get('types', {}), ensure_ascii=False))}</p>"
            f"<p>Falhas: {html.escape(json.dumps(chapter_data.get('failure_classes', {}), ensure_ascii=False))}</p>"
            "</section>"
        )
    smoke_cards = []
    for chapter, chapter_data in (smoke.get("chapters") or {}).items():
        smoke_cards.append(
            "<section>"
            f"<h3>Smoke {html.escape(chapter)}</h3>"
            f"<pre>{html.escape(json.dumps(chapter_data.get('prioritized_smokes', []), ensure_ascii=False, indent=2))}</pre>"
            "</section>"
        )
    return (
        "<html><head><meta charset='utf-8'><title>Conversation Regression V4</title></head><body>"
        "<h1>Conversation Regression V4</h1>"
        f"<p>Total de capítulos: {summary.get('total_chapters', 0)}</p>"
        f"<p>Total de casos: {summary.get('total_cases', 0)}</p>"
        + "".join(chapter_cards)
        + "<hr/>"
        + "".join(smoke_cards)
        + "</body></html>"
    )
