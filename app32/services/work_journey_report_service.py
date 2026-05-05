from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import or_

from models import Employee, Process, Project, ProjectActivityCollaborator, ProjectTask, Routine, RoutineCollaborator, RoutineJourneyBinding, WorkCalendarEvent, WorkJourneyBlock, WorkJourneyItem
from services.work_journey_helpers import BLOCK_MODE_LABELS, ITEM_TYPE_LABELS, block_chronology_key, clamp_period, duration_minutes
from services.work_journey_service import build_item_display_code

CLOSED = {'completed', 'done', 'cancelled', 'canceled', 'archived'}


def build_work_journey_management_report(company_id: int, anchor: date, *, department: str | None = None, employee_id: int | None = None) -> dict:
    week_start, week_end = clamp_period('week', anchor)
    month_start, month_end = clamp_period('month', anchor)
    q = Employee.query.filter_by(company_id=company_id, status='active')
    if employee_id:
        q = q.filter(Employee.id == employee_id)
    elif department:
        q = q.filter(Employee.department == department)
    employees = q.order_by(Employee.name.asc()).all()
    if employee_id and not employees:
        raise ValueError('Colaborador não encontrado para a empresa informada.')
    all_employees = Employee.query.filter_by(company_id=company_id, status='active').order_by(Employee.name.asc()).all()
    departments = [row[0] for row in Employee.query.with_entities(Employee.department).filter(Employee.company_id == company_id, Employee.status == 'active', Employee.department.isnot(None)).distinct().order_by(Employee.department.asc()).all() if row[0]]
    if not employees:
        return {'generated_at': anchor.strftime('%d/%m/%Y'), 'anchor_date': anchor.isoformat(), 'period': _period_payload(anchor, week_start, week_end, month_start, month_end), 'filters': _filters_payload(all_employees, departments, department, employee_id), 'summary': {'employee_count': 0, 'scope_label': 'Sem dados no filtro atual', 'occupied_weekly_minutes': 0, 'free_weekly_minutes': 0, 'effective_weekly_minutes': 0, 'agreed_weekly_minutes': 0, 'occupied_monthly_minutes': 0, 'free_monthly_minutes': 0, 'effective_monthly_minutes': 0, 'agreed_monthly_minutes': 0, 'occupation_percent_week': 0, 'occupation_percent_month': 0, 'routine_weekly_minutes': 0, 'reserved_weekly_minutes': 0, 'project_weekly_minutes': 0, 'process_weekly_minutes': 0, 'meeting_weekly_minutes': 0, 'manual_weekly_minutes': 0, 'unassigned_weekly_minutes': 0}, 'employees': [], 'charts': {'scope_capacity': {'labels': ['Ocupado', 'Livre'], 'values': [0, 0]}, 'scope_mix': {'labels': ['Rotinas', 'Projetos', 'Processos', 'Reuniões', 'Avulsas', 'Reservas', 'Sem bloco'], 'values': [0, 0, 0, 0, 0, 0, 0]}, 'employees_capacity': {'labels': [], 'occupied': [], 'free': []}, 'blocks_capacity': {'labels': [], 'occupied': [], 'free': []}}}

    ids = [int(e.id) for e in employees]
    blocks = WorkJourneyBlock.query.filter(WorkJourneyBlock.company_id == company_id, WorkJourneyBlock.employee_id.in_(ids), WorkJourneyBlock.is_active.is_(True)).all()
    blocks_by_emp, blocks_by_id = defaultdict(list), {}
    for b in blocks:
        blocks_by_emp[int(b.employee_id)].append(b)
        blocks_by_id[int(b.id)] = b
    for arr in blocks_by_emp.values():
        arr.sort(key=block_chronology_key)

    bindings = {(int(b.routine_id), int(b.employee_id)): b for b in RoutineJourneyBinding.query.filter(RoutineJourneyBinding.company_id == company_id, RoutineJourneyBinding.employee_id.in_(ids)).all()}
    routine_rows = RoutineCollaborator.query.join(Routine, Routine.id == RoutineCollaborator.routine_id).filter(Routine.company_id == company_id, RoutineCollaborator.employee_id.in_(ids), Routine.is_active.isnot(False)).all()
    process_ids = sorted({int(r.routine_rel.process_id) for r in routine_rows if getattr(r.routine_rel, 'process_id', None)})
    process_map = {int(p.id): p for p in Process.query.filter(Process.company_id == company_id, Process.id.in_(process_ids)).all()} if process_ids else {}
    items = WorkJourneyItem.query.filter(WorkJourneyItem.company_id == company_id, WorkJourneyItem.employee_id.in_(ids), or_(WorkJourneyItem.occurrence_date.between(month_start, month_end), WorkJourneyItem.due_date.between(month_start, month_end))).all()
    calendar_events = WorkCalendarEvent.query.filter(
        WorkCalendarEvent.company_id == company_id,
        WorkCalendarEvent.employee_id.in_(ids),
        WorkCalendarEvent.event_date.between(month_start, month_end),
    ).all()
    project_items = {int(i.source_id): i for i in items if i.item_type == 'project_task' and i.source_id is not None}
    direct_tasks = ProjectTask.query.join(Project, Project.id == ProjectTask.project_id).filter(Project.company_id == company_id, ProjectTask.employee_id.in_(ids)).all()
    collab_rows = ProjectActivityCollaborator.query.join(ProjectTask, ProjectTask.id == ProjectActivityCollaborator.activity_id).join(Project, Project.id == ProjectTask.project_id).filter(Project.company_id == company_id, ProjectActivityCollaborator.employee_id.in_(ids), ProjectActivityCollaborator.is_deleted.isnot(True)).all()
    projects_by_emp = _build_projects(employees, direct_tasks, collab_rows, project_items, blocks_by_id)
    employees_payload, emp_labels, emp_occ, emp_free, blk_labels, blk_occ, blk_free = [], [], [], [], [], [], []
    totals = defaultdict(int)
    week_days = _business_days(week_start, week_end)
    month_days = _business_days(month_start, month_end)

    for emp in employees:
        emp_id = int(emp.id)
        emp_blocks = blocks_by_emp.get(emp_id, [])
        emp_items = [i for i in items if int(i.employee_id) == emp_id]
        emp_routines = [r for r in routine_rows if int(r.employee_id) == emp_id]
        block_stats = _init_blocks(emp_blocks, week_start, week_end, month_start, month_end)
        groups = {'daily': [], 'weekly': [], 'monthly': [], 'other': []}
        routine_week = routine_month = 0
        for rel in emp_routines:
            routine = rel.routine_rel
            sched = _sched_type(routine.schedule_type)
            m = _routine_metrics(float(rel.hours_used or 0), sched, getattr(routine, 'schedule_value', None))
            routine_week += m['week_min']; routine_month += m['month_min']
            binding = bindings.get((int(routine.id), emp_id))
            block = blocks_by_id.get(int(binding.block_id)) if binding and binding.block_id else None
            if block and int(block.id) in block_stats:
                block_stats[int(block.id)]['occupied_week'] += m['week_min']
                block_stats[int(block.id)]['occupied_month'] += m['month_min']
                block_stats[int(block.id)]['routine_week'] += m['week_min']
            groups[sched if sched in groups else 'other'].append({'routine_id': int(routine.id), 'routine_name': routine.name, 'process_name': process_map.get(int(routine.process_id)).name if getattr(routine, 'process_id', None) and int(routine.process_id) in process_map else None, 'process_code': process_map.get(int(routine.process_id)).code if getattr(routine, 'process_id', None) and int(routine.process_id) in process_map else None, 'schedule_description': _sched_desc(sched, getattr(routine, 'schedule_value', None)), 'weekly_formula_label': m['label'], 'hours_per_occurrence': round(float(rel.hours_used or 0), 2), 'weekly_equivalent_hours': round(m['week_min'] / 60, 2), 'monthly_equivalent_hours': round(m['month_min'] / 60, 2), 'block_name': block.name if block else 'Sem bloco vinculado', 'block_window': _block_window(block), 'notes': binding.notes if binding else None})

        mix = defaultdict(int)
        unassigned_week = unassigned_month = 0
        event_week = event_month = event_week_count = 0
        for item in emp_items:
            target = item.occurrence_date or item.due_date
            if not target:
                continue
            mins = int(item.estimated_minutes or 0)
            in_week = week_start <= target <= week_end
            in_month = month_start <= target <= month_end
            if not in_week and not in_month:
                continue
            if in_week:
                mix[item.item_type] += mins
            if item.block_id and int(item.block_id) in block_stats:
                if in_week:
                    block_stats[int(item.block_id)]['occupied_week'] += mins
                    block_stats[int(item.block_id)]['worked_week'] += int(item.worked_minutes or 0)
                    block_stats[int(item.block_id)]['items_week'] += 1
                if in_month:
                    block_stats[int(item.block_id)]['occupied_month'] += mins
                    block_stats[int(item.block_id)]['worked_month'] += int(item.worked_minutes or 0)
                    block_stats[int(item.block_id)]['items_month'] += 1
            else:
                if in_week:
                    unassigned_week += mins
                if in_month:
                    unassigned_month += mins

        for event in [row for row in calendar_events if int(row.employee_id) == emp_id]:
            target = event.event_date
            if not target:
                continue
            mins = _event_minutes(event)
            in_week = week_start <= target <= week_end
            in_month = month_start <= target <= month_end
            if not in_week and not in_month:
                continue
            if in_week:
                mix['calendar_event'] += mins
                event_week += mins
                event_week_count += 1
            if in_month:
                event_month += mins
            if event.block_id and int(event.block_id) in block_stats:
                if in_week:
                    block_stats[int(event.block_id)]['occupied_week'] += mins
                    block_stats[int(event.block_id)]['events_week'] += 1
                if in_month:
                    block_stats[int(event.block_id)]['occupied_month'] += mins
                    block_stats[int(event.block_id)]['events_month'] += 1
            else:
                if in_week:
                    unassigned_week += mins
                if in_month:
                    unassigned_month += mins

        block_rows = _finalize_blocks(block_stats)
        agreed_week = int(round(float(emp.weekly_hours or 0) * 60)) or sum(b['week_capacity'] for b in block_rows)
        agreed_month = int(round((agreed_week / max(week_days, 1)) * month_days))
        block_week_cap = sum(b['week_capacity'] for b in block_rows)
        block_month_cap = sum(b['month_capacity'] for b in block_rows)
        eff_week = min(agreed_week, block_week_cap) if block_week_cap else agreed_week
        eff_month = min(agreed_month, block_month_cap) if block_month_cap else agreed_month
        occ_week = sum(b['occupied_week'] for b in block_rows) + unassigned_week
        occ_month = sum(b['occupied_month'] for b in block_rows) + unassigned_month
        free_week = max(eff_week - occ_week, 0)
        free_month = max(eff_month - occ_month, 0)
        over_week = max(occ_week - eff_week, 0)
        over_month = max(occ_month - eff_month, 0)
        employees_payload.append({'employee': {'id': emp_id, 'name': emp.name, 'department': emp.department or 'Sem departamento', 'weekly_hours': float(emp.weekly_hours or 0)}, 'summary': {'agreed_weekly_minutes': agreed_week, 'effective_weekly_minutes': eff_week, 'occupied_weekly_minutes': occ_week, 'free_weekly_minutes': free_week, 'overload_weekly_minutes': over_week, 'agreed_monthly_minutes': agreed_month, 'effective_monthly_minutes': eff_month, 'occupied_monthly_minutes': occ_month, 'free_monthly_minutes': free_month, 'overload_monthly_minutes': over_month, 'blocks_weekly_capacity_minutes': block_week_cap, 'blocks_monthly_capacity_minutes': block_month_cap, 'routine_weekly_minutes': routine_week, 'routine_monthly_minutes': routine_month, 'project_weekly_minutes': mix['project_task'], 'process_weekly_minutes': mix['process_instance'], 'meeting_weekly_minutes': mix['meeting'], 'manual_weekly_minutes': mix['manual'], 'event_weekly_minutes': event_week, 'event_monthly_minutes': event_month, 'event_weekly_count': event_week_count, 'unassigned_weekly_minutes': unassigned_week, 'occupation_percent_week': _pct(occ_week, eff_week), 'occupation_percent_month': _pct(occ_month, eff_month)}, 'blocks': block_rows, 'routines': groups, 'projects': projects_by_emp.get(emp_id, []), 'unassigned': {'weekly_minutes': unassigned_week, 'monthly_minutes': unassigned_month}})
        totals['agreed_weekly_minutes'] += agreed_week; totals['effective_weekly_minutes'] += eff_week; totals['occupied_weekly_minutes'] += occ_week; totals['free_weekly_minutes'] += free_week; totals['overload_weekly_minutes'] += over_week
        totals['agreed_monthly_minutes'] += agreed_month; totals['effective_monthly_minutes'] += eff_month; totals['occupied_monthly_minutes'] += occ_month; totals['free_monthly_minutes'] += free_month; totals['overload_monthly_minutes'] += over_month
        totals['routine_weekly_minutes'] += routine_week; totals['reserved_weekly_minutes'] += sum(b['reserved_week'] for b in block_rows); totals['project_weekly_minutes'] += mix['project_task']; totals['process_weekly_minutes'] += mix['process_instance']; totals['meeting_weekly_minutes'] += mix['meeting']; totals['manual_weekly_minutes'] += mix['manual']; totals['event_weekly_minutes'] += event_week; totals['event_weekly_count'] += event_week_count; totals['unassigned_weekly_minutes'] += unassigned_week
        emp_labels.append(emp.name); emp_occ.append(round(occ_week / 60, 2)); emp_free.append(round(free_week / 60, 2))
        for b in block_rows:
            blk_labels.append(f"{emp.name} • {b['name']}"); blk_occ.append(round(b['occupied_week'] / 60, 2)); blk_free.append(round(b['free_week'] / 60, 2))

    top_blocks = sorted(zip(blk_labels, blk_occ, blk_free), key=lambda x: x[1], reverse=True)[:8]
    summary = dict(totals)
    summary.update({'employee_count': len(employees_payload), 'scope_label': _scope(employees_payload, department, employee_id), 'occupation_percent_week': _pct(summary['occupied_weekly_minutes'], summary['effective_weekly_minutes']), 'occupation_percent_month': _pct(summary['occupied_monthly_minutes'], summary['effective_monthly_minutes'])})
    return {'generated_at': anchor.strftime('%d/%m/%Y'), 'anchor_date': anchor.isoformat(), 'period': _period_payload(anchor, week_start, week_end, month_start, month_end), 'filters': _filters_payload(all_employees, departments, department, employee_id), 'summary': summary, 'employees': employees_payload, 'charts': {'scope_capacity': {'labels': ['Ocupado', 'Livre'], 'values': [round(summary['occupied_weekly_minutes'] / 60, 2), round(summary['free_weekly_minutes'] / 60, 2)]}, 'scope_mix': {'labels': ['Rotinas', 'Projetos', 'Processos', 'Reuniões', 'Avulsas', 'Eventos', 'Reservas', 'Sem bloco'], 'values': [round(summary['routine_weekly_minutes'] / 60, 2), round(summary['project_weekly_minutes'] / 60, 2), round(summary['process_weekly_minutes'] / 60, 2), round(summary['meeting_weekly_minutes'] / 60, 2), round(summary['manual_weekly_minutes'] / 60, 2), round(summary['event_weekly_minutes'] / 60, 2), round(summary['reserved_weekly_minutes'] / 60, 2), round(summary['unassigned_weekly_minutes'] / 60, 2)]}, 'employees_capacity': {'labels': emp_labels, 'occupied': emp_occ, 'free': emp_free}, 'blocks_capacity': {'labels': [r[0] for r in top_blocks], 'occupied': [r[1] for r in top_blocks], 'free': [r[2] for r in top_blocks]}}}

