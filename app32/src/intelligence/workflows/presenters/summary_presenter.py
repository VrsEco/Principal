from __future__ import annotations

from typing import Any, Dict, List

from .chat_contract import ChatMessageBlock, make_list_block
from .confirmation_presenter import WorkflowDisplayOption
from .conversation_presenter import build_chat_contract_message, build_status_callout


def build_summary_period_prompt(option: WorkflowDisplayOption, *, channel: str = "web") -> str:
    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Configure o periodo personalizado do resumo.",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("info", "Informe a data inicial e final do periodo desejado.", channel=channel),
            ),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Formato: DD/MM/AAAA a DD/MM/AAAA",
                    "Exemplo: 01/03/2026 a 31/03/2026",
                ],
            ),
        ],
    )


def build_summary_company_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(
            kind="status",
            text=build_status_callout("info", "Selecione apenas uma empresa para seguir.", channel=channel),
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
        subtitle="Escolha a empresa para consolidar o resumo.",
        channel=channel,
        blocks=blocks,
    )


def build_summary_collaborator_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    items = ["0 - Todos os colaboradores"]
    items.extend(f"{item['index']} - {item['label']}" for item in (choices or []))
    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Defina o escopo dos colaboradores que entrarao no resumo.",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("info", "Voce pode escolher todos ou uma combinacao especifica.", channel=channel),
            ),
            make_list_block(items),
            ChatMessageBlock(
                kind="next_step",
                items=["Responda com 0 (todos), um numero (ex: 1) ou varios (ex: 1,3,4)."],
            ),
        ],
    )


def build_summary_status_prompt(
    option: WorkflowDisplayOption,
    choices: List[Dict[str, Any]],
    *,
    channel: str = "web",
) -> str:
    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(
            kind="status",
            text=build_status_callout("info", "O status define quais itens entrarao na consolidacao final.", channel=channel),
        ),
    ]
    if choices:
        blocks.append(make_list_block([f"{item['index']} - {item['label']}" for item in choices]))
    blocks.append(
        ChatMessageBlock(
            kind="next_step",
            items=["Responda apenas com o numero do status. Exemplo: 1"],
        )
    )
    return build_chat_contract_message(
        f"{option.code} - {option.title}",
        subtitle="Escolha o recorte operacional do resumo.",
        channel=channel,
        blocks=blocks,
    )
