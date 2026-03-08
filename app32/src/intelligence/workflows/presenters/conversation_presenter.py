from __future__ import annotations

from typing import Any, Iterable, List

from .channel_presenter import format_channel_heading, get_bullet_style, sanitize_for_channel
from .chat_contract import ChatMessageBlock, ChatMessageContract, render_chat_message


def build_presenter_header(title: str, subtitle: str | None = None, *, channel: str = "web") -> List[str]:
    lines = [format_channel_heading(title, channel)]
    if subtitle:
        lines.extend(["", sanitize_for_channel(subtitle, channel)])
    return lines


def build_numbered_options(options: Iterable[str], *, channel: str = "web") -> List[str]:
    lines: List[str] = []
    for idx, option in enumerate(options, start=1):
        lines.append(f"{idx} - {sanitize_for_channel(option, channel)}")
    return lines


def build_key_value_lines(items: Iterable[tuple[str, Any]], *, channel: str = "web") -> List[str]:
    style = get_bullet_style(channel)
    lines: List[str] = []
    for key, value in items:
        lines.append(
            f"{style['bullet']}{sanitize_for_channel(key, channel)}: {sanitize_for_channel(value, channel)}"
        )
    return lines


def build_guidance_block(*lines: str, channel: str = "web") -> List[str]:
    return [sanitize_for_channel(line, channel) for line in lines if str(line or "").strip()]


def build_next_step_block(*lines: str, channel: str = "web") -> List[str]:
    guidance = [line for line in lines if str(line or "").strip()]
    if not guidance:
        return []
    return [
        sanitize_for_channel("Proximo passo:", channel),
        *[f"→ {sanitize_for_channel(line, channel)}" for line in guidance],
    ]


def build_status_callout(kind: str, message: str, *, channel: str = "web") -> str:
    prefix = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "danger": "⛔",
    }.get(str(kind or "info").strip().lower(), "ℹ️")
    return sanitize_for_channel(f"{prefix} {message}", channel)


def build_chat_contract_message(
    title: str,
    *,
    subtitle: str | None = None,
    blocks: list[ChatMessageBlock] | None = None,
    channel: str = "web",
) -> str:
    contract = ChatMessageContract(
        title=title,
        subtitle=subtitle,
        blocks=list(blocks or []),
    )
    return render_chat_message(contract, channel=channel)
