from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .contracts import WorkflowDiscoveryResult, WorkflowMatch


def _normalize_reasons(raw_reasons: Iterable[Any], *, limit: int) -> List[str]:
    reasons: List[str] = []
    for raw_reason in raw_reasons or []:
        reason = str(raw_reason or "").strip()
        if not reason:
            continue
        reasons.append(reason)
        if len(reasons) >= limit:
            break
    return reasons


def _compact_match_dict(raw_match: Dict[str, Any], *, reason_limit: int) -> Dict[str, Any]:
    compacted: Dict[str, Any] = {
        "code": str(raw_match.get("code") or "").strip(),
        "action_key": str(raw_match.get("action_key") or "").strip(),
        "score": int(raw_match.get("score") or 0),
        "reasons": _normalize_reasons(raw_match.get("reasons") or [], limit=reason_limit),
    }
    return {key: value for key, value in compacted.items() if value not in ("", [], None)}


def _compact_workflow_match(match: WorkflowMatch, *, reason_limit: int) -> Dict[str, Any]:
    return {
        "code": str(match.workflow.code or "").strip(),
        "action_key": str(match.workflow.action_key or "").strip(),
        "score": int(match.score or 0),
        "reasons": _normalize_reasons(match.reasons or [], limit=reason_limit),
    }


def build_workflow_discovery_trace(
    discovery: WorkflowDiscoveryResult,
    *,
    match_limit: int = 3,
    reason_limit: int = 4,
) -> Dict[str, Any]:
    telemetry = dict(discovery.telemetry or {})
    selected_match = discovery.selected_match
    selected = selected_match.workflow if selected_match else None

    top_matches = telemetry.get("final_top_matches") or telemetry.get("top_matches")
    compact_matches: List[Dict[str, Any]] = []
    if isinstance(top_matches, list) and top_matches:
        for raw_match in top_matches[:match_limit]:
            if isinstance(raw_match, dict):
                compact_matches.append(_compact_match_dict(raw_match, reason_limit=reason_limit))
    if not compact_matches:
        compact_matches = [
            _compact_workflow_match(match, reason_limit=reason_limit)
            for match in discovery.matches[:match_limit]
        ]

    trace: Dict[str, Any] = {
        "strategy": str(telemetry.get("strategy") or "unknown"),
        "candidate_count": int(telemetry.get("merged_match_count") or telemetry.get("match_count") or len(discovery.matches)),
        "selected_code": str(telemetry.get("selected_code") or getattr(selected, "code", "") or "").strip(),
        "selected_action_key": str(
            telemetry.get("selected_action_key")
            or getattr(selected, "action_key", "")
            or ""
        ).strip(),
        "reranker_applied": bool(telemetry.get("reranker_applied", False)),
        "top_matches": compact_matches,
    }

    if "lexical_match_count" in telemetry:
        trace["lexical_match_count"] = int(telemetry.get("lexical_match_count") or 0)
    if "semantic_match_count" in telemetry:
        trace["semantic_match_count"] = int(telemetry.get("semantic_match_count") or 0)
    if telemetry.get("reranker_kind"):
        trace["reranker_kind"] = str(telemetry.get("reranker_kind") or "").strip()
    if selected_match is not None:
        trace["selected_score"] = int(selected_match.score or 0)
        trace["selected_reasons"] = _normalize_reasons(selected_match.reasons or [], limit=reason_limit)

    return {
        key: value
        for key, value in trace.items()
        if value not in ("", [], None)
    }


def build_explicit_workflow_trace(
    workflow: Any,
    *,
    explicit_code: Optional[str] = None,
) -> Dict[str, Any]:
    code = str(getattr(workflow, "code", "") or "").strip()
    action_key = str(getattr(workflow, "action_key", "") or "").strip()
    trace = {
        "strategy": "explicit_code",
        "candidate_count": 1,
        "selected_code": code,
        "selected_action_key": action_key,
        "explicit_code": str(explicit_code or code).strip(),
        "top_matches": [
            {
                "code": code,
                "action_key": action_key,
                "score": 1000,
                "reasons": ["explicit:code_match"],
            }
        ],
    }
    return {
        key: value
        for key, value in trace.items()
        if value not in ("", [], None)
    }
