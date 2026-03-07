from __future__ import annotations

from typing import Any, Callable, Dict


def normalize_channel(channel: str) -> str:
    return str(channel or "web").strip().lower() or "web"


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
    if normalize_channel(channel) == "whatsapp":
        return f"*{text}*"
    return text


def get_bullet_style(channel: str) -> Dict[str, Any]:
    normalized = normalize_channel(channel)
    if normalized == "whatsapp":
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
