import json

from flask import Blueprint, render_template, jsonify, request, send_file, url_for
from flask_login import login_required, current_user
from datetime import datetime
from models import db, User, Company, Employee, Project, ProjectTask, Process, ProcessInstance
from utils.permissions import can_access_company
import logging

logger = logging.getLogger(__name__)

my_work_bp = Blueprint('my_work', __name__)


def _user_has_company_access(company_id: int | None) -> bool:
    if not company_id:
        return False
    return can_access_company(company_id)


@my_work_bp.route('/my-work')
@login_required
def my_work():
    """My Work dashboard page"""
    return render_template('modules/my_work/my_work_v2.html')

def safe_date_format(dt, format_type='br'):
    """Safely format a date object or string"""
    if not dt:
        return '--' if format_type == 'br' else None
    
    # If it's already a date/datetime object (has strftime)
    if hasattr(dt, 'strftime'):
        if format_type == 'br':
            return dt.strftime('%d/%m/%Y')
        return dt.isoformat()
    
    # If it's a string, try to convert YYYY-MM-DD to DD/MM/YYYY if requested
    if isinstance(dt, str):
        if format_type == 'br' and len(dt) >= 10 and dt[4] == '-' and dt[7] == '-':
            # Simple conversion for YYYY-MM-DD to DD/MM/YYYY
            return f"{dt[8:10]}/{dt[5:7]}/{dt[0:4]}"
        return dt # Return as is
            
    return str(dt)


def _parse_int_list(values):
    if not isinstance(values, list):
        return []
    parsed = []
    for value in values:
        try:
            parsed.append(int(value))
        except (TypeError, ValueError):
            continue
    # mantém ordem de chegada sem duplicar
    unique = []
    seen = set()
    for item in parsed:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _parse_export_filters(raw_filters: str):
    if not raw_filters:
        return {}
    try:
        payload = json.loads(raw_filters)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    normalized = {}
    for key in (
        "company_ids",
        "responsible_ids",
        "executor_ids",
        "project_ids",
        "process_ids",
        "process_owner_ids",
    ):
        values = _parse_int_list(payload.get(key))
        if values:
            normalized[key] = values

    tags = payload.get("delivery_tags")
    if isinstance(tags, list):
        valid_tags = []
        for tag in tags:
            value = str(tag or "").strip().lower()
            if value in {"open", "completed"} and value not in valid_tags:
                valid_tags.append(value)
        normalized["delivery_tags"] = valid_tags

    for key in ("due_date_start", "due_date_end"):
        value = str(payload.get(key) or "").strip()
        if value:
            normalized[key] = value

    search = str(payload.get("search") or "").strip()
    if search:
        normalized["search"] = search

    project_selection = str(payload.get("project_selection") or "").strip().lower()
    if project_selection == "none":
        normalized["project_selection"] = "none"

    process_selection = str(payload.get("process_selection") or "").strip().lower()
    if process_selection == "none":
        normalized["process_selection"] = "none"

    return normalized


def _join_labels(items, limit=4):
    if not items:
        return ""
    if len(items) <= limit:
        return ", ".join(items)
    return f"{', '.join(items[:limit])} e mais {len(items) - limit}"


def _format_filter_date_range(start_value, end_value):
    start_label = safe_date_format(start_value, "br") if start_value else ""
    end_label = safe_date_format(end_value, "br") if end_value else ""
    if start_label and end_label:
        return f"{start_label} até {end_label}"
    if start_label:
        return f"A partir de {start_label}"
    if end_label:
        return f"Até {end_label}"
    return ""


def _coerce_date(value):
    if not value:
        return None
    if hasattr(value, "date"):
        try:
            return value.date()
        except Exception:
            pass
    if hasattr(value, "strftime") and not isinstance(value, str):
        try:
            return value
        except Exception:
            pass
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).date()
        except ValueError:
            continue
    return None


def _resolve_report_status_label(activity: dict) -> str:
    closed_statuses = {"completed", "done", "cancelled", "canceled", "archived"}
    status = str(activity.get("status") or "").strip().lower()
    is_closed = status in closed_statuses

    due_date = _coerce_date(
        activity.get("deadline_date")
        or activity.get("deadline")
        or activity.get("due_date")
    )
    completed_date = _coerce_date(activity.get("completed_date"))

    if is_closed:
        is_late = False
        if due_date and completed_date:
            is_late = completed_date > due_date
        elif activity.get("is_overdue"):
            is_late = True
        return "Concluída com Atraso" if is_late else "Concluída em Dia"

    return "Em Aberto Atrasada" if activity.get("is_overdue") else "Em Aberto em Dia"


