from __future__ import annotations

from typing import Iterable

from .chat_contract import ChatMessageBlock, make_list_block
from .conversation_presenter import build_chat_contract_message, build_status_callout


def build_root_menu_message(options: Iterable[str], *, channel: str = "web") -> str:
    items = [str(option) for option in options if str(option or "").strip()]
    if not items:
        return build_chat_contract_message(
            "Menu principal indisponivel",
            channel=channel,
            blocks=[
                ChatMessageBlock(
                    kind="status",
                    text=build_status_callout("warning", "Nenhuma opcao de menu ativa encontrada.", channel=channel),
                )
            ],
        )

    return build_chat_contract_message(
        "Menu principal",
        subtitle="Selecione uma opcao para continuar.",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("info", "Escolha um fluxo pelo codigo para seguir com seguranca.", channel=channel),
            ),
            make_list_block(items),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Responda com o codigo do fluxo. Exemplo: 1.4",
                    "Se preferir, envie: menu 1.4 executar ...",
                ],
            ),
        ],
    )


def build_submenu_message(title: str, options: Iterable[str], *, channel: str = "web") -> str:
    return build_chat_contract_message(
        title,
        subtitle="Escolha o item desejado dentro deste grupo.",
        channel=channel,
        blocks=[
            make_list_block([str(option) for option in options if str(option or "").strip()]),
            ChatMessageBlock(
                kind="next_step",
                items=["Digite o codigo desejado. Exemplo: menu 1.4 executar"],
            ),
        ],
    )


def build_ambiguous_options_message(options: Iterable[str], *, channel: str = "web") -> str:
    return build_chat_contract_message(
        "Escolha uma opcao",
        subtitle="Nao tive certeza do que voce quer executar.",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("warning", "Existem multiplas opcoes parecidas para este pedido.", channel=channel),
            ),
            make_list_block([str(option) for option in options if str(option or "").strip()]),
            ChatMessageBlock(
                kind="next_step",
                items=["Se preferir, envie: menu CODIGO executar com os dados necessarios."],
            ),
        ],
    )


def build_processing_ack_message(*, channel: str = "web") -> str:
    return build_chat_contract_message(
        "Processando sua solicitacao",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("info", "Estou organizando o contexto e preparando a resposta.", channel=channel),
            )
        ],
    )
