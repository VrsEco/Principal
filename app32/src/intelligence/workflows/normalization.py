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
