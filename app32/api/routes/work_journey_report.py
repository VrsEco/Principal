from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, current_app, render_template, request, session
from flask_login import current_user

from models import Company, Employee
from services.work_journey_report_service import build_work_journey_management_report
from utils.permissions import get_default_company_id, has_company_full_access, permission_required

work_journey_report_bp = Blueprint('work_journey_report', __name__)


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return date.today()


def _current_employee_id(company_id: int) -> int | None:
    if not getattr(current_user, 'is_authenticated', False):
        return None
    employee = Employee.query.filter_by(company_id=company_id, user_id=current_user.id, status='active').first()
    return employee.id if employee else None


def _hours(minutes: int | float | None) -> float:
    return round(float(minutes or 0) / 60, 2)


def _enrich_report(report: dict) -> dict:
    employees = list(report.get('employees') or [])
    summary = dict(report.get('summary') or {})
    if not employees:
        report['benchmarks'] = {
            'avg_week_occupation_percent': 0,
            'avg_month_occupation_percent': 0,
            'highest_occupation': None,
            'highest_availability': None,
            'most_overloaded': None,
        }
        report['rankings'] = {'occupation': [], 'availability': [], 'overload': [], 'block_pressure': []}
        report['insights'] = []
        return report

    occ_rows = []
    free_rows = []
    overload_rows = []
    block_rows = []
    for row in employees:
        emp = row.get('employee') or {}
        summ = row.get('summary') or {}
        occ_rows.append({'name': emp.get('name', 'Colaborador'), 'department': emp.get('department', 'Sem departamento'), 'value': float(summ.get('occupation_percent_week') or 0), 'occupied_hours': _hours(summ.get('occupied_weekly_minutes')), 'free_hours': _hours(summ.get('free_weekly_minutes'))})
        free_rows.append({'name': emp.get('name', 'Colaborador'), 'department': emp.get('department', 'Sem departamento'), 'value': _hours(summ.get('free_weekly_minutes')), 'occupied_hours': _hours(summ.get('occupied_weekly_minutes'))})
        overload_rows.append({'name': emp.get('name', 'Colaborador'), 'department': emp.get('department', 'Sem departamento'), 'value': _hours(summ.get('overload_weekly_minutes')), 'occupation_percent_week': float(summ.get('occupation_percent_week') or 0)})
        for block in row.get('blocks') or []:
            block_rows.append({'employee_name': emp.get('name', 'Colaborador'), 'block_name': block.get('name', 'Bloco'), 'value': float(block.get('occupation_percent_week') or 0), 'occupied_hours': _hours(block.get('occupied_week')), 'free_hours': _hours(block.get('free_week')), 'mode_label': block.get('mode_label', '')})

    occ_rows.sort(key=lambda item: item['value'], reverse=True)
    free_rows.sort(key=lambda item: item['value'], reverse=True)
    overload_rows.sort(key=lambda item: item['value'], reverse=True)
    block_rows.sort(key=lambda item: item['value'], reverse=True)

    avg_week = round(sum(item['value'] for item in occ_rows) / len(occ_rows), 1)
    avg_month = round(sum(float((row.get('summary') or {}).get('occupation_percent_month') or 0) for row in employees) / len(employees), 1)

    insights = []
    if occ_rows and occ_rows[0]['value'] >= 90:
        insights.append(f"Atenção: {occ_rows[0]['name']} está com {occ_rows[0]['value']:.1f}% de ocupação semanal.")
    if overload_rows and overload_rows[0]['value'] > 0:
        insights.append(f"Há sobrecarga estimada de {overload_rows[0]['value']:.1f}h/semana em {overload_rows[0]['name']}.")
    if free_rows and free_rows[0]['value'] >= 4:
        insights.append(f"Maior folga atual: {free_rows[0]['name']} com {free_rows[0]['value']:.1f}h livres na semana.")
    if block_rows and block_rows[0]['value'] >= 90:
        insights.append(f"Bloco mais pressionado: {block_rows[0]['block_name']} ({block_rows[0]['employee_name']}) com {block_rows[0]['value']:.1f}% de ocupação.")

    report['benchmarks'] = {
        'avg_week_occupation_percent': avg_week,
        'avg_month_occupation_percent': avg_month,
        'highest_occupation': occ_rows[0] if occ_rows else None,
        'highest_availability': free_rows[0] if free_rows else None,
        'most_overloaded': overload_rows[0] if overload_rows else None,
    }
    report['rankings'] = {
        'occupation': occ_rows[:5],
        'availability': free_rows[:5],
        'overload': overload_rows[:5],
        'block_pressure': block_rows[:8],
    }
    report['insights'] = insights
    return report


@work_journey_report_bp.route('/work-journey/report')
@permission_required('processes', 'view')
def work_journey_report_redirect():
    company_id = session.get('active_company_id') or get_default_company_id()
    if not company_id:
        abort(404)
    return work_journey_report_page(company_id)


@work_journey_report_bp.route('/companies/<int:company_id>/work-journey/report')
@permission_required('processes', 'view')
def work_journey_report_page(company_id: int):
    session['active_company_id'] = company_id
    company = Company.query.get_or_404(company_id)
    selected_employee_id = request.args.get('employee_id', type=int)
    selected_department = (request.args.get('department') or '').strip() or None
    anchor = _parse_date(request.args.get('date'))

    if not has_company_full_access(company_id):
        selected_employee_id = _current_employee_id(company_id)
        selected_department = None
        if not selected_employee_id:
            abort(403)

    try:
        report = build_work_journey_management_report(company_id, anchor, department=selected_department, employee_id=selected_employee_id)
        report = _enrich_report(report)
    except ValueError as exc:
        current_app.logger.warning('Falha no relatório gerencial da jornada: company_id=%s employee_id=%s department=%s error=%s', company_id, selected_employee_id, selected_department, exc)
        abort(404, description=str(exc))

    return render_template('modules/my_work/work_journey_report.html', company=company, report=report, can_manage_all=has_company_full_access(company_id))
