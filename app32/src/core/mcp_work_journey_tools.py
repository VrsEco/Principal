from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app import create_app
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
    WorkJourneyBoardItem,
    WorkJourneyBoardPayload,
    WorkJourneyBoardQuery,
)
from schemas.work_journey import (
    WorkJourneyAbsenceApprovalSchema,
    WorkJourneyAbsenceRequestCreateSchema,
    WorkJourneyAgendaGenerateSchema,
    WorkJourneyAgendaMoveSchema,
    WorkJourneyBlockCreateSchema,
    WorkJourneyBlockUpdateSchema,
    WorkJourneyManualTaskCreateSchema,
    WorkJourneyItemUpdateSchema,
    WorkJourneyRuleCreateSchema,
    WorkJourneyRuleUpdateSchema,
    WorkJourneyTransferApprovalSchema,
    WorkJourneyTransferRequestCreateSchema,
)
from schemas.routine_journey import RoutineJourneyBindingUpsertSchema
from services.routine_journey_binding_service import (
    list_employee_process_routines,
    list_routine_bindings_context,
    save_routine_binding,
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
    create_manual_task,
    delete_work_item,
    delete_block,
    delete_rule,
    get_work_journey_board,
    list_employee_blocks,
    list_manual_tasks,
    list_employee_rules,
    save_block,
    save_rule,
    update_work_item,
)
from services.work_journey_agenda_service import (
    get_work_journey_agenda,
    lock_work_journey_agenda,
    move_work_journey_agenda_item,
    unlock_work_journey_agenda,
)


def _run(callback, *args, **kwargs) -> Any:
    app = create_app()
    with app.app_context():
        return callback(*args, **kwargs)


def _meta(operation: str) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain='work_journey',
        operation=operation,
        scope='mcp_user',
        capability=f'work_journey.{operation}',
        permissions=['work_journey.read'],
        tags=['work-journey', 'routine'],
        human_gate_required=False,
    )


def _success_envelope(*, operation: str, data: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation),
        message=message or 'Operação work_journey concluída com sucesso.',
    ).model_dump(mode='json')


def _error_envelope(*, operation: str, message: str, code: str = 'work_journey_error', details: dict[str, Any] | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message, details=details or {}),
        meta=_meta(operation),
    ).model_dump(mode='json')


def _normalize_board_item(raw_item: dict[str, Any]) -> WorkJourneyBoardItem:
    title = raw_item.get('display_title') or raw_item.get('title') or 'Item sem título'
    return WorkJourneyBoardItem(
        item_id=raw_item.get('id') or raw_item.get('item_id'),
        source_type=raw_item.get('item_type') or raw_item.get('source_type') or 'manual',
        title=title,
        status=raw_item.get('status') or 'pending',
        block_id=raw_item.get('block_id'),
        due_date=raw_item.get('due_date'),
        estimated_minutes=raw_item.get('estimated_minutes'),
        worked_minutes=raw_item.get('worked_minutes'),
    )


def _build_work_journey_board_envelope(service_payload: dict[str, Any], query: WorkJourneyBoardQuery) -> dict[str, Any]:
    payload = WorkJourneyBoardPayload(
        company_id=query.company_id,
        employee_id=query.employee_id,
        anchor_date=query.anchor_date,
        scope=query.scope,
        items=[_normalize_board_item(item) for item in service_payload.get('period_items', [])],
        summary=dict(service_payload.get('summary') or {}),
    )
    return _success_envelope(operation='board.read', data=payload.model_dump(mode='json'))


