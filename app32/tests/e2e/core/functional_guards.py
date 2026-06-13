from __future__ import annotations

from collections.abc import Iterable
import re


PUBLIC_ERROR_PATTERNS = (
    "Erro interno do servidor",
    "Erro interno",
    "Tente novamente ou contate o suporte",
    "Erro ao salvar",
    "Erro ao publicar",
)


def _visible_text_for_guard(text: str | None) -> str:
    body = str(text or "")
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    return body


def contains_public_error(text: str | None) -> bool:
    normalized = _visible_text_for_guard(text).lower()
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
