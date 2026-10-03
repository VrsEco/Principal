from __future__ import annotations

from datetime import date, datetime

import secrets

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session
from flask_login import current_user, login_required

from models import Company, Employee, Project, Process
from services import google_calendar_service as gcal
from services.agenda_block_view_service import BlockViewError, build_block_view
from services.agenda_telemetry_service import record_events
from services.unified_calendar_service import (
    EVENT_TYPES,
    OVERDUE_SORTS,
    OVERDUE_TYPES,
    UnifiedCalendarError,
    list_overdue,
    list_unified_events,
)
from utils.permissions import (
    active_company_permission_required,
    can_access_company,
    get_active_company_id,
    get_default_company_id,
    has_company_full_access,
)

unified_calendar_bp = Blueprint('unified_calendar', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


def _parse_date(value: str | None) -> date | None:
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _current_employee(company_id: int) -> Employee | None:
    if not current_user.is_authenticated:
        return None
    return Employee.query.filter_by(company_id=company_id, user_id=current_user.id, status='active').first()


@unified_calendar_bp.route('/agenda')
@login_required
def agenda_redirect():
    company_id = get_active_company_id() or get_default_company_id()
    if not company_id:
        abort(404)
    session['active_company_id'] = company_id
    return _render_agenda(company_id)


@unified_calendar_bp.route('/companies/<int:company_id>/agenda')
@active_company_permission_required('processes', 'view')
def agenda_page(company_id: int):
    return _render_agenda(company_id)


def _render_agenda(company_id: int):
    company = Company.query.get_or_404(company_id)
    can_view_all = has_company_full_access(company_id)
    employee = _current_employee(company_id)
    employees = []
    if can_view_all:
        employees = [
            {'id': e.id, 'name': e.name}
            for e in Employee.query.filter_by(company_id=company_id, status='active').order_by(Employee.name.asc())
        ]
    projects = [
        {'id': p.id, 'name': p.name}
        for p in Project.query.filter_by(company_id=company_id).order_by(Project.name.asc()).limit(500)
    ]
    processes = [
        {'id': p.id, 'name': p.name}
        for p in Process.query.filter_by(company_id=company_id).order_by(Process.name.asc()).limit(500)
    ]
    return render_template(
        'modules/agenda/unified_calendar.html',
        company=company,
        can_view_all=can_view_all,
        current_employee_id=employee.id if employee else None,
        boot={'employees': employees, 'projects': projects, 'processes': processes},
        today=date.today().isoformat(),
    )


def _resolve_scope(company_id: int):
    """Resolve o colaborador do escopo pedido. Devolve (employee_id, scope, resposta_de_erro)."""
    scope = str(request.args.get('scope') or 'mine').strip().lower()
    if scope == 'all':
        if not has_company_full_access(company_id):
            return None, scope, (jsonify({'success': False, 'message': 'Acesso negado à visão da empresa.'}), 403)
        return request.args.get('employee_id', type=int), scope, None
    employee = _current_employee(company_id)
    if not employee:
        return None, scope, (jsonify({'success': True, 'events': [], 'items': [], 'total': 0, 'note': 'Usuário sem colaborador vinculado.'}), 200)
    return employee.id, scope, None


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/events', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_events(company_id: int):
    start = _parse_date(request.args.get('start'))
    end = _parse_date(request.args.get('end'))
    if not start or not end:
        return jsonify({'success': False, 'message': 'Informe start e end (AAAA-MM-DD).'}), 400

    employee_id, scope, error = _resolve_scope(company_id)
    if error:
        return error

    raw_types = {t.strip() for t in str(request.args.get('types') or '').split(',') if t.strip()}
    want_google = 'google_event' in raw_types and scope != 'all'
    types = (raw_types & set(EVENT_TYPES)) or (None if not raw_types else set())
    try:
        events = list_unified_events(company_id, start, end, employee_id=employee_id, types=types) if types != set() else []
    except UnifiedCalendarError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500

    payload = {'success': True}
    if want_google:
        try:
            events.extend(gcal.list_google_events(current_user.id, start, end))
            events.sort(key=lambda e: (e['date'], e['time'] or '99:99', e['type'], str(e['id'])))
        except gcal.GoogleCalendarError as exc:
            payload['google_error'] = str(exc)
    payload['events'] = events
    return jsonify(payload)


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/late', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_late(company_id: int):
    """Atrasadas ordenadas (padrão: mais antigas primeiro) e filtradas por tipo."""
    employee_id, _scope, error = _resolve_scope(company_id)
    if error:
        return error
    sort = str(request.args.get('sort') or 'old').strip().lower()
    if sort not in OVERDUE_SORTS:
        return jsonify({'success': False, 'message': 'Ordenação inválida.'}), 400
    raw_types = {t.strip() for t in str(request.args.get('types') or '').split(',') if t.strip()}
    types = (raw_types & set(OVERDUE_TYPES)) if raw_types else None
    try:
        result = list_overdue(company_id, date.today(), employee_id=employee_id, types=types, sort=sort)
    except UnifiedCalendarError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, **result})


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/blocks', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_blocks(company_id: int):
    """Sinais por bloco (Livre/Completo/Acima), somente leitura. Nunca bloqueia nada."""
    start = _parse_date(request.args.get('start'))
    end = _parse_date(request.args.get('end'))
    if not start or not end:
        return jsonify({'success': False, 'message': 'Informe start e end (AAAA-MM-DD).'}), 400
    employee_id, scope, error = _resolve_scope(company_id)
    if error:
        return error
    if not employee_id:
        return jsonify({'success': True, 'days': [], 'note': 'Informe um colaborador.'})
    extra = []
    if scope != 'all':
        try:
            extra = gcal.list_google_events(current_user.id, start, end)
        except gcal.GoogleCalendarError:
            extra = []
    try:
        view = build_block_view(company_id, employee_id, start, end, extra_events=extra)
    except BlockViewError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, **view})


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/telemetry', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_agenda_telemetry(company_id: int):
    """Eventos de uso da Agenda (só nome da ação e detalhe curto, nunca conteúdo dos itens)."""
    payload = request.get_json(silent=True) or {}
    try:
        saved = record_events(company_id, current_user.id, payload.get('device'), payload.get('events') or [])
    except Exception:
        return jsonify({'success': False}), 500
    return jsonify({'success': True, 'saved': saved})


