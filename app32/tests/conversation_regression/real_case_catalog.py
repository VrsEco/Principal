from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


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
