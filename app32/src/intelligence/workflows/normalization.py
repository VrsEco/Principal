import re
import unicodedata
from typing import List, Set


STOP_WORDS = {
    "a",
    "as",
    "ao",
    "aos",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "um",
    "uma",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9._\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize_text(value: str) -> List[str]:
    normalized = normalize_text(value)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [
        token
        for token in tokens
        if len(token) > 1 and token not in STOP_WORDS
    ]


def token_set(value: str) -> Set[str]:
    return set(tokenize_text(value))


def normalize_token_root(token: str) -> str:
    normalized = normalize_text(token)
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    if not normalized:
        return ""
    if len(normalized) <= 5:
        return normalized
    return normalized[:5]


def token_roots(value: str) -> List[str]:
    roots: List[str] = []
    for token in tokenize_text(value):
        root = normalize_token_root(token)
        if root:
            roots.append(root)
    return roots


def root_set(value: str) -> Set[str]:
    return set(token_roots(value))
