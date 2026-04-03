from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, jsonify, render_template, request, session
from flask_login import current_user
from pydantic import ValidationError

from models import Company, Employee, WorkJourneyBlock, WorkJourneyItem, WorkJourneyRule
from schemas.work_journey import (
    WorkJourneyAbsenceApprovalSchema,
    WorkJourneyAbsenceRequestCreateSchema,
    WorkJourneyBlockCreateSchema,
    WorkJourneyBlockUpdateSchema,
    WorkJourneyItemUpdateSchema,
    WorkJourneyRuleCreateSchema,
    WorkJourneyRuleUpdateSchema,
    WorkJourneyTransferApprovalSchema,
    WorkJourneyTransferRequestCreateSchema,
)
from services.work_journey_admin_service import (
    approve_absence_request,
    approve_transfer_request,
    create_absence_request,
    create_transfer_request,
    list_absence_requests,
    list_transfer_requests,
)
from services.work_journey_service import (
    WorkJourneyError,
    delete_block,
    delete_rule,
    get_work_journey_board,
    list_employee_blocks,
    list_employee_rules,
    save_block,
    save_rule,
    update_work_item,
)
from utils.permissions import (
    get_default_company_id,
    has_company_full_access,
    permission_required,
)


work_journey_bp = Blueprint('work_journey', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


@work_journey_bp.route('/work-journey')
@permission_required('processes', 'view')
def work_journey_redirect():
    company_id = session.get('active_company_id') or get_default_company_id()
    if not company_id:
        abort(404)
    session['active_company_id'] = company_id
    return _render_work_journey_page(company_id)


@work_journey_bp.route('/companies/<int:company_id>/work-journey')
@permission_required('processes', 'view')
def work_journey_page(company_id: int):
    session['active_company_id'] = company_id
    return _render_work_journey_page(company_id)


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/board')
@permission_required('processes', 'view')
def api_get_work_journey_board(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int) or _current_employee_id(company_id)
        if not employee_id:
            return jsonify({'success': False, 'message': 'Selecione um colaborador.'}), 400
        if not _can_access_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403
        anchor = _parse_date(request.args.get('date')) or date.today()
        scope = str(request.args.get('scope') or 'day').strip().lower()
        payload = get_work_journey_board(company_id, employee_id, anchor, scope)
        return jsonify({'success': True, 'data': payload})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/blocks', methods=['GET'])
@permission_required('processes', 'view')
def api_list_blocks(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int) or _current_employee_id(company_id)
        if not employee_id or not _can_access_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403
        return jsonify({'success': True, 'blocks': list_employee_blocks(company_id, employee_id)})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/blocks', methods=['POST'])
@permission_required('processes', 'view')
def api_create_block(company_id: int):
    return _save_block(company_id)


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/blocks/<int:block_id>', methods=['PUT'])
@permission_required('processes', 'view')
def api_update_block(company_id: int, block_id: int):
    return _save_block(company_id, block_id)


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/blocks/<int:block_id>', methods=['DELETE'])
@permission_required('processes', 'view')
def api_delete_block(company_id: int, block_id: int):
    try:
        block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id).first()
        if not block:
            return jsonify({'success': False, 'message': 'Bloco não encontrado.'}), 404
        if not _can_manage_employee(company_id, block.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode excluir blocos deste colaborador.'}), 403
        delete_block(company_id, block_id)
        return jsonify({'success': True})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/rules', methods=['GET'])
@permission_required('processes', 'view')
def api_list_rules(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int) or _current_employee_id(company_id)
        if not employee_id or not _can_access_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403
        return jsonify({'success': True, 'rules': list_employee_rules(company_id, employee_id)})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/rules', methods=['POST'])
@permission_required('processes', 'view')
def api_create_rule(company_id: int):
    return _save_rule(company_id)


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/rules/<int:rule_id>', methods=['PUT'])
@permission_required('processes', 'view')
def api_update_rule(company_id: int, rule_id: int):
    return _save_rule(company_id, rule_id)


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/rules/<int:rule_id>', methods=['DELETE'])
@permission_required('processes', 'view')
def api_delete_rule(company_id: int, rule_id: int):
    try:
        rule = WorkJourneyRule.query.filter_by(company_id=company_id, id=rule_id).first()
        if not rule:
            return jsonify({'success': False, 'message': 'Obrigação recorrente não encontrada.'}), 404
        if not _can_manage_employee(company_id, rule.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode excluir obrigações deste colaborador.'}), 403
        delete_rule(company_id, rule_id)
        return jsonify({'success': True})
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/items/<int:item_id>', methods=['PATCH'])
@permission_required('processes', 'view')
def api_update_item(company_id: int, item_id: int):
    try:
        item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
        if not item:
            return jsonify({'success': False, 'message': 'Atividade não encontrada.'}), 404
        if not _can_manage_employee(company_id, item.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode atualizar esta atividade.'}), 403
        payload = WorkJourneyItemUpdateSchema.model_validate(request.get_json(silent=True) or {}).model_dump(exclude_unset=True)
        data = update_work_item(company_id, item_id, payload)
        return jsonify({'success': True, 'item': data})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/items/<int:item_id>/transfer', methods=['POST'])
@permission_required('processes', 'view')
def api_create_transfer_request(company_id: int, item_id: int):
    try:
        item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
        if not item:
            return jsonify({'success': False, 'message': 'Atividade não encontrada.'}), 404
        if not _can_manage_employee(company_id, item.employee_id):
            return jsonify({'success': False, 'message': 'Você não pode transferir esta atividade.'}), 403
        payload = WorkJourneyTransferRequestCreateSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        transfer = create_transfer_request(company_id, item_id, payload['to_employee_id'], payload.get('reason'), getattr(current_user, 'id', None))
        return jsonify({'success': True, 'transfer': transfer}), 201
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/transfers', methods=['GET'])
@permission_required('processes', 'view')
def api_list_transfers(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int)
        if employee_id and not _can_access_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403
        return jsonify({'success': True, 'transfers': list_transfer_requests(company_id, employee_id)})
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/transfers/<int:request_id>/approve', methods=['POST'])
@permission_required('processes', 'view')
def api_approve_transfer(company_id: int, request_id: int):
    if not has_company_full_access(company_id):
        return jsonify({'success': False, 'message': 'Somente gestores/administradores podem aprovar transferências.'}), 403
    try:
        payload = WorkJourneyTransferApprovalSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        transfer = approve_transfer_request(company_id, request_id, getattr(current_user, 'id', None), payload.get('resolution_notes'))
        return jsonify({'success': True, 'transfer': transfer})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/absences', methods=['GET'])
@permission_required('processes', 'view')
def api_list_absences(company_id: int):
    try:
        employee_id = request.args.get('employee_id', type=int)
        if employee_id and not _can_access_employee(company_id, employee_id):
            return jsonify({'success': False, 'message': 'Acesso negado ao colaborador informado.'}), 403
        return jsonify({'success': True, 'absences': list_absence_requests(company_id, employee_id)})
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/absences', methods=['POST'])
@permission_required('processes', 'view')
def api_create_absence(company_id: int):
    try:
        payload = WorkJourneyAbsenceRequestCreateSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        if not _can_manage_employee(company_id, payload['employee_id']):
            return jsonify({'success': False, 'message': 'Você não pode solicitar ausência para este colaborador.'}), 403
        absence = create_absence_request(company_id, payload, getattr(current_user, 'id', None))
        return jsonify({'success': True, 'absence': absence}), 201
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500


@work_journey_bp.route('/api/companies/<int:company_id>/work-journey/absences/<int:request_id>/approve', methods=['POST'])
@permission_required('processes', 'view')
def api_approve_absence(company_id: int, request_id: int):
    if not has_company_full_access(company_id):
        return jsonify({'success': False, 'message': 'Somente gestores/administradores podem aprovar ausências.'}), 403
    try:
        payload = WorkJourneyAbsenceApprovalSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        absence = approve_absence_request(company_id, request_id, getattr(current_user, 'id', None), payload.get('cleanup_notes'))
        return jsonify({'success': True, 'absence': absence})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500



def _render_work_journey_page(company_id: int):
    company = Company.query.get_or_404(company_id)
    employees = Employee.query.filter_by(company_id=company_id, status='active').order_by(Employee.name.asc()).all()
    current_employee_id = _current_employee_id(company_id)
    selected_employee_id = request.args.get('employee_id', type=int) or current_employee_id or (employees[0].id if employees else None)
    if selected_employee_id and not _can_access_employee(company_id, selected_employee_id):
        abort(403)
    return render_template(
        'modules/my_work/work_journey.html',
        company=company,
        employees=employees,
        employees_payload=[employee.to_dict() for employee in employees],
        selected_employee_id=selected_employee_id,
        can_manage_all=has_company_full_access(company_id),
        today=date.today().isoformat(),
    )



def _save_block(company_id: int, block_id: int | None = None):
    try:
        schema = WorkJourneyBlockUpdateSchema if block_id else WorkJourneyBlockCreateSchema
        payload = schema.model_validate(request.get_json(silent=True) or {}).model_dump()
        if not _can_manage_employee(company_id, payload['employee_id']):
            return jsonify({'success': False, 'message': 'Você não pode editar blocos deste colaborador.'}), 403
        block = save_block(company_id, payload, block_id)
        return jsonify({'success': True, 'block': block})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500



def _save_rule(company_id: int, rule_id: int | None = None):
    try:
        schema = WorkJourneyRuleUpdateSchema if rule_id else WorkJourneyRuleCreateSchema
        payload = schema.model_validate(request.get_json(silent=True) or {}).model_dump()
        if not _can_manage_employee(company_id, payload['employee_id']):
            return jsonify({'success': False, 'message': 'Você não pode editar obrigações deste colaborador.'}), 403
        rule = save_rule(company_id, payload, rule_id)
        return jsonify({'success': True, 'rule': rule})
    except ValidationError as exc:
        return jsonify({'success': False, 'message': exc.errors()}), 400
    except WorkJourneyError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'message': PUBLIC_ERROR_MESSAGE}), 500



def _parse_date(raw_value: str | None) -> date | None:
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date()
    except ValueError:
        return None



def _current_employee_id(company_id: int) -> int | None:
    if not current_user.is_authenticated:
        return None
    employee = Employee.query.filter_by(company_id=company_id, user_id=current_user.id, status='active').first()
    return employee.id if employee else None



def _can_manage_employee(company_id: int, employee_id: int) -> bool:
    return bool(has_company_full_access(company_id) or _current_employee_id(company_id) == employee_id)



def _can_access_employee(company_id: int, employee_id: int) -> bool:
    return bool(has_company_full_access(company_id) or _current_employee_id(company_id) == employee_id)
