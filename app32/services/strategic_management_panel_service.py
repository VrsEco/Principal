from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from models import (
    Employee,
    Indicator,
    IndicatorData,
    IndicatorGoal,
    Meeting,
    Process,
    Project,
    ProjectTask,
    db,
)
from services.efficiency_collaborators_service import build_team_efficiency_summary


GROUP_DEFINITIONS = {
    "strategic": {
        "label": "Indicadores Estratégicos",
        "short_label": "Estratégicos",
        "subtitle": "Resultado, direção e objetivos corporativos",
        "color": "#ef4444",
    },
    "processes": {
        "label": "Indicadores de Processos",
        "short_label": "Processos",
        "subtitle": "Rotina, BPMN, SLA e maturidade operacional",
        "color": "#f59e0b",
    },
    "projects": {
        "label": "Indicadores de Projetos",
        "short_label": "Projetos",
        "subtitle": "Execução fora da rotina e iniciativas corretivas",
        "color": "#3b82f6",
    },
    "team_efficiency": {
        "label": "Eficiência da Equipe",
        "short_label": "Equipe",
        "subtitle": "Eficiência, capacidade e entrega do time",
        "color": "#10b981",
    },
    "webs": {
        "label": "Indicadores de Teia",
        "short_label": "Teias",
        "subtitle": "Conexões, dependências e alinhamentos críticos",
        "color": "#7c3aed",
    },
}


