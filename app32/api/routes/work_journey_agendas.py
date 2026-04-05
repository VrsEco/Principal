from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user
from pydantic import ValidationError

from models import Employee, WorkJourneyAgenda, WorkJourneyAgendaItem
from schemas.work_journey import (
    WorkJourneyAgendaGenerateSchema,
    WorkJourneyAgendaLockSchema,
    WorkJourneyAgendaMoveSchema,
)
from services.work_journey_agenda_pdf_service import generate_work_journey_agenda_pdf
from services.work_journey_agenda_service import (
    get_work_journey_agenda,
    lock_work_journey_agenda,
    move_work_journey_agenda_item,
    unlock_work_journey_agenda,
)
from services.work_journey_base import WorkJourneyError
from utils.permissions import has_company_full_access, permission_required


work_journey_agendas_bp = Blueprint('work_journey_agendas', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


def _format_validation_error(exc: ValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors():
        location = ' → '.join(str(part) for part in (error.get('loc') or []) if part not in {None, '__root__'})
        message = str(error.get('msg') or 'Valor inválido.')
        messages.append(f'{location}: {message}' if location else message)
    return '; '.join(messages) or 'Dados inválidos.'


def _parse_date(raw_value: str | None) -> date | None:
    if not raw_value:
        return None
    try:
        return date.fromisoformat(str(raw_value))
    except ValueError:
        return None


def _normalize_scope(raw_value: str | None) -> str:
    scope = str(raw_value or 'week').strip().lower()
    return scope if scope in {'day', 'week'} else 'week'


def _current_employee_id(company_id: int) -> int | None:
    if not getattr(current_user, 'is_authenticated', False):
        return None
    employee = Employee.query.filter_by(company_id=company_id, user_id=current_user.id, status='active').first()
    return employee.id if employee else None


def _can_manage_employee(company_id: int, employee_id: int) -> bool:
    return bool(has_company_full_access(company_id) or _current_employee_id(company_id) == employee_id)


def _agenda_context_from_item(company_id: int, agenda_item_id: int) -> WorkJourneyAgendaItem:
    agenda_item = WorkJourneyAgendaItem.query.filter_by(company_id=company_id, id=agenda_item_id).first()
    if not agenda_item:
        raise WorkJourneyError('Item da agenda não encontrado.')
    if not agenda_item.agenda:
        raise WorkJourneyError('Agenda não encontrada para o item informado.')
    return agenda_item


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas', methods=['GET'])
@permission_required('processes', 'view')
def api_get_agenda(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int) or _current_employee_id(company_id)
        if not employee_id:
            return jsonify({'success': False, 'message': 'Informe o colaborador da agenda.'}), 400
        if not _can_manage_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403

        anchor = _parse_date(request.args.get('date') or request.args.get('anchor_date')) or date.today()
        scope = _normalize_scope(request.args.get('scope'))
        payload = get_work_journey_agenda(company_id, employee_id, anchor, scope, False)
        return jsonify({'success': True, 'data': payload})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas/generate', methods=['POST'])
@permission_required('processes', 'view')
def api_generate_agenda(company_id: int):
    try:
        raw_payload = request.get_json(silent=True) or {}
        raw_payload.setdefault('employee_id', _current_employee_id(company_id))
        if raw_payload.get('date') and not raw_payload.get('anchor_date'):
            raw_payload['anchor_date'] = raw_payload['date']
        raw_payload.pop('date', None)
        payload = WorkJourneyAgendaGenerateSchema.model_validate(raw_payload).model_dump(exclude_unset=True)
        employee_id = payload['employee_id']
        if not _can_manage_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Você não pode gerar a agenda deste colaborador.'}), 403

        anchor = payload.get('anchor_date') or date.today()
        scope = _normalize_scope(payload.get('scope'))
        existing = WorkJourneyAgenda.query.filter_by(
            company_id=company_id,
            employee_id=employee_id,
            anchor_date=anchor,
            scope=scope,
        ).first()
        if existing and existing.status == 'locked':
            return jsonify({'success': False, 'message': 'A agenda está travada. Destrave para regenerar.'}), 400

        agenda = get_work_journey_agenda(company_id, employee_id, anchor, scope, True)
        return jsonify({'success': True, 'data': agenda})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': _format_validation_error(exc), 'details': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas/<int:agenda_id>/lock', methods=['POST'])
@permission_required('processes', 'view')
def api_lock_agenda(company_id: int, agenda_id: int):
    try:
        agenda = WorkJourneyAgenda.query.filter_by(company_id=company_id, id=agenda_id).first()
        if not agenda:
            return jsonify({'success': False, 'message': 'Agenda não encontrada.'}), 404
        if not _can_manage_employee(company_id, agenda.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode travar a agenda deste colaborador.'}), 403

        payload = WorkJourneyAgendaLockSchema.model_validate(request.get_json(silent=True) or {}).model_dump(exclude_unset=True)
        data = lock_work_journey_agenda(company_id, agenda.employee_id, agenda.anchor_date, agenda.scope, getattr(current_user, 'id', None))
        if payload.get('notes'):
            data.setdefault('agenda', {})['notes'] = payload['notes']
        return jsonify({'success': True, 'data': data})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': _format_validation_error(exc), 'details': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas/<int:agenda_id>/unlock', methods=['POST'])
@permission_required('processes', 'view')
def api_unlock_agenda(company_id: int, agenda_id: int):
    try:
        agenda = WorkJourneyAgenda.query.filter_by(company_id=company_id, id=agenda_id).first()
        if not agenda:
            return jsonify({'success': False, 'message': 'Agenda não encontrada.'}), 404
        if not _can_manage_employee(company_id, agenda.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode destravar a agenda deste colaborador.'}), 403

        data = unlock_work_journey_agenda(company_id, agenda.employee_id, agenda.anchor_date, agenda.scope)
        return jsonify({'success': True, 'data': data})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas/items/<int:agenda_item_id>', methods=['PATCH'])
@permission_required('processes', 'view')
def api_move_agenda_item(company_id: int, agenda_item_id: int):
    try:
        agenda_item = _agenda_context_from_item(company_id, agenda_item_id)
        if not _can_manage_employee(company_id, agenda_item.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode mover itens desta agenda.'}), 403

        raw_payload = dict(request.get_json(silent=True) or {})
        legacy_target_date = raw_payload.pop('due_date', None) or raw_payload.pop('agenda_date', None) or raw_payload.pop('date', None)
        legacy_block_id_present = 'block_id' in raw_payload
        legacy_block_id = raw_payload.pop('block_id', None)
        if not raw_payload.get('target_date') and legacy_target_date is not None:
            raw_payload['target_date'] = legacy_target_date
        if raw_payload.get('target_block_id') is None and legacy_block_id_present:
            raw_payload['target_block_id'] = legacy_block_id
        payload = WorkJourneyAgendaMoveSchema.model_validate(raw_payload).model_dump(exclude_unset=True)
        if not payload.get('target_date'):
            return jsonify({'success': False, 'message': 'Informe a data de destino.'}), 400

        data = move_work_journey_agenda_item(
            company_id,
            agenda_item.employee_id,
            agenda_item.agenda.anchor_date,
            agenda_item.agenda.scope,
            agenda_item_id,
            {
                'target_date': payload['target_date'],
                'block_id': payload.get('target_block_id'),
                'source_scope': payload.get('source_scope'),
                'confirm_date_change': bool(payload.get('confirm_date_change')),
                'notes': payload.get('notes'),
                'position_index': payload.get('position_index', 0),
            },
        )
        return jsonify({'success': True, 'data': data})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': _format_validation_error(exc), 'details': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_agendas_bp.route('/api/companies/<int:company_id>/work-journey/agendas/<int:agenda_id>/pdf', methods=['GET'])
@permission_required('processes', 'view')
def api_agenda_pdf(company_id: int, agenda_id: int):
    try:
        agenda = WorkJourneyAgenda.query.filter_by(company_id=company_id, id=agenda_id).first()
        if not agenda:
            return jsonify({'success': False, 'message': 'Agenda não encontrada.'}), 404
        if not _can_manage_employee(company_id, agenda.employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado à agenda informada.'}), 403

        pdf_bytes = generate_work_journey_agenda_pdf(company_id, agenda.employee_id, agenda.anchor_date, agenda.scope)
        filename = f'agenda-jornada-{agenda.employee_id}-{agenda.anchor_date.isoformat()}-{agenda.scope}.pdf'
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=filename,
            max_age=0,
        )
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500