def _build_projects(employees, direct_tasks, collab_rows, project_items, blocks_by_id):
    emp_ids = {int(e.id) for e in employees}
    data = defaultdict(dict)
    def ensure(emp_id, task):
        proj_id = int(task.project_id)
        if proj_id not in data[emp_id]:
            data[emp_id][proj_id] = {'project_id': proj_id, 'project_name': task.project.name if task.project else 'Projeto', 'project_code': task.project.code if task.project else None, 'status': getattr(task.project, 'status', None) if task.project else None, 'responsible_activities': [], 'participating_activities': [], 'block_names': set()}
        return data[emp_id][proj_id]
    def activity(task, label):
        item = project_items.get(int(task.id))
        block = blocks_by_id.get(int(item.block_id)) if item and item.block_id else None
        return {'task_id': int(task.id), 'title': task.what, 'display_code': build_item_display_code(item) if item else task.code, 'due_date': task.due_date.isoformat() if task.due_date else None, 'estimated_hours': float(task.estimated_hours or 0), 'role_label': label, 'block_name': block.name if block else 'Sem bloco mapeado'}
    for task in direct_tasks:
        if not _open_task(task) or int(task.employee_id or 0) not in emp_ids:
            continue
        row = ensure(int(task.employee_id), task); a = activity(task, 'Responsável'); row['responsible_activities'].append(a); row['block_names'].add(a['block_name'])
    for rel in collab_rows:
        task = rel.activity
        if not task or not _open_task(task) or int(rel.employee_id or 0) not in emp_ids:
            continue
        row = ensure(int(rel.employee_id), task); role = str(rel.role or 'executor').strip().lower(); a = activity(task, 'Responsável' if role == 'responsible' else 'Participante'); target = row['responsible_activities'] if role == 'responsible' else row['participating_activities']
        if not any(x['task_id'] == a['task_id'] for x in target):
            target.append(a)
        row['block_names'].add(a['block_name'])
    result = {}
    for emp_id, projects in data.items():
        rows = []
        for row in projects.values():
            row['block_names'] = sorted(row['block_names'])
            row['responsible_activities'] = sorted(row['responsible_activities'], key=lambda x: (x['due_date'] or '9999-12-31', x['title'].lower()))
            row['participating_activities'] = sorted(row['participating_activities'], key=lambda x: (x['due_date'] or '9999-12-31', x['title'].lower()))
            row['summary'] = _summarize_project_row(row)
            rows.append(row)
        result[emp_id] = sorted(rows, key=lambda x: ((x.get('project_code') or ''), x['project_name'].lower()))
    return result


