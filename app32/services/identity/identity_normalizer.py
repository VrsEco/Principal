from __future__ import annotations

import re
import unicodedata


def normalize_email(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits or None


def normalize_name(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None