def _compose_code_title(code_value, title_value):
    code = str(code_value or "").strip()
    title = str(title_value or "").strip()

    if code and title:
        if code.lower() in title.lower():
            return title
        return f"{code}\n{title}"
    if title:
        return title
    if code:
        return code
    return "-"


def _resolve_responsible_label(activity: dict) -> str:
    direct = str(
        activity.get("responsible_name")
        or activity.get("executor_name")
        or ""
    ).strip()
    if direct:
        return direct

    collaborators = activity.get("collaborators_json") or activity.get("collaborators") or []
    role_priority = ("responsible", "owner", "executor")

    for role in role_priority:
        for collaborator in collaborators:
            collaborator_role = str(collaborator.get("role") or "").strip().lower()
            if collaborator_role and collaborator_role != role:
                continue
            name = str(collaborator.get("name") or collaborator.get("email") or "").strip()
            if name:
                return name

    return "-"


def _activity_matches_process_owner(activity: dict, owner_ids: list[int]) -> bool:
    if not owner_ids:
        return True
    if (activity.get("type") or "").lower() != "process":
        return True

    direct_owner_id = activity.get("owner_id")
    try:
        if direct_owner_id is not None and int(direct_owner_id) in owner_ids:
            return True
    except (TypeError, ValueError):
        pass

    collaborators = activity.get("collaborators_json") or activity.get("collaborators") or []
    for collaborator in collaborators:
        role = str(collaborator.get("role") or "").strip().lower()
        if role and role != "owner":
            continue
        collaborator_id = collaborator.get("id") or collaborator.get("employee_id")
        try:
            if collaborator_id is not None and int(collaborator_id) in owner_ids:
                return True
        except (TypeError, ValueError):
            continue

    return False


def _build_active_filters_summary(scope: str, filters: dict, filter_options: dict) -> list[dict]:
    companies = filter_options.get("companies") or []
    collaborators = filter_options.get("collaborators") or []
    projects = filter_options.get("projects") or []
    processes = filter_options.get("processes") or []

    company_map = {int(c.get("company_id")): (c.get("company_name") or "Empresa") for c in companies if c.get("company_id")}
    collaborator_map = {int(c.get("id")): (c.get("name") or "Colaborador") for c in collaborators if c.get("id")}
    project_map = {int(p.get("id")): (p.get("title") or "Projeto") for p in projects if p.get("id")}
    process_map = {int(p.get("id")): (p.get("name") or "Processo") for p in processes if p.get("id")}

    summary = []
    if scope in {"company", "general"}:
        scope_label = {
            "company": "Empresa",
            "general": "Geral",
        }[scope]
        summary.append({"label": "Escopo", "value": scope_label})

    company_ids = filters.get("company_ids") or []
    selected_company_set = {
        int(cid) for cid in company_ids
        if isinstance(cid, int) or str(cid).isdigit()
    }
    if not selected_company_set:
        selected_company_set = {cid for cid in company_map.keys()}

    def _record_company_id(record):
        value = record.get("company_id")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _available_ids(records, id_key, allow_empty_company=False):
        available = set()
        for record in records:
            record_id = record.get(id_key)
            try:
                record_id = int(record_id)
            except (TypeError, ValueError):
                continue
            rec_company = _record_company_id(record)
            if rec_company is None and allow_empty_company:
                available.add(record_id)
                continue
            if rec_company in selected_company_set:
                available.add(record_id)
        return available
    if company_ids:
        if not (companies and len(company_ids) >= len(companies)):
            labels = [company_map.get(cid, f"Empresa #{cid}") for cid in company_ids]
            summary.append({"label": "Empresas", "value": _join_labels(labels)})

    responsible_ids = filters.get("responsible_ids") or []
    if responsible_ids:
        ids_set = set(responsible_ids)
        available = _available_ids(collaborators, "id")
        if not available or ids_set != available:
            labels = [collaborator_map.get(cid, f"Colaborador #{cid}") for cid in responsible_ids]
            summary.append({"label": "Responsáveis", "value": _join_labels(labels)})

    executor_ids = filters.get("executor_ids") or []
    if executor_ids:
        ids_set = set(executor_ids)
        available = _available_ids(collaborators, "id")
        if not available or ids_set != available:
            labels = [collaborator_map.get(cid, f"Colaborador #{cid}") for cid in executor_ids]
            summary.append({"label": "Executores", "value": _join_labels(labels)})

    if filters.get("project_selection") == "none":
        summary.append({"label": "Projetos", "value": "Nenhum selecionado"})
    else:
        project_ids = filters.get("project_ids") or []
        if project_ids:
            ids_set = set(project_ids)
            available = _available_ids(projects, "id")
            if not available or ids_set != available:
                labels = [project_map.get(pid, f"Projeto #{pid}") for pid in project_ids]
                summary.append({"label": "Projetos", "value": _join_labels(labels)})

    if filters.get("process_selection") == "none":
        summary.append({"label": "Processos", "value": "Nenhum selecionado"})
    else:
        process_ids = filters.get("process_ids") or []
        if process_ids:
            ids_set = set(process_ids)
            available = _available_ids(processes, "id")
            if not available or ids_set != available:
                labels = [process_map.get(pid, f"Processo #{pid}") for pid in process_ids]
                summary.append({"label": "Processos", "value": _join_labels(labels)})

    process_owner_ids = filters.get("process_owner_ids") or []
    if process_owner_ids:
        ids_set = set(process_owner_ids)
        available = _available_ids(collaborators, "id", allow_empty_company=True)
        if not available or ids_set != available:
            labels = [collaborator_map.get(cid, f"Dono #{cid}") for cid in process_owner_ids]
            summary.append({"label": "Donos de processo", "value": _join_labels(labels)})

    if "delivery_tags" in filters:
        delivery_tags = filters.get("delivery_tags") or []
        delivery_label_map = {
            "open": "Em aberto",
            "completed": "Concluídas",
        }
        if not delivery_tags:
            delivery_value = "Nenhum status"
        else:
            delivery_value = ", ".join(delivery_label_map.get(tag, tag) for tag in delivery_tags)
        if delivery_value and delivery_value != "Todos" and delivery_value != "Nenhum status":
            summary.append({"label": "Status", "value": delivery_value})

    period_label = _format_filter_date_range(
        filters.get("due_date_start"),
        filters.get("due_date_end"),
    )
    if period_label:
        summary.append({"label": "Período", "value": period_label})

    search = str(filters.get("search") or "").strip()
    if search:
        summary.append({"label": "Busca", "value": search})

    return summary