def register_work_journey_tools(mcp) -> None:
    @mcp.tool()
    def get_work_journey_board_tool(company_id: int, employee_id: int, anchor_date: str, scope: str = 'day') -> dict:
        """Retorna o quadro operacional da jornada por blocos de um colaborador."""
        anchor = date.fromisoformat(anchor_date)
        query = WorkJourneyBoardQuery(company_id=company_id, employee_id=employee_id, anchor_date=anchor, scope=scope)
        payload = _run(get_work_journey_board, company_id, employee_id, anchor, scope)
        return _build_work_journey_board_envelope(payload or {}, query)

    @mcp.tool()
    def list_work_journey_blocks_tool(company_id: int, employee_id: int) -> dict:
        """Lista os blocos de jornada de um colaborador."""
        return {'blocks': _run(list_employee_blocks, company_id, employee_id)}

    @mcp.tool()
    def save_work_journey_block_tool(company_id: int, payload: dict, block_id: Optional[int] = None) -> dict:
        """Cria ou atualiza um bloco da jornada operacional."""
        schema = WorkJourneyUpdateSchema if block_id else WorkJourneyCreateSchema
        data = schema.model_validate(payload).model_dump()
        return {'block': _run(save_block, company_id, data, block_id)}

    @mcp.tool()
    def delete_work_journey_block_tool(company_id: int, block_id: int) -> dict:
        """Exclui um bloco da jornada operacional."""
        _run(delete_block, company_id, block_id)
        return {'success': True}

    @mcp.tool()
    def list_work_journey_rules_tool(company_id: int, employee_id: int) -> dict:
        """Lista as obrigações recorrentes configuradas para a jornada do colaborador."""
        return {'rules': _run(list_employee_rules, company_id, employee_id)}

    @mcp.tool()
    def save_work_journey_rule_tool(company_id: int, payload: dict, rule_id: Optional[int] = None) -> dict:
        """Cria ou atualiza uma obrigação recorrente da jornada operacional."""
        schema = WorkJourneyRuleUpdateSchema if rule_id else WorkJourneyRuleCreateSchema
        data = schema.model_validate(payload).model_dump(exclude_unset=True)
        return {'rule': _run(save_rule, company_id, data, rule_id)}

    @mcp.tool()
    def delete_work_journey_rule_tool(company_id: int, rule_id: int) -> dict:
        """Exclui uma obrigação recorrente da jornada operacional."""
        _run(delete_rule, company_id, rule_id)
        return {'success': True}

    @mcp.tool()
    def update_work_journey_item_tool(company_id: int, item_id: int, payload: dict) -> dict:
        """Atualiza status, bloco ou esforço real de uma tarefa da jornada."""
        data = WorkJourneyItemUpdateSchema.model_validate(payload).model_dump(exclude_unset=True)
        return {'item': _run(update_work_item, company_id, item_id, data)}

    @mcp.tool()
    def list_work_journey_manual_tasks_tool(company_id: int, employee_id: int) -> dict:
        """Lista todas as tarefas avulsas cadastradas para um colaborador na jornada operacional."""
        return {'data': _run(list_manual_tasks, company_id, employee_id)}

    @mcp.tool()
    def create_work_journey_manual_task_tool(company_id: int, payload: dict) -> dict:
        """Cria uma tarefa avulsa diretamente na agenda do colaborador.

        Observação: `occurrence_date` é campo somente-leitura, calculado pelo servidor.
        Para criação, informe `due_date`.
        """
        data = WorkJourneyManualTaskCreateSchema.model_validate(payload).model_dump()
        return {'item': _run(create_manual_task, company_id, data)}

    @mcp.tool()
    def delete_work_journey_manual_task_tool(company_id: int, item_id: int) -> dict:
        """Exclui uma tarefa avulsa criada diretamente na jornada."""
        _run(delete_work_item, company_id, item_id)
        return {'success': True}

    @mcp.tool()
    def create_work_journey_transfer_request_tool(company_id: int, item_id: int, to_employee_id: int, reason: Optional[str] = None, user_id: Optional[int] = None) -> dict:
        """Solicita transferência de uma tarefa da jornada para outro colaborador."""
        data = WorkJourneyTransferRequestCreateSchema.model_validate({
            'to_employee_id': to_employee_id,
            'reason': reason,
        }).model_dump(exclude_unset=True)
        return {'transfer_request': _run(create_transfer_request, company_id, item_id, data['to_employee_id'], data.get('reason'), user_id)}

    @mcp.tool()
    def approve_work_journey_transfer_request_tool(company_id: int, request_id: int, approver_user_id: Optional[int] = None, resolution_notes: Optional[str] = None) -> dict:
        """Aprova uma solicitação de transferência da jornada."""
        data = WorkJourneyTransferApprovalSchema.model_validate({'resolution_notes': resolution_notes}).model_dump(exclude_unset=True)
        return {'transfer_request': _run(approve_transfer_request, company_id, request_id, approver_user_id, data.get('resolution_notes'))}

    @mcp.tool()
    def list_work_journey_transfers_tool(company_id: int, employee_id: Optional[int] = None) -> dict:
        """Lista solicitações de transferência da jornada operacional."""
        return {'transfers': _run(list_transfer_requests, company_id, employee_id)}

    @mcp.tool()
    def create_work_journey_absence_request_tool(company_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Solicita férias, ausência ou licença para um colaborador."""
        data = WorkJourneyAbsenceRequestCreateSchema.model_validate(payload).model_dump()
        return {'absence_request': _run(create_absence_request, company_id, data, user_id)}

    @mcp.tool()
    def approve_work_journey_absence_request_tool(company_id: int, request_id: int, approver_user_id: Optional[int] = None, cleanup_notes: Optional[str] = None) -> dict:
        """Aprova uma ausência após limpeza operacional do período."""
        data = WorkJourneyAbsenceApprovalSchema.model_validate({'cleanup_notes': cleanup_notes}).model_dump(exclude_unset=True)
        return {'absence_request': _run(approve_absence_request, company_id, request_id, approver_user_id, data.get('cleanup_notes'))}

    @mcp.tool()
    def list_work_journey_absences_tool(company_id: int, employee_id: Optional[int] = None) -> dict:
        """Lista solicitações de ausência da jornada operacional."""
        return {'absences': _run(list_absence_requests, company_id, employee_id)}

    @mcp.tool()
    def get_work_journey_agenda_tool(company_id: int, employee_id: int, anchor_date: str, scope: str = 'week', force_regenerate: bool = False) -> dict:
        """Retorna a agenda materializada diária ou semanal da jornada do colaborador."""
        anchor = date.fromisoformat(anchor_date)
        return {'data': _run(get_work_journey_agenda, company_id, employee_id, anchor, scope, force_regenerate)}

    @mcp.tool()
    def generate_work_journey_agenda_tool(company_id: int, payload: dict) -> dict:
        """Gera ou regenera a agenda materializada da jornada do colaborador."""
        data = WorkJourneyAgendaGenerateSchema.model_validate(payload).model_dump()
        return {'data': _run(get_work_journey_agenda, company_id, data['employee_id'], data['anchor_date'], data['scope'], True)}

    @mcp.tool()
    def lock_work_journey_agenda_tool(company_id: int, employee_id: int, anchor_date: str, scope: str = 'week', user_id: Optional[int] = None) -> dict:
        """Trava a agenda da jornada para impedir novas alterações manuais."""
        anchor = date.fromisoformat(anchor_date)
        return {'data': _run(lock_work_journey_agenda, company_id, employee_id, anchor, scope, user_id)}

    @mcp.tool()
    def unlock_work_journey_agenda_tool(company_id: int, employee_id: int, anchor_date: str, scope: str = 'week') -> dict:
        """Cancela o travamento da agenda da jornada."""
        anchor = date.fromisoformat(anchor_date)
        return {'data': _run(unlock_work_journey_agenda, company_id, employee_id, anchor, scope)}

    @mcp.tool()
    def move_work_journey_agenda_item_tool(company_id: int, employee_id: int, anchor_date: str, scope: str, agenda_item_id: int, payload: dict) -> dict:
        """Move uma tarefa entre blocos ou dias da agenda materializada."""
        data = WorkJourneyAgendaMoveSchema.model_validate(payload).model_dump(exclude_unset=True)
        data['target_date'] = data.get('target_date') or date.fromisoformat(anchor_date)
        anchor = date.fromisoformat(anchor_date)
        return {'data': _run(move_work_journey_agenda_item, company_id, employee_id, anchor, scope, agenda_item_id, data)}

    @mcp.tool()
    def list_routine_journey_bindings_tool(company_id: int, routine_id: int) -> dict:
        """Lista, por executor, os blocos elegíveis e o vínculo atual entre uma rotina e a jornada operacional."""
        return {'data': _run(list_routine_bindings_context, company_id, routine_id)}

    @mcp.tool()
    def save_routine_journey_binding_tool(company_id: int, routine_id: int, payload: dict) -> dict:
        """Cria, atualiza ou remove o vínculo entre rotina operacional, colaborador executor e bloco de jornada."""
        data = RoutineJourneyBindingUpsertSchema.model_validate(payload).model_dump(exclude_unset=True)
        return {'binding': _run(save_routine_binding, company_id, routine_id, data['employee_id'], data.get('block_id'), data.get('notes'))}

    @mcp.tool()
    def list_employee_process_routines_for_journey_tool(company_id: int, employee_id: int) -> dict:
        """Lista as rotinas operacionais de processo que um colaborador precisa encaixar na jornada."""
        return {'data': _run(list_employee_process_routines, company_id, employee_id)}


WorkJourneyCreateSchema = WorkJourneyBlockCreateSchema
WorkJourneyUpdateSchema = WorkJourneyBlockUpdateSchema

