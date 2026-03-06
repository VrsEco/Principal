from __future__ import annotations

from typing import Any, Dict, List

from .confirmation_presenter import WorkflowDisplayOption
from ..schemas.field_collection import WorkflowRequiredField


def build_missing_fields_prompt(
    option: WorkflowDisplayOption,
    missing_fields: List[Dict[str, Any]],
    payload: Dict[str, Any],
) -> str:
    fields = WorkflowRequiredField.normalize_many(missing_fields)
    action = str(option.action_key or "").strip().lower()
    lines = [
        f"Voce quer fazer {option.code} - {option.title}.",
        "Para executar, faltam os seguintes dados:",
    ]
    for idx, field in enumerate(fields, start=1):
        lines.append(f"{idx} - {field.label} ({field.key})")
    if payload:
        lines.append("")
        lines.append("Dados ja recebidos:")
        for key, value in payload.items():
            if str(key).startswith("_"):
                continue
            lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Envie no formato: numero: valor")
    if action == "onboarding.start":
        lines.append("Exemplos:")
        lines.append("1: real")
        lines.append("1: modelo")
    return "\n".join(lines)
