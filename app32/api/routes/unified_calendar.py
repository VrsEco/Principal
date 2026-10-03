from __future__ import annotations

from datetime import date, datetime

import secrets

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session
from flask_login import current_user, login_required

from models import Company, Employee, Project, ProjectTask, Process, db
from services import google_calendar_service as gcal
from services.agenda_block_view_service import BlockViewError, build_block_view
from services import block_assignment_service as assignment
from services import block_migration_service as migration
from services.team_block_signal_service import build_team_view
from services.agenda_requests_service import list_requests
from services import person_work_block_service as person_blocks
from services.agenda_telemetry_service import record_events
from services.work_journey_base import WorkJourneyError
from services.estimate_batch_service import ESTIMATE_TYPES, EstimateError, list_without_estimate, save_estimates
from services.project_task_due_date_change_service import ProjectTaskDueDateChangeService
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
    has_permission,
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
        boot={'employees': employees, 'projects': projects, 'processes': processes, 'person_blocks': person_blocks.has_blocks(current_user.id)},
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
        view = build_block_view(company_id, employee_id, start, end, extra_events=extra, viewer_user_id=(current_user.id if scope != 'all' else None), allowed_company_ids=_allowed_company_ids())
    except BlockViewError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, **view})


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/estimates', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_estimates(company_id: int):
    """Itens abertos sem estimativa (prazo mais próximo primeiro). `limit=1` serve de contador."""
    employee_id, _scope, error = _resolve_scope(company_id)
    if error:
        return error
    raw_types = {t.strip() for t in str(request.args.get('types') or '').split(',') if t.strip()}
    types = (raw_types & set(ESTIMATE_TYPES)) if raw_types else None
    try:
        result = list_without_estimate(company_id, employee_id=employee_id, types=types, limit=request.args.get('limit', type=int) or 200)
    except EstimateError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, **result})


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/estimates', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_agenda_save_estimates(company_id: int):
    """Grava estimativas em lote; cada item respeita a permissão de edição própria."""
    payload = request.get_json(silent=True) or {}
    employee = _current_employee(company_id)
    full_edit = has_permission(company_id, 'processes', 'edit')

    def can_edit_task(task, project):
        return ProjectTaskDueDateChangeService.user_can_apply_due_date_change(task, project, company_id)

    def can_edit_instance(instance):
        if full_edit:
            return True
        return bool(employee and employee.id in {instance.owner_employee_id, instance.responsible_id, instance.executor_id})

    try:
        result = save_estimates(company_id, payload.get('entries') or [], can_edit_task=can_edit_task, can_edit_instance=can_edit_instance)
    except EstimateError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({'success': True, **result})


def _planning_employee(company_id: int):
    """Colaborador do planejamento (escrita): o próprio, ou o informado por quem vê a empresa toda."""
    scope = str(request.args.get('scope') or (request.get_json(silent=True) or {}).get('scope') or 'mine').strip().lower()
    if scope == 'all':
        if not has_company_full_access(company_id):
            return None, (jsonify({'success': False, 'message': 'Acesso negado à visão da empresa.'}), 403)
        employee_id = request.args.get('employee_id', type=int) or (request.get_json(silent=True) or {}).get('employee_id')
        if not employee_id:
            return None, (jsonify({'success': False, 'message': 'Informe o colaborador.'}), 400)
        return int(employee_id), None
    employee = _current_employee(company_id)
    if not employee:
        return None, (jsonify({'success': False, 'message': 'Usuário sem colaborador vinculado.'}), 400)
    return employee.id, None


def _viewer_user_id():
    """Só quem opera a PRÓPRIA agenda usa os blocos da pessoa; o gestor segue isolado por empresa."""
    scope = str(request.args.get('scope') or (request.get_json(silent=True) or {}).get('scope') or 'mine').strip().lower()
    return current_user.id if scope != 'all' and current_user.is_authenticated else None


def _allowed_company_ids() -> set[int]:
    """Empresas em que o usuário logado ainda pode ver a Agenda (vínculo ativo + permissão processes:view)."""
    if not current_user.is_authenticated:
        return set()
    ids = {e.company_id for e in Employee.query.filter_by(user_id=current_user.id, status='active')}
    return {cid for cid in ids if has_permission(cid, 'processes', 'view')}


