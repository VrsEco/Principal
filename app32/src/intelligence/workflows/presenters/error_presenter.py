from __future__ import annotations

from .conversation_presenter import build_guidance_block, build_next_step_block, build_presenter_header, build_status_callout


def build_recovery_message(
    title: str,
    message: str,
    *,
    channel: str = "web",
    next_steps: list[str] | None = None,
) -> str:
    lines = build_presenter_header(title, channel=channel)
    lines.extend(["", build_status_callout("warning", message, channel=channel)])
    if next_steps:
        lines.extend(["", *build_next_step_block(*next_steps, channel=channel)])
    return "\n".join(lines)


def build_internal_error_message(*, channel: str = "web") -> str:
    lines = build_presenter_header("Nao foi possivel concluir a solicitacao", channel=channel)
    lines.extend(["", build_status_callout("danger", "Ocorreu um erro interno e o time de engenharia foi notificado.", channel=channel)])
    lines.extend(["", *build_next_step_block("Tente novamente em alguns segundos.", "Se o problema persistir, envie a ultima mensagem novamente com mais contexto.", channel=channel)])
    return "\n".join(lines)


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
