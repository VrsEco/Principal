from __future__ import annotations

from collections.abc import Iterable


PUBLIC_ERROR_PATTERNS = (
    "Erro interno do servidor",
    "Erro interno",
    "Tente novamente ou contate o suporte",
    "Erro ao salvar",
    "Erro ao publicar",
)


def contains_public_error(text: str | None) -> bool:
    normalized = str(text or "").lower()
    return any(pattern.lower() in normalized for pattern in PUBLIC_ERROR_PATTERNS)


def html_contains_all_markers(text: str | None, markers: Iterable[str]) -> bool:
    body = str(text or "")
    return all(marker in body for marker in markers)


def html_contains_any_marker(text: str | None, markers: Iterable[str]) -> bool:
    body = str(text or "")
    return any(marker in body for marker in markers)


def is_html_success(text: str | None, *, any_markers: Iterable[str] = (), all_markers: Iterable[str] = ()) -> bool:
    if contains_public_error(text):
        return False
    if all_markers and not html_contains_all_markers(text, all_markers):
        return False
    if any_markers and not html_contains_any_marker(text, any_markers):
        return False
    return True
