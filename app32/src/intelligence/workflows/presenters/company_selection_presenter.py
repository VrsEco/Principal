from __future__ import annotations

from typing import Any, Dict, List

from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_guidance_block, build_presenter_header, build_status_callout
from .channel_presenter import sanitize_for_channel


def build_operation_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Escolha a empresa para continuar:",
        channel=channel,
    )
    lines.extend(["", build_status_callout("info", "Esse passo garante multi-tenancy correta antes da execucao.", channel=channel), ""])
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.extend(["", *build_guidance_block("Responda apenas com o numero da empresa. Exemplo: 1", channel=channel)])
    return "\n".join(lines)
