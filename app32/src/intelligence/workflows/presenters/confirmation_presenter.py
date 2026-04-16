from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from .chat_contract import ChatMessageBlock, make_list_block
from .conversation_presenter import build_chat_contract_message, build_status_callout


class WorkflowDisplayOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    action_key: Optional[str] = None
    description: Optional[str] = None


def build_workflow_selection_confirmation(
    option: WorkflowDisplayOption,
    *,
    user_name: str | None = None,
    channel: str = "web",
) -> str:
    greeting = f"Ola, {str(user_name or 'usuario').strip()}!" if str(user_name or "").strip() else "Ola!"
    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(kind="body", text=greeting),
        ChatMessageBlock(kind="body", text="Entendi melhor o seu pedido e selecionei o fluxo mais adequado para continuar."),
        ChatMessageBlock(kind="heading", text=f"Fluxo/Tool sugerido: {option.code} - {option.title}"),
    ]

    if option.description:
        blocks.append(ChatMessageBlock(kind="body", text=f"Descricao: {option.description}"))

    blocks.extend(
        [
            ChatMessageBlock(kind="status", text=build_status_callout("info", "Se estiver certo, eu sigo com os dados da sessao e pergunto apenas o que faltar.", channel=channel)),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Responda 'sim' para continuar.",
                    "Responda 'nao' para cancelar.",
                    "Se quiser, descreva em uma frase curta o ajuste necessario.",
                ],
            ),
        ]
    )

    return build_chat_contract_message(
        "Confirmacao do fluxo",
        subtitle="Validacao explicita antes da coleta e execucao controlada.",
        blocks=blocks,
        channel=channel,
    )


def build_confirmation_text(
    option: WorkflowDisplayOption,
    payload: Dict[str, Any],
    *,
    format_project_choice_line: Callable[[str], Optional[str]],
    format_project_task_choice_line: Callable[[str], Optional[str]],
    format_process_instance_choice_line: Callable[[str], Optional[str]],
    format_meeting_choice_line: Callable[[str], Optional[str]],
    format_objective_label: Callable[[str], str],
    channel: str = "web",
) -> str:
    consolidated_items = build_confirmation_display_items(
        option,
        payload,
        format_project_choice_line=format_project_choice_line,
        format_project_task_choice_line=format_project_task_choice_line,
        format_process_instance_choice_line=format_process_instance_choice_line,
        format_meeting_choice_line=format_meeting_choice_line,
        format_objective_label=format_objective_label,
    )

    blocks: List[ChatMessageBlock] = [
        ChatMessageBlock(kind="heading", text=f"Fluxo selecionado: {option.code} - {option.title}"),
        ChatMessageBlock(kind="body", text="Confirme que voce quer:"),
        ChatMessageBlock(kind="status", text=build_status_callout("info", "Revise os dados antes de executar.", channel=channel)),
    ]

    if consolidated_items:
        blocks.append(ChatMessageBlock(kind="body", text="Dados consolidados:"))
        blocks.append(make_list_block([f"• item: {item}" for item in consolidated_items]))
    else:
        blocks.append(ChatMessageBlock(kind="body", text="Nenhum dado adicional foi informado."))

    blocks.append(
        ChatMessageBlock(
            kind="next_step",
            items=[
                "Responda 'sim' para executar agora.",
                "Responda 'nao' para cancelar com seguranca.",
            ],
        )
    )
    blocks.append(
        ChatMessageBlock(
            kind="body",
            text="Se precisar ajustar algum dado, descreva a alteracao em uma frase curta.",
        )
    )

    return build_chat_contract_message("Confirme a operacao", blocks=blocks, channel=channel)


def build_confirmation_display_items(
    option: WorkflowDisplayOption,
    payload: Dict[str, Any],
    *,
    format_project_choice_line: Callable[[str], Optional[str]],
    format_project_task_choice_line: Callable[[str], Optional[str]],
    format_process_instance_choice_line: Callable[[str], Optional[str]],
    format_meeting_choice_line: Callable[[str], Optional[str]],
    format_objective_label: Callable[[str], str],
) -> List[str]:
    action = str(option.action_key or "").strip().lower()
    items: List[str] = []

    if action in {"project.update", "project.complete", "project_task.create"}:
        project_code = str(payload.get("codigo_projeto") or "").strip()
        if project_code:
            pretty = format_project_choice_line(project_code)
            items.append(pretty or f"codigo_projeto: {project_code}")

        for key, value in payload.items():
            if key == "codigo_projeto":
                continue
            items.append(f"{key}: {value}")
        return items

    if action == "project_task.complete":
        activity_code = str(payload.get("codigo_atividade") or "").strip()
        if activity_code:
            pretty = format_project_task_choice_line(activity_code)
            items.append(pretty or f"codigo_atividade: {activity_code}")

        if payload.get("data_finalizacao"):
            items.append(f"data_finalizacao: {payload['data_finalizacao']}")

        for key, value in payload.items():
            if key in {"codigo_atividade", "data_finalizacao"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action == "process_instance.complete":
        instance_code = str(payload.get("codigo_instancia") or "").strip()
        if instance_code:
            pretty = format_process_instance_choice_line(instance_code)
            items.append(pretty or f"codigo_instancia: {instance_code}")

        if payload.get("data_finalizacao"):
            items.append(f"data_finalizacao: {payload['data_finalizacao']}")

        for key, value in payload.items():
            if key in {"codigo_instancia", "data_finalizacao"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action in {"meeting.start", "meeting.summarize", "meeting.close", "meeting.send_summary_email", "meeting.send_summary_whatsapp"}:
        meeting_value = str(
            payload.get("id_reuniao")
            or payload.get("meeting_id")
            or payload.get("codigo_reuniao")
            or payload.get("codigo")
            or ""
        ).strip()
        if meeting_value:
            pretty = format_meeting_choice_line(meeting_value)
            items.append(pretty or f"id_reuniao: {meeting_value}")

        for key, value in payload.items():
            if key in {"id_reuniao", "meeting_id", "codigo_reuniao", "codigo"}:
                continue
            items.append(f"{key}: {value}")
        return items

    if action == "onboarding.diagnose":
        objective_raw = str(
            payload.get("objetivo")
            or payload.get("o_que_quer_funcionar")
            or payload.get("objetivo_de_funcionamento")
            or ""
        ).strip()
        if objective_raw:
            items.append(f"objetivo: {format_objective_label(objective_raw)}")

        for key, value in payload.items():
            if key in {"objetivo", "o_que_quer_funcionar", "objetivo_de_funcionamento"}:
                continue
            items.append(f"{key}: {value}")
        return items

    for key, value in payload.items():
        items.append(f"{key}: {value}")
    return items
