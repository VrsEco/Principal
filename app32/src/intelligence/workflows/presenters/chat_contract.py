from __future__ import annotations

from typing import List, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .channel_presenter import format_channel_heading, sanitize_for_channel

ChatBlockKind = Literal["heading", "subtitle", "status", "body", "list", "next_step"]


class ChatMessageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ChatBlockKind
    text: str | None = None
    items: List[str] = Field(default_factory=list)


class ChatMessageContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    subtitle: str | None = None
    blocks: List[ChatMessageBlock] = Field(default_factory=list)


def render_chat_message(contract: ChatMessageContract, *, channel: str = "web") -> str:
    lines: List[str] = [format_channel_heading(contract.title, channel)]
    if contract.subtitle:
        lines.extend(["", sanitize_for_channel(contract.subtitle, channel)])

    for block in contract.blocks:
        if block.kind == "heading" and block.text:
            lines.extend(["", format_channel_heading(block.text, channel)])
            continue
        if block.kind == "subtitle" and block.text:
            lines.extend(["", sanitize_for_channel(block.text, channel)])
            continue
        if block.kind == "status" and block.text:
            lines.extend(["", sanitize_for_channel(block.text, channel)])
            continue
        if block.kind == "body" and block.text:
            lines.extend(["", sanitize_for_channel(block.text, channel)])
            continue
        if block.kind == "list" and block.items:
            lines.append("")
            lines.extend(sanitize_for_channel(item, channel) for item in block.items if str(item or "").strip())
            continue
        if block.kind == "next_step":
            content = [item for item in block.items if str(item or "").strip()]
            if content:
                lines.extend(["", sanitize_for_channel("Proximo passo:", channel)])
                lines.extend(f"→ {sanitize_for_channel(item, channel)}" for item in content)

    return "\n".join(lines)


def make_list_block(items: Sequence[str]) -> ChatMessageBlock:
    return ChatMessageBlock(kind="list", items=[str(item) for item in items if str(item or "").strip()])
