from __future__ import annotations

from typing import Any

DEFAULT_PERFORMANCE_THRESHOLDS: dict[str, float] = {
    "red": 80.0,
    "yellow": 90.0,
    "green": 110.0,
}


def _coerce_threshold(value: Any, *, increment: float = 0.0) -> float | None:
    if value in (None, ""):
        return None

    try:
        return float(value) + increment
    except (TypeError, ValueError):
        return None


def normalize_performance_ranges(raw_ranges: Any) -> dict[str, float]:
    """
    Normaliza performance_ranges para o formato limiar usado nas regras do app.

    Suporta:
    - dict moderno: {"red": 80, "yellow": 95, "green": 110}
    - lista legada com bandas por cor e intervalos min/max
    """
    normalized = dict(DEFAULT_PERFORMANCE_THRESHOLDS)

    if isinstance(raw_ranges, dict):
        for color in ("red", "yellow", "green"):
            value = _coerce_threshold(raw_ranges.get(color))
            if value is not None:
                normalized[color] = value
        return normalized

    if not isinstance(raw_ranges, list):
        return normalized

    by_color = {}
    for item in raw_ranges:
        if not isinstance(item, dict):
            continue

        color = str(item.get("color") or "").strip().lower()
        if color:
            by_color[color] = item

    legacy_thresholds = {
        "red": _coerce_threshold(by_color.get("yellow", {}).get("min")),
        "yellow": _coerce_threshold(by_color.get("green", {}).get("min")),
        "green": _coerce_threshold(by_color.get("blue", {}).get("min")),
    }
    legacy_fallbacks = {
        "red": _coerce_threshold(by_color.get("red", {}).get("max"), increment=1.0),
        "yellow": _coerce_threshold(by_color.get("yellow", {}).get("max"), increment=1.0),
        "green": _coerce_threshold(by_color.get("green", {}).get("max"), increment=1.0),
    }

    for color in ("red", "yellow", "green"):
        value = legacy_thresholds[color]
        if value is None:
            value = legacy_fallbacks[color]
        if value is not None:
            normalized[color] = value

    return normalized
