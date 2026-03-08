from __future__ import annotations

from .chat_contract import ChatMessageBlock
from .conversation_presenter import build_chat_contract_message, build_status_callout


def build_recovery_message(
    title: str,
    message: str,
    *,
    channel: str = "web",
    next_steps: list[str] | None = None,
) -> str:
    blocks = [ChatMessageBlock(kind="status", text=build_status_callout("warning", message, channel=channel))]
    if next_steps:
        blocks.append(ChatMessageBlock(kind="next_step", items=list(next_steps)))
    return build_chat_contract_message(title, blocks=blocks, channel=channel)


def build_internal_error_message(*, channel: str = "web") -> str:
    return build_chat_contract_message(
        "Nao foi possivel concluir a solicitacao",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout("danger", "Ocorreu um erro interno e o time de engenharia foi notificado.", channel=channel),
            ),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Tente novamente em alguns segundos.",
                    "Se o problema persistir, envie a ultima mensagem novamente com mais contexto.",
                ],
            ),
        ],
    )


def build_menu_recovery_message(*, channel: str = "web") -> str:
    return build_recovery_message(
        "Nao consegui abrir o menu agora",
        "O menu nao ficou disponivel neste momento.",
        channel=channel,
        next_steps=[
            "Tente novamente em alguns segundos.",
            "Se preferir, responda apenas com 'menu'.",
        ],
    )