@my_work_bp.route('/my-work/export-pdf')
@login_required
def export_my_work_pdf():
    """Renderiza relatório do My Work em modo impressão (browser print/PDF)."""
    from services.my_work.discovery_service import (
        get_filter_options_v2,
        get_user_activities_v2,
    )
    from services.my_work_service import _calculate_stats_from_activities

    scope = str(request.args.get("scope") or "me").strip().lower()
    if scope not in {"me", "company", "general"}:
        scope = "me"

    exported_filters = _parse_export_filters(request.args.get("filters"))
    query_filters = dict(exported_filters)
    responsible_ids = query_filters.pop("responsible_ids", [])
    executor_ids = query_filters.pop("executor_ids", [])
    if responsible_ids or executor_ids:
        query_filters["employee_ids"] = list(set(responsible_ids + executor_ids))

    company_ids = exported_filters.get("company_ids")
    active_company_id = request.args.get("active_company_id", type=int)

    activities_raw, _scope_counts = get_user_activities_v2(
        user_id=current_user.id,
        scope=scope,
        filters=query_filters,
        company_ids=company_ids,
        active_company_id=active_company_id,
    )

    if exported_filters.get("project_selection") == "none":
        activities_raw = [
            item for item in activities_raw
            if (item.get("type") or "").lower() != "project"
        ]

    if exported_filters.get("process_selection") == "none":
        activities_raw = [
            item for item in activities_raw
            if (item.get("type") or "").lower() != "process"
        ]

    process_owner_ids = exported_filters.get("process_owner_ids") or []
    if process_owner_ids:
        activities_raw = [
            item for item in activities_raw
            if _activity_matches_process_owner(item, process_owner_ids)
        ]

    stats = _calculate_stats_from_activities(activities_raw)
    stats["total"] = len(activities_raw)

    activities = []
    for item in activities_raw:
        item_type = (item.get("type") or "").lower()
        is_project = item_type == "project"

        process_project_code = item.get("project_code") if is_project else item.get("process_code")
        process_project_title = item.get("project_title") if is_project else item.get("process_name")
        process_project_label = _compose_code_title(process_project_code, process_project_title)

        activity_instance_code = item.get("activity_code")
        if not activity_instance_code and not is_project:
            activity_instance_code = item.get("instance_code")
        if not activity_instance_code and not is_project:
            process_code = str(item.get("process_code") or "").strip()
            instance_id = item.get("id") or item.get("instance_id")
            if process_code and instance_id:
                activity_instance_code = f"{process_code}.{instance_id}"

        activity_instance_title = item.get("title") or item.get("process_name") or item.get("project_title")
        activity_instance_label = _compose_code_title(activity_instance_code, activity_instance_title)
        responsible_label = _resolve_responsible_label(item)

        due_raw = item.get("deadline_date") or item.get("deadline") or item.get("due_date")
        activities.append(
            {
                "type": "Projeto" if is_project else "Processo",
                "process_project": process_project_label,
                "activity_instance": activity_instance_label,
                "responsible": responsible_label,
                "due_date": safe_date_format(due_raw, "br"),
                "status": item.get("status"),
                "status_display": _resolve_report_status_label(item),
            }
        )

    activities_sorted = sorted(
        activities,
        key=lambda activity: (
            activity.get("due_date") in (None, "", "--"),
            str(activity.get("due_date") or ""),
            str(activity.get("activity_instance") or "").lower(),
        ),
    )

    filter_options = get_filter_options_v2(current_user.id) or {}
    active_filters = _build_active_filters_summary(scope, exported_filters, filter_options)

    employee = Employee.query.filter_by(user_id=current_user.id, status='active').first()
    company = Company.query.get(employee.company_id) if employee and employee.company_id else None

    return render_template(
        "modules/my_work/my_work_report_compact_print.html",
        user_name=current_user.name or current_user.email,
        company_name=company.name if company else "Empresa",
        generated_at=datetime.now().strftime('%d/%m/%Y %H:%M'),
        activities=activities_sorted,
        stats=stats,
        active_filters=active_filters,
    )

