from __future__ import annotations

from typing import Any, Dict, List

from .confirmation_presenter import WorkflowDisplayOption


def build_operation_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
) -> str:
    lines = [f"{option.code} - {option.title}", "", "Escolha a empresa para continuar:"]
    for item in choices or []:
        lines.append(f"{item['index']} - {item['label']}")
    lines.append("")
    lines.append("Responda apenas com o numero da empresa. Exemplo: 1")
    return "\n".join(lines)
