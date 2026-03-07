from __future__ import annotations

from typing import Any, Callable, Dict, List

from .channel_presenter import format_channel_heading, sanitize_for_channel
from .confirmation_presenter import WorkflowDisplayOption


def build_item_selection_prompt(
    option: WorkflowDisplayOption,
    selection: Dict[str, Any],
    *,
    format_project_status_label: Callable[[Any], str],
    format_date_br: Callable[[Any], str],
    channel: str = "web",
) -> str:
    choices = selection.get("choices") or []
    scope_label = selection.get("scope_label") or "empresa ativa"
    item_label_plural = selection.get("item_label_plural") or "itens"
    selection_kind = str(selection.get("selection_kind") or "").strip().lower()
    article = "os"
    if item_label_plural.strip().lower() in {"atividades", "instancias de processo", "reunioes"}:
        article = "as"

    if not choices:
        if selection_kind == "project_picker":
            return (
                "Nao encontrei projetos ativos no contexto atual.\n"
                "Se preferir, informe o codigo diretamente no formato codigo_projeto: AA.J.12."
            )
        return (
            f"Nao encontrei {item_label_plural} em aberto no contexto atual.\n"
            "Se quiser, informe o codigo diretamente no formato campo: valor."
        )

    action = str(option.action_key or "").strip().lower()
    header = format_channel_heading(f"{option.code} - {option.title}", channel)
    if selection_kind == "project_picker":
        lines = [
            header,
            "",
            f"Escolha o projeto ativo para a {sanitize_for_channel(scope_label, channel)}:",
        ]
        for item in choices:
            code = item.get("code") or "-"
            title = item.get("title") or "-"
            status = format_project_status_label(item.get("status"))
            due_str = format_date_br(item.get("due_date"))
            progress = item.get("progress")
            detail_parts = [f"Status: {status}"]
            if progress is not None:
                detail_parts.append(f"Progresso: {progress}%")
            detail_parts.append(f"Prazo: {due_str}")
            lines.append(
                f"{item['index']} - {sanitize_for_channel(code, channel)} - "
                f"{sanitize_for_channel(title, channel)} | {sanitize_for_channel(' | '.join(detail_parts), channel)}"
            )
        lines.append("")
        lines.append("Informe apenas o numero do projeto.")
        lines.append("Exemplo: 1")
        lines.append("Se preferir, envie o codigo diretamente no formato codigo_projeto: AA.J.12")
        return "\n".join(lines)

    if action == "onboarding.diagnose":
        lines = [
            header,
            "",
            "Selecione o objetivo do diagnostico:",
        ]
        for item in choices:
            lines.append(f"{item['index']} - {sanitize_for_channel(item.get('title') or item.get('code') or '-', channel)}")
        lines.append("")
        lines.append("Informe o numero da opcao.")
        lines.append("Exemplo: 1")
        return "\n".join(lines)

    if action in {"meeting.start", "meeting.summarize"}:
        lines = [
            header,
            "",
            f"Existem {article} seguintes {sanitize_for_channel(item_label_plural, channel)} disponiveis para a {sanitize_for_channel(scope_label, channel)}:",
        ]
    else:
        lines = [
            header,
            "",
            f"Existem {article} seguintes {sanitize_for_channel(item_label_plural, channel)} em aberto para a {sanitize_for_channel(scope_label, channel)}:",
        ]
    for item in choices:
        code = item.get("code") or "-"
        title = item.get("title") or "-"
        if action in {"meeting.start", "meeting.summarize"}:
            status = item.get("status") or "-"
            when = f"{item.get('scheduled_date') or '-'} {item.get('scheduled_time') or ''}".strip()
            lines.append(
                f"{item['index']} - ID {sanitize_for_channel(code, channel)} - "
                f"{sanitize_for_channel(title, channel)} | Status: {sanitize_for_channel(status, channel)} | "
                f"Data: {sanitize_for_channel(when, channel)}"
            )
        else:
            due_str = item.get("due_date") or "-"
            detail = item.get("project_name") or item.get("process_code") or ""
            if detail:
                lines.append(
                    f"{item['index']} - {sanitize_for_channel(code, channel)} - {sanitize_for_channel(title, channel)} | "
                    f"{sanitize_for_channel(detail, channel)} | Prazo: {sanitize_for_channel(due_str, channel)}"
                )
            else:
                lines.append(
                    f"{item['index']} - {sanitize_for_channel(code, channel)} - {sanitize_for_channel(title, channel)} | "
                    f"Prazo: {sanitize_for_channel(due_str, channel)}"
                )

    lines.append("")
    if action in {"meeting.start", "meeting.summarize"}:
        lines.append("Informe o numero da reuniao no formato:")
        lines.append("numero")
        lines.append("Exemplo: 1")
    else:
        lines.append(
            "Informe o numero da atividade / instancia e a data que voce quer registrar como finalizacao, no formato:"
        )
        lines.append("numero: data")
        lines.append("Exemplo: 1: 27/02/2026")
        lines.append("Se quiser usar a data de hoje, envie apenas o numero. Exemplo: 1")
    return "\n".join(lines)
