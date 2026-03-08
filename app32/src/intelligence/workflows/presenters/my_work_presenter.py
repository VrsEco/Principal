from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional

from .channel_presenter import get_bullet_style, sanitize_for_channel
from .conversation_presenter import build_next_step_block, build_presenter_header, build_status_callout


def group_my_work_by_company(
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[int, Dict[str, Any]] = {}

    def _ensure_company(item: Dict[str, Any]) -> Dict[str, Any]:
        cid = int(item.get("company_id") or 0)
        company = grouped.get(cid)
        if company:
            return company

        company = {
            "company_id": cid,
            "company_code": item.get("company_code") or "CP",
            "company_name": item.get("company_name") or f"Empresa {cid}" if cid else "Empresa",
            "projects_map": {},
            "processes_map": {},
            "meetings": [],
        }
        grouped[cid] = company
        return company

    for task in tasks or []:
        company = _ensure_company(task)
        project_code = task.get("project_code") or "SEM-CODIGO"
        project_entry = company["projects_map"].get(project_code)
        if not project_entry:
            project_entry = {
                "project_code": project_code,
                "project_name": task.get("project_name") or "Sem nome",
                "activities": [],
            }
            company["projects_map"][project_code] = project_entry
        project_entry["activities"].append(task)

    for process in processes or []:
        company = _ensure_company(process)
        process_code = process.get("process_code") or "SEM-CODIGO"
        process_entry = company["processes_map"].get(process_code)
        if not process_entry:
            process_entry = {
                "process_code": process_code,
                "process_name": process.get("process_name") or "Sem nome",
                "instances": [],
            }
            company["processes_map"][process_code] = process_entry
        process_entry["instances"].append(process)

    for meeting in meetings or []:
        company = _ensure_company(meeting)
        company["meetings"].append(meeting)

    companies: List[Dict[str, Any]] = []
    for item in grouped.values():
        projects = list(item["projects_map"].values())
        projects.sort(key=lambda project: ((project.get("project_code") or ""), (project.get("project_name") or "")))
        for project in projects:
            project["activities"].sort(
                key=lambda activity: ((activity.get("due_date") or ""), (activity.get("activity_code") or ""))
            )

        process_groups = list(item["processes_map"].values())
        process_groups.sort(key=lambda process: ((process.get("process_code") or ""), (process.get("process_name") or "")))
        for process in process_groups:
            process["instances"].sort(
                key=lambda instance: ((instance.get("due_date") or ""), (instance.get("instance_code") or ""))
            )

        meetings_sorted = sorted(
            item["meetings"],
            key=lambda meeting: (
                (meeting.get("due_date") or ""),
                (meeting.get("scheduled_time") or ""),
                (meeting.get("meeting_code") or ""),
            ),
        )

        companies.append(
            {
                "company_id": item["company_id"],
                "company_code": item["company_code"],
                "company_name": item["company_name"],
                "projects": projects,
                "processes": process_groups,
                "meetings": meetings_sorted,
            }
        )

    companies.sort(key=lambda company: ((company.get("company_code") or ""), (company.get("company_name") or "")))
    return companies


def resolve_my_work_collaborator_label(
    payload: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    fallback_name: str,
) -> str:
    explicit = str(
        payload.get("colaborador")
        or payload.get("colaborador_nome")
        or payload.get("responsavel")
        or payload.get("responsável")
        or ""
    ).strip()
    if explicit:
        explicit_norm = explicit.lower()
        if explicit_norm in {"todos", "todos os colaboradores", "todos colaboradores"}:
            return "de todos os colaboradores"
        if ", " in explicit or " e " in explicit_norm or " e mais " in explicit_norm:
            return f"dos colaboradores {explicit}"
        return f"do colaborador {explicit}"

    names = {
        str(task.get("responsible") or "").strip()
        for task in (tasks or [])
        if str(task.get("responsible") or "").strip()
        and str(task.get("responsible")).strip().lower() != "sem responsavel"
    }
    names.update(
        str(process.get("owner") or "").strip()
        for process in (processes or [])
        if str(process.get("owner") or "").strip()
        and str(process.get("owner")).strip().lower() != "sem dono definido"
    )
    names = {name for name in names if name}

    if not names:
        return f"do colaborador {fallback_name}"

    ordered = sorted(names)
    if len(ordered) == 1:
        return f"do colaborador {ordered[0]}"
    if len(ordered) == 2:
        return f"dos colaboradores {ordered[0]} e {ordered[1]}"
    return f"dos colaboradores {', '.join(ordered[:3])}"


def describe_my_work_period(
    action: str,
    start_date: Optional[date],
    end_date: Optional[date],
    *,
    today: date,
    format_date_br: Callable[[Any], str],
) -> str:
    if action == "my_work.open":
        return "em aberto"
    if action == "my_work.overdue":
        return "atrasadas"
    if action == "my_work.completed_range":
        return (
            f"concluidas no periodo de {format_date_br(start_date)} a {format_date_br(end_date)}"
            if start_date and end_date
            else "concluidas no periodo informado"
        )
    if action != "my_work.due_range" or not start_date or not end_date:
        return "com vencimento no periodo informado"

    if start_date == today and end_date == today:
        return f"vencendo hoje ({format_date_br(today)})"

    if start_date == today:
        if end_date == today + timedelta(days=6):
            return f"vencendo nesta semana ({format_date_br(start_date)} a {format_date_br(end_date)})"
        if end_date == today + timedelta(days=14):
            return f"vencendo nos proximos 15 dias ({format_date_br(start_date)} a {format_date_br(end_date)})"
        first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_day_next_month - timedelta(days=1)
        if end_date == end_of_month:
            return f"com vencimento neste mes ({format_date_br(start_date)} a {format_date_br(end_date)})"

    return f"com vencimento no periodo de {format_date_br(start_date)} a {format_date_br(end_date)}"


def summarize_my_work_totals(
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
) -> Dict[str, int]:
    return {
        "tasks": len(tasks or []),
        "processes": len(processes or []),
        "meetings": len(meetings or []),
        "total": len(tasks or []) + len(processes or []) + len(meetings or []),
    }


def build_my_work_summary_lines(
    *,
    totals: Dict[str, int],
    channel: str,
) -> List[str]:
    style = get_bullet_style(channel)
    total_text = sanitize_for_channel(f"Total de itens: {totals['total']}", channel)
    tasks_text = sanitize_for_channel(f"Atividades: {totals['tasks']}", channel)
    processes_text = sanitize_for_channel(f"Instancias de processo: {totals['processes']}", channel)
    meetings_text = sanitize_for_channel(f"Reunioes: {totals['meetings']}", channel)
    return [
        style["header"]("Painel Executivo"),
        f"{style['bullet']}{total_text}",
        f"{style['bullet']}{tasks_text}",
        f"{style['bullet']}{processes_text}",
        f"{style['bullet']}{meetings_text}",
    ]


def build_my_work_empty_report(*, title: str, channel: str) -> str:
    lines = build_presenter_header(title, channel=channel)
    lines.extend(["", build_status_callout("info", "Nenhum item encontrado para o filtro informado.", channel=channel)])
    lines.extend([
        "",
        *build_next_step_block(
            "Ajuste o filtro de empresa, periodo ou colaborador.",
            "Se preferir, solicite um novo recorte com outro periodo.",
            channel=channel,
        ),
    ])
    return "\n".join(lines)


def build_my_work_report(
    *,
    action: str,
    company_label: str,
    tasks: List[Dict[str, Any]],
    processes: List[Dict[str, Any]],
    meetings: List[Dict[str, Any]],
    start_date: Optional[date],
    end_date: Optional[date],
    channel: str,
    payload: Dict[str, Any],
    manager_name: str,
    reference_date: date,
    format_date_br: Callable[[Any], str],
) -> str:
    style = get_bullet_style(channel)
    base_date = format_date_br(reference_date)
    period_label = describe_my_work_period(
        action=action,
        start_date=start_date,
        end_date=end_date,
        today=reference_date,
        format_date_br=format_date_br,
    )
    collaborator_label = resolve_my_work_collaborator_label(
        payload=payload,
        tasks=tasks,
        processes=processes,
        fallback_name=manager_name,
    )
    normalized_company_label = str(company_label or "").strip().lower()
    company_phrase = (
        company_label
        if normalized_company_label.startswith("empresa") or normalized_company_label.startswith("empresas")
        else f"empresa {company_label}"
    )
    manager_name_norm = manager_name.strip().lower()
    collaborator_label_norm = collaborator_label.strip().lower()
    if collaborator_label_norm == f"do colaborador {manager_name_norm}":
        collaborator_label = "do seu contexto de atuação"

    title = (
        f"Resumo das atividades {period_label} nas {company_phrase}, "
        f"{collaborator_label}, com referência em {base_date}."
    )

    company_groups = group_my_work_by_company(tasks=tasks, processes=processes, meetings=meetings)
    if not company_groups:
        return build_my_work_empty_report(title=title, channel=channel)

    totals = summarize_my_work_totals(tasks, processes, meetings)
    date_name = "Conclusao" if action == "my_work.completed_range" else "Prazo"
    lines = build_presenter_header(title, channel=channel)
    lines.extend(["", build_status_callout("success", "Consolidacao pronta para acompanhamento operacional.", channel=channel), ""])
    lines.extend(build_my_work_summary_lines(totals=totals, channel=channel))
    lines.extend([
        "",
        *build_next_step_block(
            "Revise primeiro os totais executivos abaixo.",
            "Depois aprofunde por empresa, projeto, processo ou reuniao.",
            channel=channel,
        ),
    ])

    for group_index, company in enumerate(company_groups):
        if group_index >= 0:
            lines.append("")

        company_code = company.get("company_code") or "CP"
        company_name = company.get("company_name") or "Empresa"
        company_totals = summarize_my_work_totals(
            [activity for project in company.get("projects") or [] for activity in project.get("activities") or []],
            [instance for process in company.get("processes") or [] for instance in process.get("instances") or []],
            company.get("meetings") or [],
        )
        lines.append(style["header"]("Empresa"))
        lines.append(f"{style['bullet']}{sanitize_for_channel(f'{company_code} - {company_name}', channel)}")
        company_total_text = sanitize_for_channel(f"Total de itens: {company_totals['total']}", channel)
        company_breakdown_text = sanitize_for_channel(
            f"Atividades: {company_totals['tasks']} | Processos: {company_totals['processes']} | Reunioes: {company_totals['meetings']}",
            channel,
        )
        lines.append(f"{style['sub_bullet']}{company_total_text}")
        lines.append(f"{style['sub_bullet']}{company_breakdown_text}")
        lines.append("")

        lines.append(style["header"]("Projetos"))
        projects = company.get("projects") or []
        if projects:
            for project in projects:
                project_label = f"{project['project_code']} - {project['project_name']}"
                lines.append(f"{style['bullet']}{sanitize_for_channel(project_label, channel)}")
                project_activity_count = len(project.get("activities") or [])
                project_activity_text = sanitize_for_channel(f"Atividades no recorte: {project_activity_count}", channel)
                lines.append(f"{style['sub_bullet']}{project_activity_text}")
                for activity in project.get("activities") or []:
                    date_label = activity["completion_date"] if action == "my_work.completed_range" else activity["due_date"]
                    activity_line = (
                        f"{activity['activity_code']} - {activity['title']} | "
                        f"Responsavel: {activity['responsible']} | {date_name}: {format_date_br(date_label)}"
                    )
                    lines.append(f"{style['item_bullet']}{sanitize_for_channel(activity_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem atividades no periodo.")
        lines.append("")

        lines.append(style["header"]("Processos"))
        process_groups = company.get("processes") or []
        if process_groups:
            for process in process_groups:
                process_label = f"{process['process_code']} - {process['process_name']}"
                lines.append(f"{style['bullet']}{sanitize_for_channel(process_label, channel)}")
                process_instance_count = len(process.get("instances") or [])
                process_instance_text = sanitize_for_channel(f"Instancias no recorte: {process_instance_count}", channel)
                lines.append(f"{style['sub_bullet']}{process_instance_text}")
                for instance in process.get("instances") or []:
                    date_label = instance["completion_date"] if action == "my_work.completed_range" else instance["due_date"]
                    instance_line = (
                        f"{instance['instance_code']} - {instance['title']} | "
                        f"Dono do Processo: {instance['owner']} | {date_name}: {format_date_br(date_label)}"
                    )
                    lines.append(f"{style['item_bullet']}{sanitize_for_channel(instance_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem instancias no periodo.")
        lines.append("")

        lines.append(style["header"]("Reunioes Agendadas"))
        meeting_items = company.get("meetings") or []
        if meeting_items:
            meeting_count_text = sanitize_for_channel(f"Reunioes no recorte: {len(meeting_items)}", channel)
            lines.append(f"{style['bullet']}{meeting_count_text}")
            for meeting in meeting_items:
                date_label = meeting["completion_date"] if action == "my_work.completed_range" else meeting["due_date"]
                project_ref = f"{meeting['project_code']} - {meeting['project_name']}" if meeting.get("project_code") else "-"
                meeting_line = (
                    f"{meeting['meeting_code']} - {meeting['meeting_name']} | "
                    f"Projeto: {project_ref} | {date_name}: {format_date_br(date_label)}"
                )
                if action != "my_work.completed_range" and meeting.get("scheduled_time") and meeting.get("scheduled_time") != "-":
                    meeting_line += f" | Hora: {meeting['scheduled_time']}"
                lines.append(f"{style['item_bullet']}{sanitize_for_channel(meeting_line, channel)}")
        else:
            lines.append(f"{style['bullet']}Sem reunioes agendadas no periodo.")

    return "\n".join(lines)
