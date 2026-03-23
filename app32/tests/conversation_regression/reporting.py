from typing import Any, Dict, List

from .taxonomy import infer_failure_class


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
