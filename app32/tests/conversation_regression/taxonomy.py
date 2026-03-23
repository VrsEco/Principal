from typing import Any, Dict


VALID_FAILURE_CLASSES = {"parsing", "routing", "multi_turn", "execution"}


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


def classify_result_bucket(*, case: Dict[str, Any], passed: bool) -> str:
    if passed:
        return "passed"
    return infer_failure_class(case)