@my_work_bp.route('/my-work/process-instance/<int:instance_id>')
@login_required
def process_instance_view(instance_id):
    """Detailed view of a process execution"""
    instance = ProcessInstance.query.get_or_404(instance_id)
    company = Company.query.get(instance.company_id)
    return render_template('modules/processes/process_instance_v2.html', 
                          instance=instance, 
                          instance_data=instance.to_dict(),
                          company=company)

@my_work_bp.route('/my-work/project-task/<int:task_id>')
@login_required
def project_task_view(task_id):
    """Detailed view of a project task execution (Hours and Info)"""
    from models import ProjectTask, Project
    task = ProjectTask.query.get_or_404(task_id)
    project = Project.query.get(task.project_id) if task.project_id else None
    company = Company.query.get(project.company_id) if project else None
    return render_template('modules/projects/project_task_v2.html', 
                           task=task, 
                           task_data=task.to_dict(),
                           project=project,
                           company=company)

@my_work_bp.route('/my-work/api/project-task/<int:task_id>/summary-options')
@login_required
def project_task_summary_options(task_id):
    from services.project_responsible_summary_service import build_summary_hint, build_summary_options, get_task_responsible_user

    task = ProjectTask.query.get_or_404(task_id)
    project = Project.query.get(task.project_id) if task.project_id else None
    company_id = project.company_id if project else None
    if not _user_has_company_access(company_id):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    target_user = get_task_responsible_user(task)
    return jsonify({
        'success': True,
        'title': 'Resumo da Atividade',
        'options': build_summary_options(
            target_user,
            url_for('my_work.project_task_summary_pdf', task_id=task.id),
            url_for('my_work.send_project_task_summary', task_id=task.id),
        ),
        'hint': build_summary_hint(target_user),
    })


@my_work_bp.route('/my-work/api/project-task/<int:task_id>/summary.pdf')
@login_required
def project_task_summary_pdf(task_id):
    from io import BytesIO
    from services.project_summary_pdf_service import generate_task_summary_pdf_bytes

    task = ProjectTask.query.get_or_404(task_id)
    project = Project.query.get(task.project_id) if task.project_id else None
    company_id = project.company_id if project else None
    if not _user_has_company_access(company_id):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    pdf_bytes = generate_task_summary_pdf_bytes(task)
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'resumo-atividade-{task.code or task.id}.pdf',
    )


@my_work_bp.route('/my-work/api/project-task/<int:task_id>/summary', methods=['POST'])
@my_work_bp.route('/my-work/api/project-task/<int:task_id>/send-summary', methods=['POST'])
@login_required
def send_project_task_summary(task_id):
    task = ProjectTask.query.get_or_404(task_id)
    project = Project.query.get(task.project_id) if task.project_id else None
    company_id = project.company_id if project else None
    if not _user_has_company_access(company_id):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    from services.project_responsible_summary_service import send_task_summary_to_responsible

    payload = request.get_json(silent=True) or {}
    preferred_channel = (payload.get('channel') or '').strip().lower() or None
    result = send_task_summary_to_responsible(task, preferred_channel=preferred_channel)
    if not result.get('success'):
        return jsonify({'success': False, 'message': result.get('error') or 'Falha ao enviar resumo', 'result': result}), 400

    channel_label = {'email': 'E-mail', 'whatsapp': 'WhatsApp'}.get(result.get('delivery_channel'), result.get('delivery_channel'))
    return jsonify({
        'success': True,
        'message': f"Resumo da atividade enviado com sucesso via {channel_label}",
        'result': result,
    })


