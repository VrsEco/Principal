from __future__ import annotations

from typing import Any, Callable, Dict, List

from .channel_presenter import sanitize_for_channel
from .chat_contract import ChatMessageBlock, make_list_block
from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_chat_contract_message, build_status_callout


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

    if selection_kind == "project_picker":
        blocks: List[ChatMessageBlock] = [
            ChatMessageBlock(kind="status", text=build_status_callout("info", "Selecione um unico projeto para continuar.", channel=channel)),
            make_list_block([
                (
                    f"{item['index']} - {sanitize_for_channel(item.get('code') or '-', channel)} - "
                    f"{sanitize_for_channel(item.get('title') or '-', channel)} | "
                    f"{sanitize_for_channel(' | '.join(_project_detail_parts(item, format_project_status_label, format_date_br)), channel)}"
                )
                for item in choices
            ]),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Informe apenas o numero do projeto.",
                    "Exemplo: 1",
                    "Se preferir, envie o codigo diretamente no formato codigo_projeto: AA.J.12",
                ],
            ),
        ]
        return build_chat_contract_message(
            f"{option.code} - {option.title}",
            subtitle=f"Escolha o projeto ativo para a {scope_label}.",
            blocks=blocks,
            channel=channel,
        )

    if action == "onboarding.diagnose":
        blocks = [
            ChatMessageBlock(kind="status", text=build_status_callout("info", "O objetivo ajuda a orientar a analise dos agentes.", channel=channel)),
            make_list_block([
                f"{item['index']} - {sanitize_for_channel(item.get('title') or item.get('code') or '-', channel)}"
                for item in choices
            ]),
            ChatMessageBlock(kind="next_step", items=["Informe o numero da opcao.", "Exemplo: 1"]),
        ]
        return build_chat_contract_message(
            f"{option.code} - {option.title}",
            subtitle="Selecione o objetivo do diagnostico.",
            blocks=blocks,
            channel=channel,
        )

    description = (
        f"Existem {article} seguintes {item_label_plural} disponiveis para a {scope_label}."
        if action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}
        else f"Existem {article} seguintes {item_label_plural} em aberto para a {scope_label}."
    )
    blocks = [
        ChatMessageBlock(kind="status", text=build_status_callout("info", "Escolha o item correto para evitar execucao sobre o registro errado.", channel=channel)),
        make_list_block([_build_generic_choice_line(item, action, channel) for item in choices]),
    ]
    if action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}:
        blocks.append(ChatMessageBlock(kind="next_step", items=["Informe o numero da reuniao.", "Exemplo: 1"]))
    else:
        blocks.append(
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Informe o numero da atividade / instancia e a data que voce quer registrar como finalizacao.",
                    "Formato: numero: data",
                    "Exemplo: 1: 27/02/2026",
                    "Se quiser usar a data de hoje, envie apenas o numero. Exemplo: 1",
                ],
            )
        )

    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle=description,
        blocks=blocks,
        channel=channel,
    )


def _project_detail_parts(item: Dict[str, Any], format_project_status_label: Callable[[Any], str], format_date_br: Callable[[Any], str]) -> List[str]:
    status = format_project_status_label(item.get("status"))
    due_str = format_date_br(item.get("due_date"))
    progress = item.get("progress")
    detail_parts = [f"Status: {status}"]
    if progress is not None:
        detail_parts.append(f"Progresso: {progress}%")
    detail_parts.append(f"Prazo: {due_str}")
    return detail_parts


def _build_generic_choice_line(item: Dict[str, Any], action: str, channel: str) -> str:
    code = item.get("code") or "-"
    title = item.get("title") or "-"
    if action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}:
        status = item.get("status") or "-"
        when = f"{item.get('scheduled_date') or '-'} {item.get('scheduled_time') or ''}".strip()
        return (
            f"{item['index']} - ID {sanitize_for_channel(code, channel)} - "
            f"{sanitize_for_channel(title, channel)} | Status: {sanitize_for_channel(status, channel)} | "
            f"Data: {sanitize_for_channel(when, channel)}"
        )

    due_str = item.get("due_date") or "-"
    detail = item.get("project_name") or item.get("process_code") or ""
    if detail:
        return (
            f"{item['index']} - {sanitize_for_channel(code, channel)} - {sanitize_for_channel(title, channel)} | "
            f"{sanitize_for_channel(detail, channel)} | Prazo: {sanitize_for_channel(due_str, channel)}"
        )
    return (
        f"{item['index']} - {sanitize_for_channel(code, channel)} - {sanitize_for_channel(title, channel)} | "
        f"Prazo: {sanitize_for_channel(due_str, channel)}"
    )
