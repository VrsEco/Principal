from __future__ import annotations

from typing import Any, Iterable, List, Optional


def coalesce_str(payload: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return None


def positive_int_list(raw_values: Any) -> List[int]:
    values: List[int] = []
    if isinstance(raw_values, list):
        iterable: Iterable[Any] = raw_values
    elif raw_values is None:
        iterable = []
    else:
        iterable = [raw_values]

    seen = set()
    for raw_value in iterable:
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            continue
        if parsed <= 0 or parsed in seen:
            continue
        seen.add(parsed)
        values.append(parsed)
    return values


def split_text_values(raw_value: str, pattern: str) -> List[str]:
    import re

    values: List[str] = []
    seen = set()
    for item in re.split(pattern, str(raw_value or "").strip()):
        normalized = str(item or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        values.append(normalized)
    return values