# ---------------------------------------------------------------- Google Calendar
# A conexão é por usuário (vale em todas as empresas); a sincronização é por empresa ou global.
def _user_sync_targets(only_company_id: int | None = None) -> list[tuple[int, int]]:
    """Pares (empresa, colaborador) em que o usuário atua e pode acessar; opcionalmente só uma empresa."""
    query = Employee.query.filter_by(user_id=current_user.id, status='active')
    if only_company_id:
        query = query.filter_by(company_id=only_company_id)
    targets: dict[int, int] = {}
    for employee in query.order_by(Employee.id.asc()):
        company = Company.query.get(employee.company_id)
        if company and getattr(company, 'is_active', True) and can_access_company(employee.company_id):
            targets.setdefault(employee.company_id, employee.id)
    return sorted(targets.items())


@unified_calendar_bp.route('/agenda/google')
@login_required
def google_connection_page():
    company_id = get_active_company_id() or get_default_company_id()
    if not company_id or not can_access_company(company_id):
        abort(403)
    company = Company.query.get_or_404(company_id)
    return render_template(
        'modules/agenda/google_connection.html',
        company=company,
        has_employee=bool(_user_sync_targets()),
        today=date.today().isoformat(),
    )


@unified_calendar_bp.route('/agenda/google/connect')
@login_required
def google_connect():
    if not _user_sync_targets():
        abort(403)
    nonce = secrets.token_urlsafe(16)
    session['gcal_oauth_nonce'] = nonce
    try:
        return redirect(gcal.build_auth_url(current_user.id, nonce))
    except gcal.GoogleCalendarError:
        return redirect('/agenda/google?google=not_configured')


@unified_calendar_bp.route('/agenda/google/callback')
@login_required
def google_callback():
    if request.args.get('error') or not request.args.get('code'):
        return redirect('/agenda/google?google=denied')
    nonce = session.pop('gcal_oauth_nonce', None)
    try:
        state = gcal.parse_state(request.args.get('state', ''))
        if (
            not nonce
            or not secrets.compare_digest(str(state['n']), nonce)
            or int(state['u']) != current_user.id
        ):
            return redirect('/agenda/google?google=invalid')
        gcal.complete_connection(current_user.id, request.args['code'])
    except gcal.GoogleCalendarError as exc:
        current_app.logger.warning('Falha ao concluir conexão Google Calendar: %s', exc)
        return redirect('/agenda/google?google=error')
    return redirect('/agenda/google?google=connected')


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/google/status', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_google_status(company_id: int):
    return jsonify({'success': True, **gcal.check_connection(current_user.id)})


def _run_sync(only_company_id: int | None):
    payload = request.get_json(silent=True) or {}
    start, end = _parse_date(payload.get('start')), _parse_date(payload.get('end'))
    if not start or not end:
        return jsonify({'success': False, 'message': 'Informe start e end (AAAA-MM-DD).'}), 400
    targets = _user_sync_targets(only_company_id)
    if not targets:
        return jsonify({'success': False, 'message': 'Usuário sem colaborador ativo nesta empresa.'}), 400
    try:
        stats = gcal.sync_range(current_user.id, targets, start, end)
    except (gcal.GoogleCalendarError, UnifiedCalendarError) as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, 'stats': stats})


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/google/sync', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_google_sync_company(company_id: int):
    """Sincroniza apenas a empresa ativa."""
    return _run_sync(company_id)


@unified_calendar_bp.route('/api/agenda/google/sync-all', methods=['POST'])
@login_required
def api_google_sync_all():
    """Sincroniza todas as empresas em que o usuário atua."""
    return _run_sync(None)


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/google/disconnect', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_google_disconnect(company_id: int):
    gcal.disconnect(current_user.id)
    return jsonify({'success': True})
