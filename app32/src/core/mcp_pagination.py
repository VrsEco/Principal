"""Paginação das listagens MCP de leitura (sem ela, listas grandes estouram o limite do cliente)."""

from __future__ import annotations

from typing import Any

PAGE_DEFAULT = 20
PAGE_MAX = 100


def validated_page(limit: Any, offset: Any) -> tuple[int, int]:
    for value in (limit, offset):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("limit e offset devem ser inteiros.")
    if limit < 1 or limit > PAGE_MAX:
        raise ValueError(f"limit deve estar entre 1 e {PAGE_MAX}.")
    if offset < 0:
        raise ValueError("offset deve ser maior ou igual a 0.")
    return limit, offset


def page_of(rows: list, limit: int, offset: int) -> dict:
    window = rows[offset : offset + limit]
    end = offset + len(window)
    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "returned": len(window),
        "has_more": end < len(rows),
        "next_offset": end if end < len(rows) else None,
        "window": window,
    }
