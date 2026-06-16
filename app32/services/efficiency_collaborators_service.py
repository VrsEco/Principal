from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import func, text as sql_text

from models import (
    ActivityWorkLog,
    CompanyPerformanceSettings,
    Employee,
    Occurrence,
    Process,
    ProcessInstance,
    ProcessInstanceCollaborator,
    Project,
    ProjectActivityCollaborator,
    ProjectTask,
    db,
)


def parse_efficiency_period(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[date, date]:
    today = date.today()
    if not start_date and not end_date:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif start_date and not end_date:
        end_date = start_date
    elif end_date and not start_date:
        start_date = end_date

    assert start_date is not None and end_date is not None
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def get_efficiency_collaborators(
    *,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    employee_ids: Iterable[int] | None = None,
) -> list[dict]:
    start_date, end_date = parse_efficiency_period(start_date=start_date, end_date=end_date)
    business_days = _business_days_between(start_date, end_date)
    scoped_employee_ids = {int(item) for item in (employee_ids or []) if int(item) > 0}

    employees_query = Employee.query.filter_by(company_id=company_id)
    if scoped_employee_ids:
        employees_query = employees_query.filter(Employee.id.in_(sorted(scoped_employee_ids)))
    employees = employees_query.all()

    results: dict[int, dict] = {}
    for employee in employees:
        emp_id = int(employee.id)
        weekly_hours = float(employee.weekly_hours or 40.0)
        contracted_hours = round((weekly_hours / 5.0) * business_days, 2) if weekly_hours else 0.0
        results[emp_id] = {
            "employee_id": emp_id,
            "employee_name": employee.name,
            "role_title": employee.role.title if employee.role else None,
            "department": employee.department,
            "in_progress": {"total": 0, "on_time": 0, "late": 0},
            "completed": {"total": 0, "on_time": 0, "late": 0},
            "positive_occurrences": {"count": 0, "score": 0},
            "negative_occurrences": {"count": 0, "score": 0},
            "delivery_scores": {
                "process": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0, "assigned_count": 0},
                "project": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0, "assigned_count": 0},
                "overall": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0, "assigned_count": 0},
            },
            "delivery_records": {"project": [], "process": []},
            "occurrence_records": {"positive": [], "negative": []},
            "period_hours": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "business_days": business_days,
                "weekly_hours": round(weekly_hours, 2),
                "contracted": contracted_hours,
                "worked_project": 0.0,
                "worked_process": 0.0,
                "worked_total": 0.0,
                "free_capacity": contracted_hours,
                "utilization_percent": 0.0,
                "details": {"project": [], "process": []},
            },
        }

    today = date.today()
    employee_pk_ids = list(results.keys())
    if not employee_pk_ids:
        return []

    log_rows = (
        db.session.query(
            ActivityWorkLog.employee_id,
            ActivityWorkLog.activity_type,
            func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0).label("total_hours"),
        )
        .join(Employee, Employee.id == ActivityWorkLog.employee_id)
        .filter(
            Employee.company_id == company_id,
            ActivityWorkLog.employee_id.in_(employee_pk_ids),
            ActivityWorkLog.work_date >= start_date,
            ActivityWorkLog.work_date <= end_date,
        )
        .group_by(ActivityWorkLog.employee_id, ActivityWorkLog.activity_type)
        .all()
    )

    for row in log_rows:
        if row.employee_id not in results:
            continue
        hours = round(float(row.total_hours or 0), 2)
        if row.activity_type == "project":
            results[row.employee_id]["period_hours"]["worked_project"] += hours
        elif row.activity_type in ("process", "process_instance"):
            results[row.employee_id]["period_hours"]["worked_process"] += hours
        results[row.employee_id]["period_hours"]["worked_total"] += hours

    detailed_logs = (
        ActivityWorkLog.query
        .join(Employee, Employee.id == ActivityWorkLog.employee_id)
        .filter(
            Employee.company_id == company_id,
            ActivityWorkLog.employee_id.in_(employee_pk_ids),
            ActivityWorkLog.work_date >= start_date,
            ActivityWorkLog.work_date <= end_date,
        )
        .order_by(ActivityWorkLog.work_date.desc(), ActivityWorkLog.created_at.desc())
        .all()
    )

    project_ids = sorted({int(log.activity_id) for log in detailed_logs if log.activity_type == "project"})
    process_instance_ids = sorted({int(log.activity_id) for log in detailed_logs if log.activity_type in ("process", "process_instance")})

    project_task_map = {}
    if project_ids:
        project_tasks = (
            ProjectTask.query
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(Project.company_id == company_id, ProjectTask.id.in_(project_ids))
            .all()
        )
        project_task_map = {task.id: task for task in project_tasks}

    process_instance_map = {}
    if process_instance_ids:
        process_instances = (
            ProcessInstance.query
            .filter(ProcessInstance.company_id == company_id, ProcessInstance.id.in_(process_instance_ids))
            .all()
        )
        process_instance_map = {instance.id: instance for instance in process_instances}

    for log in detailed_logs:
        employee_data = results.get(log.employee_id)
        if not employee_data:
            continue

        hours = round(float(log.hours_worked or 0), 2)
        base_record = {
            "activity_id": log.activity_id,
            "hours_worked": hours,
            "work_date": log.work_date.isoformat() if hasattr(log.work_date, "isoformat") else log.work_date,
            "description": log.description or "",
            "created_at": log.created_at.isoformat() if hasattr(log.created_at, "isoformat") else log.created_at,
        }

        if log.activity_type == "project":
            task = project_task_map.get(int(log.activity_id))
            project = task.project if task else None
            employee_data["period_hours"]["details"]["project"].append({
                **base_record,
                "project_name": project.name if project else "Projeto",
                "project_code": getattr(project, "code", None) if project else None,
                "activity_title": getattr(task, "what", None) if task else None,
            })
        elif log.activity_type in ("process", "process_instance"):
            instance = process_instance_map.get(int(log.activity_id))
            process_rel = instance.process_rel if instance else None
            employee_data["period_hours"]["details"]["process"].append({
                **base_record,
                "process_name": process_rel.name if process_rel else "Processo",
                "process_code": getattr(process_rel, "code", None) if process_rel else None,
                "instance_title": getattr(instance, "title", None) if instance else None,
            })

    settings = CompanyPerformanceSettings.query.filter_by(company_id=company_id).first()
    on_time_base = float(settings.on_time_score) if settings else 5.0
    late_fixed_base = float(settings.late_score) if settings else -5.0
    daily_penalty_base = float(settings.daily_delay_penalty) if settings else -1.0

    tasks = ProjectTask.query.join(Project).filter(Project.company_id == company_id).all()
    task_ids = [t.id for t in tasks]
    collabs = ProjectActivityCollaborator.query.filter(
        ProjectActivityCollaborator.activity_id.in_(task_ids) if task_ids else db.false(),
        ProjectActivityCollaborator.is_deleted == False,
    ).all()

    task_collab_map: dict[int, list[int]] = {}
    for collaborator in collabs:
        task_collab_map.setdefault(collaborator.activity_id, []).append(collaborator.employee_id)

    for task in tasks:
        project = task.project
        involved_ids = set()
        if task.employee_id:
            involved_ids.add(int(task.employee_id))
        for employee_id in task_collab_map.get(task.id, []):
            involved_ids.add(int(employee_id))

        is_completed = task.stage in ["completed", "archived"] or task.status == "completed"
        due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
        completion_date = task.completion_date

        is_late = False
        days_late = 0
        if due_date:
            if is_completed:
                completion_day = completion_date.date() if isinstance(completion_date, datetime) else completion_date
                if completion_day and completion_day > due_date:
                    is_late = True
                    days_late = (completion_day - due_date).days
            elif today > due_date:
                is_late = True
                days_late = (today - due_date).days

        multiplier = float(task.score_weight or 1.0)
        for emp_id in involved_ids:
            if emp_id not in results:
                continue
            results[emp_id]["delivery_scores"]["project"]["assigned"] += (on_time_base * multiplier)
            results[emp_id]["delivery_scores"]["project"]["assigned_count"] += 1
            if is_completed:
                results[emp_id]["delivery_scores"]["project"]["potential"] += (on_time_base * multiplier)
                results[emp_id]["completed"]["total"] += 1
                if is_late:
                    results[emp_id]["completed"]["late"] += 1
                    points = (late_fixed_base + (daily_penalty_base * days_late)) * multiplier
                    category = "late_completed"
                    results[emp_id]["delivery_scores"]["project"]["negative"] += abs(points)
                else:
                    results[emp_id]["completed"]["on_time"] += 1
                    points = on_time_base * multiplier
                    category = "on_time"
                    results[emp_id]["delivery_scores"]["project"]["positive"] += points

                results[emp_id]["delivery_scores"]["project"]["total"] += points
                results[emp_id]["delivery_scores"]["project"]["count"] += 1
                results[emp_id]["delivery_records"]["project"].append({
                    "project_code": f"{project.code if hasattr(project, 'code') else 'PROJ-' + str(project.id)}",
                    "project_name": project.name,
                    "activity_title": task.what,
                    "category": category,
                    "due_date": due_date.isoformat() if due_date else None,
                    "completion_date": completion_date.isoformat() if completion_date else None,
                    "points": points,
                    "weight": multiplier,
                })
            else:
                results[emp_id]["in_progress"]["total"] += 1
                if is_late:
                    results[emp_id]["in_progress"]["late"] += 1
                    points = (late_fixed_base + (daily_penalty_base * days_late)) * multiplier
                    results[emp_id]["delivery_scores"]["project"]["total"] += points
                    results[emp_id]["delivery_scores"]["project"]["negative"] += abs(points)
                    results[emp_id]["delivery_scores"]["project"]["potential"] += (on_time_base * multiplier)
                else:
                    results[emp_id]["in_progress"]["on_time"] += 1

    instances = ProcessInstance.query.filter_by(company_id=company_id).all()
    instance_ids = [instance.id for instance in instances]
    process_collaborators = ProcessInstanceCollaborator.query.filter(
        ProcessInstanceCollaborator.process_instance_id.in_(instance_ids) if instance_ids else db.false(),
        ProcessInstanceCollaborator.is_deleted == False,
    ).all()

    instance_collab_map: dict[int, list[int]] = {}
    for row in process_collaborators:
        instance_collab_map.setdefault(row.process_instance_id, []).append(row.employee_id)

    for instance in instances:
        involved_ids = set()
        for attr_name in ("executor_id", "responsible_id", "owner_employee_id"):
            value = getattr(instance, attr_name, None)
            if value:
                involved_ids.add(int(value))
        if instance.collaborators_json:
            try:
                payload = instance.collaborators_json if isinstance(instance.collaborators_json, list) else json.loads(instance.collaborators_json)
                for value in payload:
                    involved_ids.add(int(value))
            except Exception:
                pass
        for employee_id in instance_collab_map.get(instance.id, []):
            involved_ids.add(int(employee_id))

        is_completed = instance.status in ["completed", "finished", "stable"]
        due_date = instance.due_date.date() if isinstance(instance.due_date, datetime) else instance.due_date
        completion_date = instance.completed_at
        completion_day = completion_date.date() if isinstance(completion_date, datetime) else completion_date

        is_late = False
        days_late = 0
        if due_date:
            if is_completed:
                if completion_day and completion_day > due_date:
                    is_late = True
                    days_late = (completion_day - due_date).days
            elif today > due_date:
                is_late = True
                days_late = (today - due_date).days

        multiplier = float(instance.score_weight or 1.0)
        for emp_id in involved_ids:
            if emp_id not in results:
                continue
            results[emp_id]["delivery_scores"]["process"]["assigned"] += (on_time_base * multiplier)
            results[emp_id]["delivery_scores"]["process"]["assigned_count"] += 1
            if is_completed:
                results[emp_id]["delivery_scores"]["process"]["potential"] += (on_time_base * multiplier)
                results[emp_id]["completed"]["total"] += 1
                if is_late:
                    results[emp_id]["completed"]["late"] += 1
                    points = (late_fixed_base + (daily_penalty_base * days_late)) * multiplier
                    category = "late_completed"
                    results[emp_id]["delivery_scores"]["process"]["negative"] += abs(points)
                else:
                    results[emp_id]["completed"]["on_time"] += 1
                    points = on_time_base * multiplier
                    category = "on_time"
                    results[emp_id]["delivery_scores"]["process"]["positive"] += points

                results[emp_id]["delivery_scores"]["process"]["total"] += points
                results[emp_id]["delivery_scores"]["process"]["count"] += 1
                process_name = instance.process_rel.name if instance.process_rel else "Processo"
                results[emp_id]["delivery_records"]["process"].append({
                    "process_name": process_name,
                    "instance_title": instance.title,
                    "category": category,
                    "due_date": due_date.isoformat() if due_date else None,
                    "completion_date": completion_date.isoformat() if completion_date else None,
                    "points": points,
                    "weight": multiplier,
                })
            else:
                results[emp_id]["in_progress"]["total"] += 1
                if is_late:
                    results[emp_id]["in_progress"]["late"] += 1
                    points = (late_fixed_base + (daily_penalty_base * days_late)) * multiplier
                    results[emp_id]["delivery_scores"]["process"]["total"] += points
                    results[emp_id]["delivery_scores"]["process"]["negative"] += abs(points)
                    results[emp_id]["delivery_scores"]["process"]["potential"] += (on_time_base * multiplier)
                else:
                    results[emp_id]["in_progress"]["on_time"] += 1

    collaborators_column_exists = db.session.execute(
        sql_text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'occurrences'
                  AND column_name = 'collaborators_ids'
            )
            """
        )
    ).scalar()

    occurrences_sql = """
        SELECT id, company_id, employee_id, title, type, score, created_at,
               {collaborators_field}
        FROM occurrences
        WHERE company_id = :company_id
    """.format(
        collaborators_field=(
            "collaborators_ids" if collaborators_column_exists else "NULL::text AS collaborators_ids"
        )
    )

    occurrences = db.session.execute(
        sql_text(occurrences_sql),
        {"company_id": company_id},
    ).mappings().all()

    for occurrence in occurrences:
        involved_ids = set()
        if occurrence.get("employee_id"):
            involved_ids.add(int(occurrence["employee_id"]))
        collaborators_ids = occurrence.get("collaborators_ids")
        if collaborators_ids:
            try:
                payload = collaborators_ids if isinstance(collaborators_ids, list) else json.loads(collaborators_ids)
                for value in payload:
                    involved_ids.add(int(value))
            except Exception:
                pass
        for emp_id in involved_ids:
            if emp_id not in results:
                continue
            score = occurrence.get("score") or 0
            occurrence_type = str(occurrence.get("type") or "").lower()
            created_at = occurrence.get("created_at")
            created_at_value = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
            if "positiv" in occurrence_type:
                results[emp_id]["positive_occurrences"]["count"] += 1
                results[emp_id]["positive_occurrences"]["score"] += score
                results[emp_id]["occurrence_records"]["positive"].append({
                    "type": occurrence.get("type"),
                    "title": occurrence.get("title"),
                    "score": score,
                    "created_at": created_at_value,
                })
            elif "negativ" in occurrence_type:
                results[emp_id]["negative_occurrences"]["count"] += 1
                negative_value = -abs(score)
                results[emp_id]["negative_occurrences"]["score"] += negative_value
                results[emp_id]["occurrence_records"]["negative"].append({
                    "type": occurrence.get("type"),
                    "title": occurrence.get("title"),
                    "score": negative_value,
                    "created_at": created_at_value,
                })

    ordered = []
    for emp_id, data in results.items():
        delivery_scores = data["delivery_scores"]
        delivery_scores["overall"]["positive"] = delivery_scores["project"]["positive"] + delivery_scores["process"]["positive"]
        delivery_scores["overall"]["negative"] = delivery_scores["project"]["negative"] + delivery_scores["process"]["negative"]
        delivery_scores["overall"]["total"] = delivery_scores["project"]["total"] + delivery_scores["process"]["total"]
        delivery_scores["overall"]["count"] = delivery_scores["project"]["count"] + delivery_scores["process"]["count"]
        delivery_scores["overall"]["potential"] = delivery_scores["project"]["potential"] + delivery_scores["process"]["potential"]
        delivery_scores["overall"]["assigned"] = delivery_scores["project"]["assigned"] + delivery_scores["process"]["assigned"]
        delivery_scores["overall"]["assigned_count"] = delivery_scores["project"].get("assigned_count", 0) + delivery_scores["process"].get("assigned_count", 0)

        period_hours = data["period_hours"]
        period_hours["worked_project"] = round(period_hours["worked_project"], 2)
        period_hours["worked_process"] = round(period_hours["worked_process"], 2)
        period_hours["worked_total"] = round(period_hours["worked_total"], 2)
        period_hours["free_capacity"] = round(period_hours["contracted"] - period_hours["worked_total"], 2)
        period_hours["utilization_percent"] = round(
            (period_hours["worked_total"] / period_hours["contracted"] * 100) if period_hours["contracted"] > 0 else 0.0,
            1,
        )
        ordered.append(data)

    ordered.sort(key=lambda item: str(item.get("employee_name") or "").lower())
    return ordered


def build_team_efficiency_summary(
    *,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    employee_ids: Iterable[int] | None = None,
) -> dict:
    """Consolida a eficiência da equipe para consumo executivo no painel.

    Mantém a regra detalhada em ``get_efficiency_collaborators`` e devolve
    apenas um read model agregado, tenant-safe por ``company_id``.
    """
    collaborators = get_efficiency_collaborators(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        employee_ids=employee_ids,
    )

    semaphore = {"green": 0, "yellow": 0, "red": 0, "blue": 0, "gray": 0}
    contracted_total = 0.0
    worked_total = 0.0
    score_total = 0.0
    score_max_total = 0.0
    activity_count_total = 0
    instance_count_total = 0
    occurrence_count_total = 0
    late_total = 0
    items = []

    for row in collaborators:
        period_hours = row.get("period_hours") or {}
        contracted = float(period_hours.get("contracted") or 0.0)
        worked = float(period_hours.get("worked_total") or 0.0)
        utilization = float(period_hours.get("utilization_percent") or 0.0)
        in_progress_late = int((row.get("in_progress") or {}).get("late") or 0)
        completed_late = int((row.get("completed") or {}).get("late") or 0)
        employee_late = in_progress_late + completed_late
        positive_occurrences = row.get("positive_occurrences") or {}
        negative_occurrences = row.get("negative_occurrences") or {}
        occurrence_score = float(positive_occurrences.get("score") or 0.0) + float(negative_occurrences.get("score") or 0.0)
        occurrence_count = int(positive_occurrences.get("count") or 0) + int(negative_occurrences.get("count") or 0)
        delivery_scores = row.get("delivery_scores") or {}
        project_scores = delivery_scores.get("project") or {}
        process_scores = delivery_scores.get("process") or {}
        overall_scores = delivery_scores.get("overall") or {}
        project_score = float(project_scores.get("total") or 0.0)
        process_score = float(process_scores.get("total") or 0.0)
        project_max = float(project_scores.get("assigned") or 0.0)
        process_max = float(process_scores.get("assigned") or 0.0)
        activity_count = int(project_scores.get("assigned_count") or project_scores.get("count") or 0)
        instance_count = int(process_scores.get("assigned_count") or process_scores.get("count") or 0)
        project_finished = int(project_scores.get("count") or 0)
        process_finished = int(process_scores.get("count") or 0)
        project_open = max(activity_count - project_finished, 0)
        process_open = max(instance_count - process_finished, 0)
        project_hours = float(period_hours.get("worked_project") or 0.0)
        process_hours = float(period_hours.get("worked_process") or 0.0)
        total_worked_for_split = project_hours + process_hours
        project_capacity = round((contracted * (project_hours / total_worked_for_split)) if total_worked_for_split > 0 else 0.0, 2)
        process_capacity = round(contracted - project_capacity, 2) if total_worked_for_split > 0 else contracted
        project_planned_hours = project_capacity
        process_planned_hours = process_capacity
        employee_score_total = project_score + process_score + occurrence_score
        employee_score_max = float(overall_scores.get("assigned") or 0.0)

        contracted_total += contracted
        worked_total += worked
        score_total += employee_score_total
        score_max_total += employee_score_max
        activity_count_total += activity_count
        instance_count_total += instance_count
        occurrence_count_total += occurrence_count
        late_total += employee_late

        status = _team_efficiency_status(utilization, contracted, employee_late)
        semaphore[status["semaphore"]] += 1
        items.append(
            {
                "id": row.get("employee_id"),
                "code": f"EQ-{row.get('employee_id')}",
                "name": row.get("employee_name") or "Colaborador",
                "group": "team_efficiency",
                "subgroup": status["subgroup"],
                "semaphore": status["semaphore"],
                "situation": status["label"],
                "objective": "Avaliar eficiência, capacidade utilizada e pontualidade das entregas do colaborador.",
                "current_value": utilization,
                "unit": "%",
                "goal": employee_score_max,
                "responsible": {
                    "id": row.get("employee_id"),
                    "name": row.get("employee_name") or "Colaborador",
                    "email": None,
                },
                "project": None,
                "activities": [],
                "status_detail": status["detail"],
                "next_charge": "Análise da Eficiência da Equipe",
                "efficiency": {
                    "role_title": row.get("role_title") or row.get("department") or "",
                    "activity_count": activity_count,
                    "instance_count": instance_count,
                    "occurrence_count": occurrence_count,
                    "status_label": _capacity_label(utilization, contracted, employee_late),
                    "score_total": round(employee_score_total, 2),
                    "score_max": round(employee_score_max, 2),
                    "score_total_label": _format_score_ptbr(employee_score_total),
                    "score_max_label": _format_score_ptbr(employee_score_max),
                    "project_score": round(project_score, 2),
                    "project_max": round(project_max, 2),
                    "process_score": round(process_score, 2),
                    "process_max": round(process_max, 2),
                    "occurrence_score": round(occurrence_score, 2),
                    "project_score_label": _format_score_ptbr(project_score),
                    "project_max_label": _format_score_ptbr(project_max),
                    "process_score_label": _format_score_ptbr(process_score),
                    "process_max_label": _format_score_ptbr(process_max),
                    "occurrence_score_label": _format_score_ptbr(occurrence_score),
                    "project_quantity": {
                        "total": activity_count,
                        "open": project_open,
                        "finished": project_finished,
                    },
                    "process_quantity": {
                        "total": instance_count,
                        "open": process_open,
                        "finished": process_finished,
                    },
                    "project_hours": {
                        "realized": round(project_hours, 2),
                        "planned": round(project_planned_hours, 2),
                        "capacity": round(project_capacity, 2),
                        "realized_label": _format_hours_ptbr(project_hours),
                        "planned_label": _format_hours_ptbr(project_planned_hours),
                        "capacity_label": _format_hours_ptbr(project_capacity),
                    },
                    "process_hours": {
                        "realized": round(process_hours, 2),
                        "planned": round(process_planned_hours, 2),
                        "capacity": round(process_capacity, 2),
                        "realized_label": _format_hours_ptbr(process_hours),
                        "planned_label": _format_hours_ptbr(process_planned_hours),
                        "capacity_label": _format_hours_ptbr(process_capacity),
                    },
                    "occurrences": {
                        "positive_count": int(positive_occurrences.get("count") or 0),
                        "negative_count": int(negative_occurrences.get("count") or 0),
                        "positive_score": float(positive_occurrences.get("score") or 0.0),
                        "negative_score": float(negative_occurrences.get("score") or 0.0),
                        "positive_score_label": _format_score_ptbr(float(positive_occurrences.get("score") or 0.0)),
                        "negative_score_label": _format_score_ptbr(float(negative_occurrences.get("score") or 0.0)),
                    },
                    "utilization_percent": utilization,
                    "contracted_hours": round(contracted, 2),
                    "worked_hours": round(worked, 2),
                    "free_capacity": round(float(period_hours.get("free_capacity") or 0.0), 2),
                    "contracted_hours_label": _format_hours_ptbr(contracted),
                    "worked_hours_label": _format_hours_ptbr(worked),
                    "free_capacity_label": _format_hours_ptbr(float(period_hours.get("free_capacity") or 0.0)),
                    "late_deliveries": employee_late,
                    "score": employee_score_total,
                },
            }
        )

    overall_utilization = round((worked_total / contracted_total * 100) if contracted_total > 0 else 0.0, 1)
    alerts_count = semaphore["yellow"] + semaphore["red"]
    status_label = (
        "Sem equipe ativa"
        if not collaborators
        else "Atenção na capacidade"
        if alerts_count
        else "Equipe em faixa saudável"
    )

    return {
        "total": len(collaborators),
        "card_title": "Equipe (Eficiência)",
        "value_label": f"{_format_score_ptbr(score_total)} / {_format_score_ptbr(score_max_total)}",
        "card_subtitle": "Global da Empresa",
        "alerts_count": alerts_count,
        "alert_label": f"{alerts_count} fora da faixa ideal" if alerts_count else "0 fora da faixa ideal",
        "semaphore": semaphore,
        "items": items,
        "summary": {
            "score_total": round(score_total, 2),
            "score_max": round(score_max_total, 2),
            "score_total_label": _format_score_ptbr(score_total),
            "score_max_label": _format_score_ptbr(score_max_total),
            "activity_count": activity_count_total,
            "instance_count": instance_count_total,
            "occurrence_count": occurrence_count_total,
            "counts_label": f"{activity_count_total} atividades | {instance_count_total} instâncias | {occurrence_count_total} Ocorrências",
            "utilization_percent": overall_utilization,
            "contracted_hours": round(contracted_total, 2),
            "worked_hours": round(worked_total, 2),
            "free_capacity": round(contracted_total - worked_total, 2),
            "late_deliveries": late_total,
            "status_label": status_label,
        },
    }


def _capacity_label(utilization_percent: float, contracted_hours: float, late_deliveries: int) -> str:
    if contracted_hours <= 0:
        return "Sem carga"
    if late_deliveries > 0 or utilization_percent > 95:
        return "Sobrecarregado"
    if utilization_percent < 70:
        return "Ocioso"
    if utilization_percent <= 90:
        return "Saudável"
    return "Atenção"


def _format_score_ptbr(value: float) -> str:
    text = f"{float(value or 0.0):,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_hours_ptbr(value: float) -> str:
    return f"{_format_score_ptbr(value)}h"


def _team_efficiency_status(utilization_percent: float, contracted_hours: float, late_deliveries: int) -> dict:
    if contracted_hours <= 0:
        return {
            "semaphore": "gray",
            "label": "Sem capacidade configurada",
            "subgroup": "Sem carga horária",
            "detail": "Colaborador sem carga horária contratada configurada para o período.",
        }
    if utilization_percent > 95 or late_deliveries > 0:
        return {
            "semaphore": "red",
            "label": "Fora da faixa ideal",
            "subgroup": "Sobrecarga ou atraso",
            "detail": "Há sobrecarga e/ou entregas atrasadas; requer ação de balanceamento.",
        }
    if utilization_percent < 70:
        return {
            "semaphore": "yellow",
            "label": "Capacidade ociosa",
            "subgroup": "Capacidade livre elevada",
            "detail": "A utilização está abaixo da faixa esperada; avaliar redistribuição de demandas.",
        }
    if utilization_percent <= 90:
        return {
            "semaphore": "green",
            "label": "Faixa saudável",
            "subgroup": "Eficiência saudável",
            "detail": "Capacidade e entregas em faixa saudável.",
        }
    return {
        "semaphore": "yellow",
        "label": "Próximo da sobrecarga",
        "subgroup": "Atenção na capacidade",
        "detail": "Utilização acima da faixa ideal; acompanhar para evitar sobrecarga.",
    }


def _business_days_between(start_date: date, end_date: date) -> int:
    total = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)
    return total
