from __future__ import annotations

from typing import Any, Dict, List

from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import (
    build_guidance_block,
    build_next_step_block,
    build_presenter_header,
    build_status_callout,
)
from ..schemas.field_collection import WorkflowRequiredField


def build_missing_fields_prompt(
    option: WorkflowDisplayOption,
    missing_fields: List[Dict[str, Any]],
    payload: Dict[str, Any],
    *,
    channel: str = "web",
) -> str:
    fields = WorkflowRequiredField.normalize_many(missing_fields)
    action = str(option.action_key or "").strip().lower()
    lines = build_presenter_header(
        f"{option.code} - {option.title}",
        "Faltam alguns parametros para concluir a solicitacao.",
        channel=channel,
    )
    lines.extend(["", build_status_callout("warning", "Preencha somente o que ainda estiver pendente.", channel=channel)])
    lines.extend(["", "Para executar, faltam os seguintes dados:", "", "Campos obrigatorios pendentes:"])
    for idx, field in enumerate(fields, start=1):
        lines.append(f"{idx} - {field.label} ({field.key})")
    if payload:
        lines.append("")
        lines.append("Dados ja recebidos:")
        for key, value in payload.items():
            if str(key).startswith("_"):
                continue
            lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        *build_next_step_block(
            "Envie no formato: numero: valor",
            "Exemplo geral: 1: valor",
            channel=channel,
        ),
    ])
    if action == "onboarding.start":
        lines.extend(build_guidance_block("Exemplos:", "1: real", "1: modelo", channel=channel))
    return "\n".join(lines)