def _planning_call(fn):
    try:
        return jsonify({'success': True, **fn()})
    except (assignment.AssignmentError, WorkJourneyError) as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception('agenda planning call failed')
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/move-options', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_move_options(company_id: int):
    """Até 5 destinos para o item, com o estado atual do bloco e o que ficaria."""
    employee_id, error = _planning_employee(company_id)
    if error:
        return error
    source_type = str(request.args.get('type') or '')
    source_id = request.args.get('id', type=int)
    if not source_id:
        return jsonify({'success': False, 'message': 'Informe o item.'}), 400
    def build():
        data = assignment.move_options(company_id, employee_id, source_type, source_id, viewer_user_id=_viewer_user_id(), allowed_company_ids=_allowed_company_ids())
        if source_type == 'project_task':
            task = ProjectTask.query.get(source_id)
            project = Project.query.filter_by(id=task.project_id, company_id=company_id).first() if task else None
            data['due_change_applies_now'] = bool(task and project and ProjectTaskDueDateChangeService.user_can_apply_due_date_change(task, project, company_id))
        return data

    return _planning_call(build)


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/assign', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_agenda_assign(company_id: int):
    """Atribui o item a um bloco/dia. Atividade em outro dia exige motivo e usa o fluxo de prazo."""
    employee_id, error = _planning_employee(company_id)
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    target = _parse_date(payload.get('date'))
    block_id = payload.get('block_id')
    source_id = payload.get('id')
    if not target or not block_id or not source_id:
        return jsonify({'success': False, 'message': 'Informe item, data e bloco.'}), 400
    return _planning_call(lambda: assignment.assign_item(
        company_id, employee_id, str(payload.get('type') or ''), int(source_id), target, int(block_id), reason=payload.get('reason'), viewer_user_id=_viewer_user_id()))


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/suggestions', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_suggestions(company_id: int):
    """Prévia da distribuição sugerida para o dia (não grava nada)."""
    employee_id, error = _planning_employee(company_id)
    if error:
        return error
    target = _parse_date(request.args.get('date'))
    if not target:
        return jsonify({'success': False, 'message': 'Informe a data (AAAA-MM-DD).'}), 400
    return _planning_call(lambda: assignment.suggest_distribution(company_id, employee_id, target, viewer_user_id=_viewer_user_id(), allowed_company_ids=_allowed_company_ids()))


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/suggestions', methods=['POST'])
@active_company_permission_required('processes', 'view')
def api_agenda_suggestions_action(company_id: int):
    """Aplica, aceita ou desfaz a sugestão do dia. Desfazer remove só o que o sistema sugeriu."""
    employee_id, error = _planning_employee(company_id)
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    target = _parse_date(payload.get('date'))
    action = str(payload.get('action') or '')
    handlers = {'apply': assignment.apply_suggestions, 'accept': assignment.accept_suggestions, 'undo': assignment.undo_suggestions}
    if not target or action not in handlers:
        return jsonify({'success': False, 'message': 'Informe a data e a ação (apply, accept ou undo).'}), 400
    return _planning_call(lambda: handlers[action](company_id, employee_id, target, viewer_user_id=_viewer_user_id(), allowed_company_ids=_allowed_company_ids()))


def _own_call(fn):
    """Chamada de serviço dos blocos da PESSOA: sempre sobre o próprio usuário logado."""
    try:
        return jsonify({'success': True, **fn(current_user.id)})
    except person_blocks.PersonBlockError as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception('person blocks call failed')
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@unified_calendar_bp.route('/api/agenda/person-blocks', methods=['GET'])
@login_required
def api_person_blocks_list():
    return _own_call(lambda uid: {**person_blocks.list_blocks(uid), 'has_blocks': person_blocks.has_blocks(uid)})


@unified_calendar_bp.route('/api/agenda/person-blocks', methods=['POST'])
@login_required
def api_person_blocks_create():
    payload = request.get_json(silent=True) or {}
    return _own_call(lambda uid: person_blocks.create_block(uid, payload))


@unified_calendar_bp.route('/api/agenda/person-blocks/<int:block_id>', methods=['PATCH'])
@login_required
def api_person_blocks_update(block_id: int):
    payload = request.get_json(silent=True) or {}
    return _own_call(lambda uid: person_blocks.update_block(uid, block_id, payload))


@unified_calendar_bp.route('/api/agenda/person-blocks/<int:block_id>', methods=['DELETE'])
@login_required
def api_person_blocks_delete(block_id: int):
    return _own_call(lambda uid: person_blocks.delete_block(uid, block_id))


@unified_calendar_bp.route('/api/agenda/person-blocks/reorder', methods=['POST'])
@login_required
def api_person_blocks_reorder():
    payload = request.get_json(silent=True) or {}
    return _own_call(lambda uid: person_blocks.reorder_blocks(uid, [int(i) for i in (payload.get('ids') or [])]))


@unified_calendar_bp.route('/api/agenda/person-blocks/migration', methods=['GET'])
@login_required
def api_person_blocks_migration_proposal():
    """Proposta do assistente: lista única a partir dos blocos de todas as empresas do usuário. Não grava nada."""
    return _own_call(migration.propose)


@unified_calendar_bp.route('/api/agenda/person-blocks/migration/apply', methods=['POST'])
@login_required
def api_person_blocks_migration_apply():
    payload = request.get_json(silent=True) or {}
    return _own_call(lambda uid: migration.apply(uid, payload.get('decisions') or []))


@unified_calendar_bp.route('/api/agenda/person-blocks/migration/revert', methods=['POST'])
@login_required
def api_person_blocks_migration_revert():
    """Volta aos blocos por empresa. Os blocos legados nunca foram alterados."""
    return _own_call(migration.revert)


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/team', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_team(company_id: int):
    """Sinais por bloco da equipe (só gestor). Itens de outras empresas saem apenas como minutos."""
    if not has_company_full_access(company_id):
        return jsonify({'success': False, 'message': 'Acesso negado à visão da equipe.'}), 403
    start = _parse_date(request.args.get('start'))
    end = _parse_date(request.args.get('end'))
    if not start or not end:
        return jsonify({'success': False, 'message': 'Informe start e end (AAAA-MM-DD).'}), 400
    try:
        return jsonify({'success': True, **build_team_view(company_id, start, end)})
    except BlockViewError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        current_app.logger.exception('agenda team view failed')
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@unified_calendar_bp.route('/api/companies/<int:company_id>/agenda/requests', methods=['GET'])
@active_company_permission_required('processes', 'view')
def api_agenda_requests(company_id: int):
    """Ausências e transferências com escopo: o colaborador vê as próprias; o gestor, as da empresa (e o total de pendentes)."""
    employee = _current_employee(company_id)
    try:
        return jsonify({'success': True, **list_requests(company_id, viewer_employee_id=employee.id if employee else None, is_manager=has_company_full_access(company_id))})
    except Exception:
        current_app.logger.exception('agenda requests failed')
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


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
