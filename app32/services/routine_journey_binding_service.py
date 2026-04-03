from __future__ import annotations

from typing import Any

from models import Employee, Process, Routine, RoutineCollaborator, RoutineJourneyBinding, WorkJourneyBlock, db


def list_routine_bindings_context(company_id: int, routine_id: int) -> dict[str, Any]:
    routine = Routine.query.filter_by(company_id=company_id, id=routine_id).first()
    if not routine:
        raise ValueError('Rotina não encontrada.')

    process = Process.query.filter_by(company_id=company_id, id=routine.process_id).first() if routine.process_id else None
    relations = (
        RoutineCollaborator.query.filter_by(routine_id=routine_id)
        .order_by(RoutineCollaborator.employee_id.asc(), RoutineCollaborator.id.asc())
        .all()
    )

    collaborator_rows = []
    for relation in relations:
        employee = Employee.query.filter_by(company_id=company_id, id=relation.employee_id, status='active').first()
        if not employee:
            continue
        binding = RoutineJourneyBinding.query.filter_by(company_id=company_id, routine_id=routine_id, employee_id=employee.id).first()
        blocks = (
            WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee.id, is_active=True)
            .all()
        )
        eligible_blocks = [
            {
                'id': block.id,
                'name': block.name,
                'start_time': block.start_time.strftime('%H:%M') if block.start_time else None,
                'end_time': block.end_time.strftime('%H:%M') if block.end_time else None,
                'weekdays': list(block.weekdays_json or []),
            }
            for block in sorted(blocks, key=lambda item: _block_sort_key(item))
            if 'process_instance' in (block.accepted_item_types or [])
        ]
        collaborator_rows.append(
            {
                'employee_id': employee.id,
                'employee_name': employee.name,
                'employee_email': employee.email,
                'hours_used': float(relation.hours_used or 0),
                'routine_collaborator_id': relation.id,
                'binding': {
                    'id': binding.id,
                    'block_id': binding.block_id,
                    'block_name': binding.block.name if binding and binding.block else None,
                    'notes': binding.notes if binding else None,
                } if binding else None,
                'available_blocks': eligible_blocks,
            }
        )

    return {
        'routine': {
            'id': routine.id,
            'name': routine.name,
            'process_id': routine.process_id,
            'process_name': process.name if process else None,
            'process_code': process.code if process else None,
        },
        'collaborators': collaborator_rows,
    }


def save_routine_binding(company_id: int, routine_id: int, employee_id: int, block_id: int | None, notes: str | None = None) -> dict[str, Any]:
    routine = Routine.query.filter_by(company_id=company_id, id=routine_id).first()
    if not routine:
        raise ValueError('Rotina não encontrada.')

    relation = RoutineCollaborator.query.filter_by(routine_id=routine_id, employee_id=employee_id).first()
    if not relation:
        raise ValueError('O colaborador informado não está vinculado à rotina.')

    employee = Employee.query.filter_by(company_id=company_id, id=employee_id, status='active').first()
    if not employee:
        raise ValueError('Colaborador inválido para esta empresa.')

    binding = RoutineJourneyBinding.query.filter_by(company_id=company_id, routine_id=routine_id, employee_id=employee_id).first()

    if not block_id:
        if binding:
            db.session.delete(binding)
            db.session.commit()
        return {
            'employee_id': employee_id,
            'block_id': None,
            'block_name': None,
            'notes': None,
        }

    block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id, employee_id=employee_id, is_active=True).first()
    if not block:
        raise ValueError('Bloco inválido para o colaborador informado.')
    if 'process_instance' not in (block.accepted_item_types or []):
        raise ValueError('O bloco selecionado não aceita instâncias de processo.')

    if not binding:
        binding = RoutineJourneyBinding(company_id=company_id, routine_id=routine_id, employee_id=employee_id)

    binding.block_id = block.id
    binding.notes = (notes or '').strip() or None
    db.session.add(binding)
    db.session.commit()

    return {
        'id': binding.id,
        'employee_id': employee_id,
        'block_id': block.id,
        'block_name': block.name,
        'notes': binding.notes,
    }


def list_employee_process_routines(company_id: int, employee_id: int) -> dict[str, Any]:
    employee = Employee.query.filter_by(company_id=company_id, id=employee_id, status='active').first()
    if not employee:
        raise ValueError('Colaborador não encontrado para a empresa informada.')

    blocks = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True)
        .all()
    )
    eligible_blocks = [
        {
            'id': block.id,
            'name': block.name,
            'start_time': block.start_time.strftime('%H:%M') if block.start_time else None,
            'end_time': block.end_time.strftime('%H:%M') if block.end_time else None,
            'weekdays': list(block.weekdays_json or []),
        }
        for block in sorted(blocks, key=lambda item: _block_sort_key(item))
        if 'process_instance' in (block.accepted_item_types or [])
    ]

    relations = (
        RoutineCollaborator.query.join(Routine, Routine.id == RoutineCollaborator.routine_id)
        .filter(Routine.company_id == company_id, RoutineCollaborator.employee_id == employee_id)
        .all()
    )

    routines_payload = []
    for relation in relations:
        routine = Routine.query.filter_by(company_id=company_id, id=relation.routine_id).first()
        if not routine or routine.is_active is False:
            continue
        process = Process.query.filter_by(company_id=company_id, id=routine.process_id).first() if routine.process_id else None
        binding = RoutineJourneyBinding.query.filter_by(company_id=company_id, routine_id=routine.id, employee_id=employee_id).first()
        routines_payload.append(
            {
                'routine_id': routine.id,
                'routine_name': routine.name,
                'process_id': routine.process_id,
                'process_name': process.name if process else None,
                'process_code': process.code if process else None,
                'schedule_type': routine.schedule_type,
                'schedule_value': routine.schedule_value,
                'hours_used': float(relation.hours_used or 0),
                'binding': {
                    'id': binding.id,
                    'block_id': binding.block_id,
                    'block_name': binding.block.name if binding and binding.block else None,
                    'notes': binding.notes if binding else None,
                } if binding else None,
            }
        )

    routines_payload.sort(key=lambda item: ((item.get('process_code') or ''), (item.get('routine_name') or '').lower(), item.get('routine_id') or 0))
    return {
        'employee': {'id': employee.id, 'name': employee.name},
        'available_blocks': eligible_blocks,
        'routines': routines_payload,
    }


def get_bound_block_id(company_id: int, routine_id: int | None, employee_id: int | None) -> int | None:
    if not routine_id or not employee_id:
        return None
    binding = RoutineJourneyBinding.query.filter_by(
        company_id=company_id,
        routine_id=routine_id,
        employee_id=employee_id,
    ).first()
    return binding.block_id if binding else None


def _block_sort_key(block) -> tuple[int, int, int, str, int]:
    weekdays = sorted(int(day) for day in (block.weekdays_json or []))
    first_weekday = weekdays[0] if weekdays else 7
    start_minutes = (block.start_time.hour * 60 + block.start_time.minute) if block.start_time else 0
    end_minutes = (block.end_time.hour * 60 + block.end_time.minute) if block.end_time else 0
    return (first_weekday, start_minutes, end_minutes, (block.name or '').lower(), block.id or 0)