@my_work_bp.route('/my-work/api/filter-options')
@login_required
def my_work_filter_options():
    from services.my_work.discovery_service import get_filter_options_v2
    try:
        data = get_filter_options_v2(current_user.id)
        logger.info(f"📊 Filter Options Response: {len(data.get('companies', []))} companies, {len(data.get('collaborators', []))} collabs, role={data.get('user_role')}")
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"filter-options error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/activities')
@login_required
def my_work_api_activities():
    from services.my_work.discovery_service import get_user_activities_v2
    # In v2, stats are calculated directly or derived from data for now
    from services.my_work_service import _calculate_stats_from_activities
    
    # user = User.query.get(current_user.id) # Redundante pois current_user já é o objeto User
    scope = request.args.get('scope', 'me')

    def _parse_ints(val_str):
        if not val_str: return None
        res = []
        for i in val_str.split(','):
            i = i.strip()
            if i and i.isdigit():
                res.append(int(i))
        return res if res else None

    # Parsing filters
    company_ids = _parse_ints(request.args.get('company_ids'))

    # Merge responsible_ids and executor_ids into a single list of employee_ids to filter
    r_ids = _parse_ints(request.args.get('responsible_ids')) or []
    e_ids = _parse_ints(request.args.get('executor_ids')) or []
    all_emp_ids = list(set(r_ids + e_ids))

    # Parse delivery_tags (status filters)
    delivery_tags = request.args.get('delivery_tags')
    # If param is missing (None), return everything (delivery_tags_list = None)
    # If param is provided but empty (''), return nothing (delivery_tags_list = [])
    if delivery_tags is not None:
        delivery_tags_list = [t.strip() for t in delivery_tags.split(',')] if delivery_tags.strip() else []
    else:
        delivery_tags_list = None

    # Normalizing request parameters to filters dict
    filters = {
        "search": request.args.get('search'),
        "sort": request.args.get('sort', 'deadline'),
        "project_ids": _parse_ints(request.args.get('project_ids')),
        "process_ids": _parse_ints(request.args.get('process_ids')),
        "employee_ids": all_emp_ids if all_emp_ids else None,
        "due_date_start": request.args.get('due_date_start'),
        "due_date_end": request.args.get('due_date_end'),
        "delivery_tags": delivery_tags_list
    }


    active_company_id = request.args.get('active_company_id', type=int)

    logger.info(f"📊 API Request: scope={scope}, company_ids={company_ids}, active_company={active_company_id}")
    try:
        activities, scope_counts = get_user_activities_v2(
            user_id=current_user.id,
            scope=scope,
            filters=filters,
            company_ids=company_ids,
            active_company_id=active_company_id
        )
        
        stats = _calculate_stats_from_activities(activities)

        return jsonify({
            "success": True,
            "data": activities,
            "stats": stats,
            "scope_counts": scope_counts
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/occurrences/summary')
@login_required
def my_work_occurrences_summary():
    from services.my_work_service import get_occurrences_summary, get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_ids_str = request.args.get('company_ids')
    
    company_ids = None
    if company_ids_str:
        company_ids = []
        for i in company_ids_str.split(','):
            i = i.strip()
            if i and i.isdigit():
                company_ids.append(int(i))
    
    try:
        summary = get_occurrences_summary(employee_id, company_ids=company_ids)
        return jsonify({
            "success": True,
            "data": summary
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/team-overview')
@login_required
def my_work_team_overview():
    from services.my_work_service import get_team_overview, get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_id_str = request.args.get('company_id')
    company_id = int(company_id_str) if company_id_str and company_id_str.isdigit() else None
    
    try:
        data = get_team_overview(employee_id, company_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Team Overview Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/company-overview')
@login_required
def my_work_company_overview():
    from services.my_work.metrics_service import get_company_overview_v2
    from services.my_work_service import get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_id_str = request.args.get('company_id')
    company_id = int(company_id_str) if company_id_str and company_id_str.isdigit() else None
    
    try:
        data = get_company_overview_v2(employee_id, company_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Company Overview Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
