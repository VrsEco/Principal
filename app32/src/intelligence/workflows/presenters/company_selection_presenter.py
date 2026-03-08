from __future__ import annotations

from typing import Any, Dict, List

from .chat_contract import ChatMessageBlock, make_list_block
from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_chat_contract_message, build_status_callout


def build_operation_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(
            kind="status",
            text=build_status_callout("info", "Esse passo garante multi-tenancy correta antes da execucao.", channel=channel),
        ),
    ]
    if choices:
        blocks.append(make_list_block([f"{item['index']} - {item['label']}" for item in choices]))
    blocks.append(
        ChatMessageBlock(
            kind="next_step",
            items=["Responda apenas com o numero da empresa. Exemplo: 1"],
        )
    )
    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Escolha a empresa para continuar:",
        channel=channel,
        blocks=blocks,
    )
