from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class WorkflowDisplayOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    action_key: Optional[str] = None


def build_confirmation_text(
    option: WorkflowDisplayOption,
    payload: Dict[str, Any],
    *,
    format_project_choice_line: Callable[[str], Optional[str]],
    format_project_task_choice_line: Callable[[str], Optional[str]],
    format_process_instance_choice_line: Callable[[str], Optional[str]],
    format_meeting_choice_line: Callable[[str], Optional[str]],
    format_objective_label: Callable[[str], str],
) -> str:
    lines = [
        "Confirme que voce quer:",
        f"{option.code} - {option.title}",
    ]
    if payload:
        lines.append("com os dados:")
        for item in build_confirmation_display_items(
            option,
            payload,
            format_project_choice_line=format_project_choice_line,
            format_project_task_choice_line=format_project_task_choice_line,
            format_process_instance_choice_line=format_process_instance_choice_line,
            format_meeting_choice_line=format_meeting_choice_line,
            format_objective_label=format_objective_label,
        ):
            lines.append(f"- {item}")
    else:
        lines.append("sem dados adicionais.")
    lines.append("Se estiver correto, responda 'sim'. Para cancelar, responda 'nao'.")
    return "\n".join(lines)


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

    if action in {"meeting.start", "meeting.summarize"}:
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
