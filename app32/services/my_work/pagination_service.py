"""Paginação de projeções do My Work sem alterar os totais do filtro."""

from __future__ import annotations

from typing import Any, Sequence


MAX_ACTIVITIES_PER_PAGE = 100
DEFAULT_ACTIVITIES_PER_PAGE = 75


def normalize_page(value: Any) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return 1


def normalize_per_page(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_ACTIVITIES_PER_PAGE
    return min(max(parsed, 1), MAX_ACTIVITIES_PER_PAGE)


def paginate_activities(activities: Sequence[dict], page: Any, per_page: Any) -> dict:
    """Retorna somente o lote solicitado, preservando o total do filtro."""
    normalized_page = normalize_page(page)
    normalized_per_page = normalize_per_page(per_page)
    total = len(activities)
    start = (normalized_page - 1) * normalized_per_page
    return {
        "items": list(activities[start : start + normalized_per_page]),
        "total": total,
        "page": normalized_page,
        "per_page": normalized_per_page,
        "has_more": start + normalized_per_page < total,
    }
