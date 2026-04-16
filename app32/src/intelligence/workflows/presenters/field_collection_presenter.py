from __future__ import annotations

from typing import Any, Dict, List

from .chat_contract import ChatMessageBlock, make_list_block
from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_chat_contract_message, build_status_callout
from ..schemas.field_collection import WorkflowRequiredField


def build_missing_fields_prompt(
    option: WorkflowDisplayOption,
    missing_fields: List[Dict[str, Any]],
    payload: Dict[str, Any],
    *,
    optional_fields: List[Dict[str, Any]] | None = None,
    complementary_fields: List[Dict[str, Any]] | None = None,
    auto_filled_fields: List[str] | None = None,
    channel: str = "web",
) -> str:
    fields = WorkflowRequiredField.normalize_many(missing_fields)
    optional = WorkflowRequiredField.normalize_many(optional_fields or [])
    complementary = WorkflowRequiredField.normalize_many(complementary_fields or [])
    action = str(option.action_key or "").strip().lower()
    has_required = bool(fields)

    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(kind="status", text=build_status_callout("warning", "Preencha somente o que ainda estiver pendente.", channel=channel)),
        ChatMessageBlock(kind="body", text=f"Voce quer fazer {option.code} - {option.title}."),
    ]

    if auto_filled_fields:
        blocks.append(ChatMessageBlock(kind="body", text="Dados aproveitados automaticamente da sessao:"))
        blocks.append(make_list_block([f"- {item}" for item in auto_filled_fields]))

    if has_required:
        blocks.append(ChatMessageBlock(kind="body", text="Para executar, faltam os seguintes dados obrigatorios:"))

    next_index = 1

    if fields:
        blocks.append(
            make_list_block([f"{idx} - {field.label} ({field.key})" for idx, field in enumerate(fields, start=next_index)])
        )
        next_index += len(fields)

    if optional:
        blocks.append(ChatMessageBlock(kind="body", text="Campos opcionais que podem melhorar a resposta:"))
        blocks.append(
            make_list_block([f"{idx} - {field.label} ({field.key})" for idx, field in enumerate(optional, start=next_index)])
        )
        next_index += len(optional)

    if complementary:
        blocks.append(ChatMessageBlock(kind="body", text="Campos complementares para dar mais contexto:"))
        blocks.append(
            make_list_block([f"{idx} - {field.label} ({field.key})" for idx, field in enumerate(complementary, start=next_index)])
        )

    visible_payload = [f"{key}: {value}" for key, value in payload.items() if not str(key).startswith("_")]
    if visible_payload:
        blocks.append(ChatMessageBlock(kind="body", text="Dados ja recebidos:"))
        blocks.append(make_list_block([f"- {item}" for item in visible_payload]))

    next_steps = ["Envie no formato: numero: valor"]
    if has_required:
        next_steps.append("Exemplo geral: 1: valor")
    else:
        next_steps.append("Se quiser seguir sem complementar, responda: pular")
    if action == "onboarding.start":
        next_steps.extend([
            "Exemplos aceitos: 1: real",
            "Exemplos aceitos: 1: modelo",
        ])

    blocks.append(ChatMessageBlock(kind="next_step", items=next_steps))

    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Faltam alguns parametros para concluir a solicitacao." if has_required else "Campos adicionais disponiveis antes da execucao.",
        blocks=blocks,
        channel=channel,
    )
