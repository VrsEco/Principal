from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


BASE_DIR = Path(__file__).resolve().parents[1]
FIXTURES_PATH = BASE_DIR / "data" / "conversation_regression" / "cases.json"
VALID_FAILURE_CLASSES = {"parsing", "routing", "multi_turn", "execution"}


def load_catalog() -> Dict[str, List[Dict[str, Any]]]:
    with FIXTURES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def infer_failure_class(case: Dict[str, Any]) -> str:
    explicit = str(case.get("failure_class") or "").strip().lower()
    if explicit in VALID_FAILURE_CLASSES:
        return explicit

    case_type = str(case.get("type") or "").strip().lower()
    if case_type == "parsing":
        return "parsing"
    if case_type == "routing":
        return "routing"
    if case_type == "multiturn":
        return "multi_turn"
    return "execution"


def build_catalog_report(catalog: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    chapter_stats: Dict[str, Dict[str, Any]] = {}
    total_cases = 0
    for chapter_key, cases in catalog.items():
        type_breakdown: Dict[str, int] = {}
        for case in cases:
            case_type = case.get("type", "unknown")
            type_breakdown[case_type] = type_breakdown.get(case_type, 0) + 1
        failure_breakdown: Dict[str, int] = {}
        for case in cases:
            failure_class = infer_failure_class(case)
            failure_breakdown[failure_class] = failure_breakdown.get(failure_class, 0) + 1
        chapter_stats[chapter_key] = {
            "total_cases": len(cases),
            "types": type_breakdown,
            "failure_classes": failure_breakdown,
            "case_ids": [case.get("id") for case in cases],
        }
        total_cases += len(cases)
    return {
        "total_chapters": len(catalog),
        "total_cases": total_cases,
        "chapters": chapter_stats,
    }


def build_smoke_assisted_plan(catalog: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    plan_chapters: Dict[str, Any] = {}
    total_cases = 0
    for chapter_key, cases in catalog.items():
        prioritized: List[Dict[str, Any]] = []
        for case in cases:
            if case.get("source", "").startswith("real_") or case.get("failure_class") in {"multi_turn", "execution"}:
                prioritized.append(
                    {
                        "id": case["id"],
                        "failure_class": infer_failure_class(case),
                        "prompt": case.get("input"),
                        "expected_signal": case.get("expected_action_key")
                        or case.get("expected_final_response")
                        or case.get("expected_payload")
                        or case.get("expected"),
                    }
                )
        plan_chapters[chapter_key] = {
            "total_cases": len(cases),
            "prioritized_smokes": prioritized[:5],
        }
        total_cases += len(cases)
    return {
        "total_cases": total_cases,
        "chapters": plan_chapters,
    }


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


def _candidate_attr(candidate: Any, field: str, default=None):
    if isinstance(candidate, Mapping):
        return candidate.get(field, default)
    return getattr(candidate, field, default)


def infer_chapter_from_gap_candidate(candidate: Any) -> str:
    request_text = str(_candidate_attr(candidate, "user_request_text", "") or "").strip().lower()
    if any(token in request_text for token in ("analise", "análise", "audite", "auditoria", "sem responsável", "sem data")):
        return "d_analisar"
    if any(token in request_text for token in ("conclu", "finaliz", "encerr", "aprov", "rejeit", "adiar", "coloque todas")):
        return "c_encerrar"
    if any(token in request_text for token in ("cadastre", "crie", "nova atividade", "iniciar", "abra", "agende")):
        return "b_cadastrar_iniciar"
    return "a_consultar"


def infer_case_type_from_gap_candidate(candidate: Any) -> str:
    resolution_type = str(_candidate_attr(candidate, "resolution_type", "") or "").strip().lower()
    if resolution_type in {"ambiguous_needs_clarification", "entity_resolution_failed"}:
        return "multiturn"
    return "routing"


def infer_failure_class_from_gap_candidate(candidate: Any) -> str:
    resolution_type = str(_candidate_attr(candidate, "resolution_type", "") or "").strip().lower()
    if resolution_type in {"ambiguous_needs_clarification", "entity_resolution_failed"}:
        return "multi_turn"
    if resolution_type == "parser_failed":
        return "parsing"
    return "routing"


def workflow_gap_to_case_stub(
    candidate: Any,
    *,
    chapter: str,
    case_type: str,
    failure_class: str,
    expected: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    request_text = str(_candidate_attr(candidate, "user_request_text", "") or "").strip()
    task_code = str(_candidate_attr(candidate, "app_task_code", "") or "").strip()
    resolution_type = str(_candidate_attr(candidate, "resolution_type", "") or "").strip()
    channel = str(_candidate_attr(candidate, "channel", "web") or "web").strip().lower()
    case_id = task_code.lower().replace(".", "_") if task_code else f"gap_{_candidate_attr(candidate, 'id', 'sem_id')}"
    return {
        "id": case_id,
        "chapter": chapter,
        "type": case_type,
        "failure_class": failure_class,
        "source": f"workflow_gap:{channel}",
        "source_ref": {
            "workflow_gap_id": _candidate_attr(candidate, "id"),
            "app_task_code": task_code or None,
            "resolution_type": resolution_type or None,
        },
        "input": request_text,
        "expected": dict(expected or {}),
    }


def build_real_case_export(
    candidates: Iterable[Any],
    *,
    chapter: str | None = None,
    case_type: str | None = None,
    failure_class: str | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        resolved_chapter = chapter or infer_chapter_from_gap_candidate(candidate)
        resolved_case_type = case_type or infer_case_type_from_gap_candidate(candidate)
        resolved_failure_class = failure_class or infer_failure_class_from_gap_candidate(candidate)
        grouped.setdefault(resolved_chapter, []).append(
            workflow_gap_to_case_stub(
                candidate,
                chapter=resolved_chapter,
                case_type=resolved_case_type,
                failure_class=resolved_failure_class,
            )
        )
    return grouped


def build_real_case_backlog_sync_payload(cases_by_chapter: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for chapter, cases in cases_by_chapter.items():
        for case in cases:
            source_ref = dict(case.get("source_ref") or {})
            is_resolved = bool(case.get("resolved_in_catalog"))
            items.append(
                {
                    "case_id": case.get("id"),
                    "chapter": chapter,
                    "failure_class": case.get("failure_class"),
                    "workflow_gap_id": source_ref.get("workflow_gap_id"),
                    "app_task_code": source_ref.get("app_task_code"),
                    "status": "completed" if is_resolved else "planned",
                    "stage": "completed" if is_resolved else "inbox",
                    "resolved_in_catalog": is_resolved,
                    "summary": (
                        f"Regressão conversacional coberta [{chapter}]"
                        if is_resolved
                        else f"Regressão conversacional catalogada [{chapter}]"
                    ),
                }
            )
    return {
        "project_code": "AA.J.31",
        "integration": "conversation_regression_v4",
        "items": items,
    }