def _summarize_project_row(row):
    responsible = list(row.get('responsible_activities') or [])
    participating = list(row.get('participating_activities') or [])
    all_activities = responsible + participating

    def _hours_sum(items):
        return round(sum(float(item.get('estimated_hours') or 0) for item in items), 1)

    def _next_due(items):
        dated = sorted([item.get('due_date') for item in items if item.get('due_date')])
        return dated[0] if dated else None

    total_count = len({int(item['task_id']) for item in all_activities if item.get('task_id') is not None})
    responsible_count = len({int(item['task_id']) for item in responsible if item.get('task_id') is not None})
    participating_count = len({int(item['task_id']) for item in participating if item.get('task_id') is not None})
    responsible_hours = _hours_sum(responsible)
    participating_hours = _hours_sum(participating)
    total_hours = round(responsible_hours + participating_hours, 1)
    next_due = _next_due(all_activities)

    return {
        'responsible_count': responsible_count,
        'participating_count': participating_count,
        'total_count': total_count,
        'responsible_hours': responsible_hours,
        'participating_hours': participating_hours,
        'total_hours': total_hours,
        'next_due': next_due,
        'next_due_label': _format_iso_date(next_due),
        'blocks_label': ', '.join(row.get('block_names') or []) or 'Sem bloco mapeado',
        'status_label': str(row.get('status') or 'ativo').replace('_', ' '),
        'has_direct_responsibility': responsible_count > 0,
    }


