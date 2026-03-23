from __future__ import annotations

from typing import Any, Dict, List

from .taxonomy import infer_failure_class


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
