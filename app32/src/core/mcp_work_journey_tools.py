from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app import create_app
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
    delete_block,
    delete_rule,
    get_work_journey_board,
    list_employee_blocks,
    list_employee_rules,
    save_block,
    save_rule,
    update_work_item,
)


def _run(callback, *args, **kwargs) -> Any:
    app = create_app()
    with app.app_context():
        return callback(*args, **kwargs)


def register_work_journey_tools(mcp) -> None:
    @mcp.tool()
    def get_work_journey_board_tool(company_id: int, employee_id: int, anchor_date: str, scope: str = 'day') -> dict:
        """Retorna o quadro operacional da jornada por blocos de um colaborador."""
        anchor = date.fromisoformat(anchor_date)
        return _run(get_work_journey_board, company_id, employee_id, anchor, scope)

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
        """Atualiza status, bloco ou esforço real de uma atividade da jornada."""
        data = WorkJourneyItemUpdateSchema.model_validate(payload).model_dump(exclude_unset=True)
        return {'item': _run(update_work_item, company_id, item_id, data)}

    @mcp.tool()
    def create_work_journey_transfer_request_tool(company_id: int, item_id: int, to_employee_id: int, reason: Optional[str] = None, user_id: Optional[int] = None) -> dict:
        """Solicita transferência de uma atividade da jornada para outro colaborador."""
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