def _init_blocks(blocks, week_start, week_end, month_start, month_end):
    out = {}
    for b in blocks:
        week_count, month_count = _block_days(b, week_start, week_end), _block_days(b, month_start, month_end)
        base = duration_minutes(b.start_time, b.end_time)
        week_cap, month_cap = base * week_count, base * month_count
        reserved_week = week_cap if b.block_mode == 'reserved_full' else 0
        reserved_month = month_cap if b.block_mode == 'reserved_full' else 0
        out[int(b.id)] = {'id': int(b.id), 'name': b.name, 'description': b.description, 'mode': b.block_mode, 'mode_label': BLOCK_MODE_LABELS.get(b.block_mode, b.block_mode), 'window_label': _block_window(b), 'weekdays_label': _weekdays(b.weekdays_json or []), 'accepted_types': [ITEM_TYPE_LABELS.get(t, t) for t in (b.accepted_item_types or [])], 'week_capacity': week_cap, 'month_capacity': month_cap, 'reserved_week': reserved_week, 'reserved_month': reserved_month, 'occupied_week': reserved_week, 'occupied_month': reserved_month, 'routine_week': 0, 'worked_week': 0, 'worked_month': 0, 'items_week': 0, 'items_month': 0, 'events_week': 0, 'events_month': 0}
    return out


