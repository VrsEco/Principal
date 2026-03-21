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
    channel: str = "web",
) -> str:
    fields = WorkflowRequiredField.normalize_many(missing_fields)
    action = str(option.action_key or "").strip().lower()

    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(kind="status", text=build_status_callout("warning", "Preencha somente o que ainda estiver pendente.", channel=channel)),
        ChatMessageBlock(kind="body", text=f"Voce quer fazer {option.code} - {option.title}."),
        ChatMessageBlock(kind="body", text="Para executar, faltam os seguintes dados:"),
    ]

    if fields:
        blocks.append(
            make_list_block([f"{idx} - {field.label} ({field.key})" for idx, field in enumerate(fields, start=1)])
        )

    visible_payload = [f"{key}: {value}" for key, value in payload.items() if not str(key).startswith("_")]
    if visible_payload:
        blocks.append(ChatMessageBlock(kind="body", text="Dados ja recebidos:"))
        blocks.append(make_list_block([f"- {item}" for item in visible_payload]))

    next_steps = [
        "Envie no formato: numero: valor",
        "Exemplo geral: 1: valor",
    ]
    if action == "onboarding.start":
        next_steps.extend([
            "Exemplos aceitos: 1: real",
            "Exemplos aceitos: 1: modelo",
        ])

    blocks.append(ChatMessageBlock(kind="next_step", items=next_steps))

    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Faltam alguns parametros para concluir a solicitacao.",
        blocks=blocks,
        channel=channel,
    )