def build_strategic_management_panel(company_id: int, *, period: str | None = None) -> dict[str, Any]:
    """Monta a visão executiva tenant-safe do Painel de Gestão Estratégica.

    A service não cria cadastros nem altera estado: apenas consolida dados já
    existentes do tenant para leitura e acionamento gerencial pela UI.
    """
    if not company_id:
        raise ValueError("company_id é obrigatório.")

    period_context = _resolve_period(period)
    today = date.today()

    indicators = (
        Indicator.query.filter(Indicator.company_id == company_id)
        .filter(Indicator.is_active.is_(True))
        .order_by(Indicator.name.asc())
        .all()
    )
    indicator_ids = [indicator.id for indicator in indicators]
    latest_data = _latest_indicator_data(company_id, indicator_ids, period_context)
    goals = _latest_indicator_goals(company_id, indicator_ids, period_context)

    projects_by_id = {
        project.id: project
        for project in Project.query.filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .all()
    }
    project_task_stats = _project_task_stats(company_id)
    indicator_task_links = _indicator_task_links(company_id)
    employees_by_id = {
        employee.id: employee
        for employee in Employee.query.filter(Employee.company_id == company_id).all()
    }

    groups: dict[str, dict[str, Any]] = {
        key: {
            **definition,
            "key": key,
            "total": 0,
            "semaphore": Counter({"green": 0, "yellow": 0, "red": 0, "blue": 0, "gray": 0}),
            "alerts": [],
            "subgroups": defaultdict(list),
            "items": [],
        }
        for key, definition in GROUP_DEFINITIONS.items()
    }

    for indicator in indicators:
        group_key = _classify_indicator(indicator)
        latest = latest_data.get(indicator.id)
        goal = goals.get(indicator.id)
        status = _evaluate_indicator_status(indicator, latest, goal)
        responsible = employees_by_id.get(indicator.responsible_id)
        project = projects_by_id.get(indicator.project_id) if indicator.project_id else None
        project_status = _project_execution_status(project, project_task_stats.get(indicator.project_id or 0))

        item = {
            "id": indicator.id,
            "code": indicator.full_code or indicator.code,
            "name": indicator.name,
            "description": indicator.description,
            "group": group_key,
            "subgroup": _infer_subgroup(indicator, group_key),
            "semaphore": status["semaphore"],
            "situation": status["label"],
            "objective": indicator.description or indicator.notes or "Objetivo não informado no cadastro do indicador.",
            "unit": indicator.unit or "",
            "polarity": indicator.polarity or "positive",
            "goal": _decimal_to_float(getattr(goal, "goal_value", None)),
            "goal_date": _date_to_iso(getattr(goal, "goal_date", None)),
            "current_value": _decimal_to_float(getattr(latest, "measured_value", None)),
            "measured_date": _date_to_iso(getattr(latest, "measured_date", None)),
            "responsible": {
                "id": responsible.id,
                "name": responsible.name,
                "email": responsible.email,
            }
            if responsible
            else None,
            "project": _project_payload(project, project_status),
            "activities": _merged_activity_payload(
                project,
                project_task_stats.get(indicator.project_id or 0),
                indicator_task_links.get(indicator.id, []),
            ),
            "status_detail": status["detail"],
            "next_charge": "Próxima reunião de gestão do período",
        }

        group = groups[group_key]
        group["total"] += 1
        group["semaphore"][item["semaphore"]] += 1
        group["items"].append(item)
        group["subgroups"][item["subgroup"]].append(item)
        if item["semaphore"] in {"red", "yellow"}:
            group["alerts"].append(item)

    _enrich_web_group(groups["webs"], company_id, indicators, projects_by_id, project_task_stats)
    _enrich_team_efficiency_group(groups["team_efficiency"], company_id, period_context)

    ordered_groups = []
    for key in ("strategic", "processes", "projects", "team_efficiency", "webs"):
        group = groups[key]
        group["semaphore"] = dict(group["semaphore"])
        group["alerts_count"] = len(group["alerts"])
        group["subgroups"] = [
            {"name": name, "total": len(items), "items": items}
            for name, items in sorted(group["subgroups"].items())
        ]
        ordered_groups.append(group)

    return {
        "company_id": company_id,
        "period": period_context,
        "groups": ordered_groups,
        "meetings": _upcoming_meetings(company_id, today),
        "form_options": _form_options(company_id, employees_by_id, projects_by_id),
        "actions": {
            "new_meeting_url": f"/meetings/company/{company_id}",
            "new_activity_project_url": "/projects/new",
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def _resolve_period(period: str | None) -> dict[str, Any]:
    today = date.today()
    raw = (period or "month").strip().lower()
    if raw == "quarter":
        quarter = ((today.month - 1) // 3) + 1
        start_month = ((quarter - 1) * 3) + 1
        start = date(today.year, start_month, 1)
        end_month = start_month + 2
        next_month = date(today.year + (1 if end_month == 12 else 0), 1 if end_month == 12 else end_month + 1, 1)
        label = f"{quarter}º trimestre/{today.year}"
    elif raw == "year":
        start = date(today.year, 1, 1)
        next_month = date(today.year + 1, 1, 1)
        label = f"Ano/{today.year}"
    else:
        start = date(today.year, today.month, 1)
        next_month = date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
        label = today.strftime("%B/%Y").capitalize()
        raw = "month"
    end = next_month - timedelta(days=1)
    return {"key": raw, "label": label, "start": start.isoformat(), "end": end.isoformat()}


def _latest_indicator_data(company_id: int, indicator_ids: list[int], period: dict[str, Any]) -> dict[int, IndicatorData]:
    if not indicator_ids:
        return {}
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    rows = (
        IndicatorData.query.filter(IndicatorData.company_id == company_id)
        .filter(IndicatorData.indicator_id.in_(indicator_ids))
        .filter(IndicatorData.measured_date >= start)
        .filter(IndicatorData.measured_date <= end)
        .order_by(IndicatorData.indicator_id.asc(), IndicatorData.measured_date.desc(), IndicatorData.id.desc())
        .all()
    )
    latest: dict[int, IndicatorData] = {}
    for row in rows:
        latest.setdefault(row.indicator_id, row)
    return latest


def _latest_indicator_goals(company_id: int, indicator_ids: list[int], period: dict[str, Any]) -> dict[int, IndicatorGoal]:
    if not indicator_ids:
        return {}
    end = date.fromisoformat(period["end"])
    rows = (
        IndicatorGoal.query.filter(IndicatorGoal.company_id == company_id)
        .filter(IndicatorGoal.indicator_id.in_(indicator_ids))
        .filter(IndicatorGoal.status == "active")
        .filter(db.or_(IndicatorGoal.goal_date.is_(None), IndicatorGoal.goal_date <= end))
        .order_by(IndicatorGoal.indicator_id.asc(), IndicatorGoal.goal_date.desc().nullslast(), IndicatorGoal.id.desc())
        .all()
    )
    latest: dict[int, IndicatorGoal] = {}
    for row in rows:
        latest.setdefault(row.indicator_id, row)
    return latest


def _project_task_stats(company_id: int) -> dict[int, dict[str, Any]]:
    today = date.today()
    rows = (
        db.session.query(ProjectTask, Project)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .filter(ProjectTask.is_deleted.is_(False))
        .all()
    )
    stats: dict[int, dict[str, Any]] = defaultdict(lambda: {"total": 0, "late": 0, "open": 0, "completed": 0, "items": []})
    for task, project in rows:
        bucket = stats[project.id]
        bucket["total"] += 1
        is_completed = task.stage == "completed" or task.status == "completed"
        due_date = _date_only(task.due_date)
        if is_completed:
            bucket["completed"] += 1
        else:
            bucket["open"] += 1
            if due_date and due_date < today:
                bucket["late"] += 1
        bucket["items"].append(
            {
                "id": task.id,
                "code": task.code,
                "what": task.what,
                "responsible": task.employee_name,
                "due_date": _date_to_iso(due_date),
                "stage": task.stage,
                "status": task.status,
                "late": bool(due_date and due_date < today and not is_completed),
            }
        )
    return stats


def _indicator_task_links(company_id: int) -> dict[int, list[dict[str, Any]]]:
    marker = "APP32_INDICATOR_LINK:"
    rows = (
        db.session.query(ProjectTask, Project)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .filter(ProjectTask.is_deleted.is_(False))
        .filter(ProjectTask.notes.ilike(f"%{marker}%"))
        .all()
    )
    links: dict[int, list[dict[str, Any]]] = defaultdict(list)
    today = date.today()
    for task, project in rows:
        indicator_id = _extract_indicator_link(task.notes)
        if not indicator_id:
            continue
        due_date = _date_only(task.due_date)
        is_completed = task.stage == "completed" or task.status == "completed"
        links[indicator_id].append(
            {
                "id": task.id,
                "code": task.code,
                "what": task.what,
                "responsible": task.employee_name,
                "due_date": _date_to_iso(due_date),
                "stage": task.stage,
                "status": task.status,
                "late": bool(due_date and due_date < today and not is_completed),
                "project_id": project.id,
                "project_code": project.code,
                "project_name": project.name,
                "linked_by_indicator": True,
            }
        )
    return links


def _extract_indicator_link(notes: str | None) -> int | None:
    if not notes:
        return None
    marker = "APP32_INDICATOR_LINK:"
    for line in str(notes).splitlines():
        if marker not in line:
            continue
        try:
            return int(line.split(marker, 1)[1].strip().split()[0])
        except (TypeError, ValueError, IndexError):
            return None
    return None


def _classify_indicator(indicator: Indicator) -> str:
    source = (indicator.source_module or "").lower()
    text = " ".join(
        str(value or "").lower()
        for value in [indicator.name, indicator.code, indicator.full_code, indicator.indicator_type, indicator.okr_reference, source]
    )
    if indicator.project_id or source in {"project", "projects", "projetos"}:
        return "projects"
    if indicator.process_id or indicator.routine_id or source in {"process", "processes", "routine", "routines", "bpmn"}:
        return "processes"
    if any(token in text for token in ["teia", "conex", "depend", "rede", "network"]):
        return "webs"
    return "strategic"


def _infer_subgroup(indicator: Indicator, group_key: str) -> str:
    text = f"{indicator.name} {indicator.code} {indicator.full_code or ''}".lower()
    if group_key == "strategic":
        if any(token in text for token in ["comercial", "venda", "cliente", "proposta"]):
            return "Comerciais"
        if any(token in text for token in ["finance", "receita", "custo", "margem", "caixa"]):
            return "Financeiros"
        if any(token in text for token in ["operac", "produção", "produtiv"]):
            return "Operacionais"
        return "Corporativos"
    if group_key == "processes":
        return "Rotina, BPMN e SLA"
    if group_key == "projects":
        return "Projetos e iniciativas"
    return "Conexões e dependências"


def _evaluate_indicator_status(indicator: Indicator, latest: IndicatorData | None, goal: IndicatorGoal | None) -> dict[str, str]:
    current = _to_decimal(getattr(latest, "measured_value", None))
    target = _to_decimal(getattr(goal, "goal_value", None))
    if current is None:
        return {"semaphore": "gray", "label": "Sem medição no período", "detail": "Inclua medição no menu de indicadores."}
    if target is None or target == 0:
        return {"semaphore": "gray", "label": "Sem meta ativa", "detail": "Cadastre meta no menu específico de indicadores."}

    ratio = current / target if (indicator.polarity or "positive") == "positive" else target / current if current else Decimal("0")
    if ratio >= Decimal("1.10"):
        return {"semaphore": "blue", "label": "Acima do range", "detail": "Resultado acima da meta de referência."}
    if ratio >= Decimal("1.00"):
        return {"semaphore": "green", "label": "Dentro do range", "detail": "Indicador dentro da meta."}
    if ratio >= Decimal("0.90"):
        return {"semaphore": "yellow", "label": "Atenção", "detail": "Desvio moderado exige acompanhamento."}
    return {"semaphore": "red", "label": "Fora do range", "detail": "Desvio crítico exige ação corretiva governada."}


def _project_execution_status(project: Project | None, stats: dict[str, Any] | None) -> dict[str, Any] | None:
    if not project:
        return None
    stats = stats or {"total": 0, "late": 0, "open": 0, "completed": 0}
    if stats.get("late", 0) > 0:
        label = "Atividades atrasadas"
        semaphore = "red"
    elif project.status in {"completed", "done"}:
        label = "Concluído"
        semaphore = "green"
    elif stats.get("open", 0) > 0:
        label = "Em execução"
        semaphore = "blue"
    else:
        label = "Sem atividades abertas"
        semaphore = "gray"
    return {"label": label, "semaphore": semaphore, **stats}


def _project_payload(project: Project | None, status: dict[str, Any] | None) -> dict[str, Any] | None:
    if not project:
        return None
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "owner": project.owner,
        "status": project.status,
        "deadline": _date_to_iso(project.end_date),
        "execution": status,
    }


def _project_activity_payload(project: Project | None, stats: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not project or not stats:
        return []
    return stats.get("items", [])[:5]


def _merged_activity_payload(project: Project | None, stats: dict[str, Any] | None, linked_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    seen = set()
    for item in _project_activity_payload(project, stats) + list(linked_items or []):
        key = int(item.get("id") or 0)
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items[:8]


def _form_options(company_id: int, employees_by_id: dict[int, Employee], projects_by_id: dict[int, Project]) -> dict[str, Any]:
    processes = (
        Process.query.filter(Process.company_id == company_id)
        .order_by(Process.name.asc())
        .all()
    )
    active_projects = [
        project
        for project in projects_by_id.values()
        if project.status not in {"completed", "cancelled", "archived"}
    ]
    return {
        "projects": [
            {"id": project.id, "code": project.code, "name": project.name}
            for project in sorted(active_projects, key=lambda item: item.name or "")
        ],
        "processes": [
            {"id": process.id, "code": process.code, "name": process.name}
            for process in processes
        ],
        "employees": [
            {"id": employee.id, "name": employee.name, "email": employee.email}
            for employee in sorted(employees_by_id.values(), key=lambda item: item.name or "")
        ],
    }


def _enrich_team_efficiency_group(group: dict[str, Any], company_id: int, period: dict[str, Any]) -> None:
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    summary = build_team_efficiency_summary(
        company_id=company_id,
        start_date=start,
        end_date=end,
    )

    group["total"] = summary["total"]
    group["card_title"] = summary.get("card_title")
    group["card_subtitle"] = summary.get("card_subtitle")
    group["value_label"] = summary["value_label"]
    group["alert_label"] = summary["alert_label"]
    group["detail_url"] = f"/companies/{company_id}/efficiency-analysis"
    group["summary"] = summary.get("summary") or {}
    group["semaphore"].update(summary["semaphore"])
    group["items"] = list(summary["items"])

    for item in group["items"]:
        group["subgroups"][item["subgroup"]].append(item)
        if item["semaphore"] in {"red", "yellow"}:
            group["alerts"].append(item)


def _enrich_web_group(group: dict[str, Any], company_id: int, indicators: list[Indicator], projects: dict[int, Project], task_stats: dict[int, dict[str, Any]]) -> None:
    unlinked_indicators = [indicator for indicator in indicators if not indicator.responsible_id or (indicator.project_id is None and _classify_indicator(indicator) != "processes")]
    late_projects = [project for project_id, project in projects.items() if task_stats.get(project_id, {}).get("late", 0) > 0]
    score = len(unlinked_indicators) + len(late_projects)
    semaphore = "green" if score == 0 else "yellow" if score < 3 else "red"
    synthetic = {
        "id": "web-health",
        "code": "TEIA",
        "name": "Saúde das teias de conexão",
        "group": "webs",
        "subgroup": "Conexões e dependências",
        "semaphore": semaphore,
        "situation": "Satisfatória" if semaphore == "green" else "Insatisfatória" if semaphore == "yellow" else "Crítica",
        "objective": "Avaliar dependências frágeis entre indicadores, responsáveis, projetos e atividades.",
        "current_value": score,
        "goal": 0,
        "responsible": None,
        "project": None,
        "activities": [],
        "status_detail": f"{len(unlinked_indicators)} indicadores com governança incompleta e {len(late_projects)} projetos com atraso.",
        "next_charge": "Reunião gerencial do período",
    }
    group["total"] += 1
    group["semaphore"][semaphore] += 1
    group["items"].append(synthetic)
    group["subgroups"]["Conexões e dependências"].append(synthetic)
    if semaphore in {"red", "yellow"}:
        group["alerts"].append(synthetic)


def _upcoming_meetings(company_id: int, today: date) -> list[dict[str, Any]]:
    meetings = (
        Meeting.query.filter(Meeting.company_id == company_id)
        .filter(Meeting.scheduled_date >= today)
        .order_by(Meeting.scheduled_date.asc(), Meeting.scheduled_time.asc())
        .limit(6)
        .all()
    )
    payload = []
    for meeting in meetings:
        data = meeting.to_dict()
        guests = data.get("guests") or {}
        internal = guests.get("internal") if isinstance(guests, dict) else []
        payload.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "date": data.get("scheduled_date"),
                "time": meeting.scheduled_time,
                "status": meeting.status,
                "project_title": data.get("project_title"),
                "guests": [guest.get("name") for guest in (internal or []) if isinstance(guest, dict)][:5],
                "agenda": data.get("agenda") or [],
            }
        )
    return payload


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_to_float(value: Any) -> float | None:
    decimal = _to_decimal(value)
    return float(decimal) if decimal is not None else None


def _date_to_iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _date_only(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
