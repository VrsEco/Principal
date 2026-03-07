from __future__ import annotations

from typing import Any, Dict, List

from .channel_presenter import format_channel_heading, sanitize_for_channel
from .confirmation_presenter import WorkflowDisplayOption


def build_operation_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = [format_channel_heading(f"{option.code} - {option.title}", channel), "", "Escolha a empresa para continuar:"]
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.append("")
    lines.append("Responda apenas com o numero da empresa. Exemplo: 1")
    return "\n".join(lines)
