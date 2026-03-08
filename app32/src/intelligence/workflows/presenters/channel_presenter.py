from __future__ import annotations

from typing import Any, Callable, Dict


CHANNEL_ALIASES = {
    "wpp": "whatsapp",
    "whats": "whatsapp",
    "ig": "instagram",
    "insta": "instagram",
    "tg": "telegram",
}


def normalize_channel(channel: str) -> str:
    normalized = str(channel or "web").strip().lower() or "web"
    return CHANNEL_ALIASES.get(normalized, normalized)


def get_channel_family(channel: str) -> str:
    normalized = normalize_channel(channel)
    if normalized in {"whatsapp", "telegram", "instagram"}:
        return "chat"
    if normalized in {"email"}:
        return "async"
    return "web"


def sanitize_for_channel(value: Any, channel: str) -> str:
    text = str(value or "")
    if normalize_channel(channel) == "telegram":
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return text


def format_channel_heading(value: Any, channel: str) -> str:
    text = sanitize_for_channel(value, channel)
    if normalize_channel(channel) == "telegram":
        return f"<b>{text}</b>"
    if normalize_channel(channel) in {"whatsapp", "instagram"}:
        return f"*{text}*"
    return text


def get_bullet_style(channel: str) -> Dict[str, Any]:
    normalized = normalize_channel(channel)
    if normalized in {"whatsapp", "instagram", "telegram"}:
        return {
            "header": lambda text: format_channel_heading(text, normalized),
            "bullet": "• ",
            "sub_bullet": "  ◦ ",
            "item_bullet": "    ▪ ",
        }
    return {
        "header": lambda text: format_channel_heading(text, normalized),
        "bullet": "- ",
        "sub_bullet": "  - ",
        "item_bullet": "    - ",
    }


def build_channel_capabilities(channel: str) -> Dict[str, Any]:
    normalized = normalize_channel(channel)
    family = get_channel_family(normalized)
    return {
        "channel": normalized,
        "family": family,
        "supports_rich_cards": normalized in {"web"},
        "supports_compact_cards": family == "chat",
        "supports_markdown_heading": normalized in {"whatsapp", "instagram"},
        "supports_html_escape": normalized in {"telegram"},
    }
