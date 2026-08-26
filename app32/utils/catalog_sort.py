"""Ordenação natural e determinística para listas de catálogo da aplicação."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from typing import Any


FieldAccessor = str | Callable[[Any], Any]


def _field_value(item: Any, accessor: FieldAccessor) -> Any:
    if callable(accessor):
        return accessor(item)
    if isinstance(item, Mapping):
        return item.get(accessor)
    return getattr(item, accessor, None)


def natural_text_key(value: Any) -> tuple[tuple[int, Any], ...]:
    """Quebra texto em partes para que ``I.2`` venha antes de ``I.10``."""
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.split(r"(\d+)", text)
        if part
    )


def coded_name_sort_key(
    item: Any,
    *,
    code: FieldAccessor = "code",
    name: FieldAccessor = "name",
) -> tuple[Any, ...]:
    """Prioriza código natural; sem código, usa o nome em ordem alfabética."""
    code_value = str(_field_value(item, code) or "").strip()
    name_value = _field_value(item, name)
    stable_id = natural_text_key(_field_value(item, "id"))
    if code_value:
        return (0, natural_text_key(code_value), natural_text_key(name_value), stable_id)
    return (1, natural_text_key(name_value), stable_id)


def sort_catalog_entries(
    entries: Iterable[Any],
    *,
    code: FieldAccessor = "code",
    name: FieldAccessor = "name",
) -> list[Any]:
    """Retorna uma nova lista com a regra canônica de ordenação de catálogos."""
    return sorted(entries, key=lambda item: coded_name_sort_key(item, code=code, name=name))