def _finalize_blocks(stats):
    rows = []
    for b in stats.values():
        rows.append({**b, 'free_week': max(b['week_capacity'] - b['occupied_week'], 0), 'free_month': max(b['month_capacity'] - b['occupied_month'], 0), 'over_week': max(b['occupied_week'] - b['week_capacity'], 0), 'over_month': max(b['occupied_month'] - b['month_capacity'], 0), 'occupation_percent_week': _pct(b['occupied_week'], b['week_capacity']), 'occupation_percent_month': _pct(b['occupied_month'], b['month_capacity'])})
    return sorted(rows, key=lambda x: (x['window_label'] or '', x['name'].lower()))


def _period_payload(anchor, week_start, week_end, month_start, month_end):
    return {'week_start': week_start.isoformat(), 'week_end': week_end.isoformat(), 'month_start': month_start.isoformat(), 'month_end': month_end.isoformat(), 'week_label': f"{week_start.strftime('%d/%m')} a {week_end.strftime('%d/%m')}", 'month_label': anchor.strftime('%m/%Y')}


def _filters_payload(employees, departments, department, employee_id):
    return {'department': department, 'employee_id': employee_id, 'departments': departments, 'employees': [{'id': int(e.id), 'name': e.name} for e in employees]}

def _business_days(start, end):
    total, current = 0, start
    while current <= end:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)
    return total


