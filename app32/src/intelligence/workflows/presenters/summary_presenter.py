from __future__ import annotations

from typing import Any, Dict, List

from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_guidance_block, build_next_step_block, build_presenter_header, build_status_callout
from .channel_presenter import sanitize_for_channel


def build_summary_period_prompt(option: WorkflowDisplayOption, *, channel: str = "web") -> str:
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Configure o periodo personalizado do resumo.",
        channel=channel,
    )
    lines.extend([
        "",
        build_status_callout("info", "Informe a data inicial e final do periodo desejado.", channel=channel),
        "",
        *build_next_step_block(
            "Formato: DD/MM/AAAA a DD/MM/AAAA",
            "Exemplo: 01/03/2026 a 31/03/2026",
            channel=channel,
        ),
    ])
    return "\n".join(lines)


def build_summary_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Escolha a empresa para consolidar o resumo.",
        channel=channel,
    )
    lines.extend(["", build_status_callout("info", "Selecione apenas uma empresa para seguir.", channel=channel), ""])
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.extend(["", *build_next_step_block("Responda apenas com o numero da empresa. Exemplo: 1", channel=channel)])
    return "\n".join(lines)


def build_summary_collaborator_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Defina o escopo dos colaboradores que entrarao no resumo.",
        channel=channel,
    )
    lines.extend(["", build_status_callout("info", "Voce pode escolher todos ou uma combinacao especifica.", channel=channel), ""])
    lines.append("0 - Todos os colaboradores")
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.extend(["", *build_next_step_block("Responda com 0 (todos), um numero (ex: 1) ou varios (ex: 1,3,4).", channel=channel)])
    return "\n".join(lines)


def build_summary_status_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Escolha o recorte operacional do resumo.",
        channel=channel,
    )
    lines.extend(["", build_status_callout("info", "O status define quais itens entrarao na consolidacao final.", channel=channel), ""])
    for item in choices or []:
        lines.append(f"{item['index']} - {sanitize_for_channel(item['label'], channel)}")
    lines.extend(["", *build_next_step_block("Responda apenas com o numero do status. Exemplo: 1", channel=channel)])
    return "\n".join(lines)
