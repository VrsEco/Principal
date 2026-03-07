from __future__ import annotations

from typing import Any, Dict, List

from .channel_presenter import format_channel_heading, sanitize_for_channel
from .confirmation_presenter import WorkflowDisplayOption


def build_summary_period_prompt(option: WorkflowDisplayOption, *, channel: str = "web") -> str:
    return "\n".join(
        [
            format_channel_heading(f"{option.code} - {option.title}", channel),
            "",
            "Informe a data inicial e final do período personalizado.",
            "Formato: DD/MM/AAAA a DD/MM/AAAA",
            "Exemplo: 01/03/2026 a 31/03/2026",
        ]
    )


def build_summary_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = [format_channel_heading(f"{option.code} - {option.title}", channel), "", "Escolha a empresa:"]
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.append("")
    lines.append("Responda apenas com o numero da empresa. Exemplo: 1")
    return "\n".join(lines)


def build_summary_collaborator_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = [format_channel_heading(f"{option.code} - {option.title}", channel), "", "Escolha o colaborador:"]
    lines.append("0 - Todos os colaboradores")
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.append("")
    lines.append("Responda com 0 (todos), um numero (ex: 1) ou varios (ex: 1,3,4).")
    return "\n".join(lines)


def build_summary_status_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = [format_channel_heading(f"{option.code} - {option.title}", channel), "", "Escolha o status:"]
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.append("")
    lines.append("Responda apenas com o numero do status. Exemplo: 1")
    return "\n".join(lines)