def _block_days(block, start, end):
    weekdays = list(block.weekdays_json or []) or [0, 1, 2, 3, 4]
    total, current = 0, start
    while current <= end:
        if current.weekday() in weekdays:
            total += 1
        current += timedelta(days=1)
    return total


def _pct(num, den):
    return round((float(num) / float(den)) * 100, 1) if den else 0.0


def _sched_type(value):
    value = str(value or 'weekly').strip().lower()
    return {'diario': 'daily', 'diária': 'daily', 'daily': 'daily', 'week': 'weekly', 'semanal': 'weekly', 'weekly': 'weekly', 'month': 'monthly', 'mensal': 'monthly', 'monthly': 'monthly'}.get(value, value or 'weekly')


def _sched_desc(kind, raw):
    text = str(raw or '').strip()
    if kind == 'daily':
        return 'Todos os dias' if not text else f'Todos os dias ({text})'
    if kind == 'weekly':
        m = {'0': 'domingo', '1': 'segunda', '2': 'terça', '3': 'quarta', '4': 'quinta', '5': 'sexta', '6': 'sábado'}
        vals = [m.get(t.strip(), t.strip()) for t in text.replace(';', ',').replace('|', ',').split(',') if t.strip()]
        return ', '.join(vals) if vals else 'Sem dia fixo informado'
    if kind == 'monthly':
        vals = [f"dia {t.strip()}" for t in text.replace(';', ',').split(',') if t.strip()]
        return ', '.join(vals) if vals else 'Sem dia fixo informado'
    return text or 'Agendamento não informado'


def _routine_metrics(hours, kind, raw):
    factor = 1.0
    if kind == 'daily':
        factor = 5.0
    elif kind == 'weekly':
        factor = float(len([t.strip() for t in str(raw or '').replace(';', ',').replace('|', ',').split(',') if t.strip()]) or 1)
    elif kind == 'monthly':
        factor = float(len([t.strip() for t in str(raw or '').replace(';', ',').split(',') if t.strip()]) or 1) / 4.0
    week_min = int(round(float(hours or 0) * factor * 60))
    month_min = int(round(week_min * 4.0))
    if kind == 'daily':
        label = f'{hours:.1f}h/dia × 5 dias úteis = {week_min / 60:.1f}h/sem'
    elif kind == 'weekly':
        label = f'{hours:.1f}h × {factor:.0f} vez(es)/sem = {week_min / 60:.1f}h/sem'
    elif kind == 'monthly':
        label = f'{hours:.1f}h × {(factor * 4):.0f} vez(es)/mês = {month_min / 60:.1f}h/mês'
    else:
        label = f'{hours:.1f}h por ocorrência'
    return {'week_min': week_min, 'month_min': month_min, 'label': label}


def _scope(payload, department, employee_id):
    if employee_id and payload:
        return f"Colaborador · {payload[0]['employee']['name']}"
    if department:
        return f'Departamento · {department}'
    return 'Empresa inteira'


def _weekdays(days):
    names = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    ordered = [names.get(int(d), str(d)) for d in sorted({int(d) for d in days})]
    return ', '.join(ordered) if ordered else 'Dias úteis'


def _block_window(block):
    return f"{block.start_time.strftime('%H:%M')} às {block.end_time.strftime('%H:%M')}" if block and block.start_time and block.end_time else None


def _open_task(task):
    return str(task.status or '').strip().lower() not in CLOSED and str(task.stage or '').strip().lower() not in CLOSED


def _format_iso_date(raw):
    if not raw:
        return 'Sem prazo definido'
    try:
        year, month, day = str(raw).split('-')[:3]
        return f'{day}/{month}/{year}'
    except ValueError:
        return str(raw)


def _event_minutes(event):
    if getattr(event, 'start_time', None) and getattr(event, 'end_time', None):
        start = (event.start_time.hour * 60) + event.start_time.minute
        end = (event.end_time.hour * 60) + event.end_time.minute
        return max(end - start, 0)
    metadata = dict(getattr(event, 'metadata_json', None) or {})
    return max(int(metadata.get('duration_minutes') or 0), 0)
