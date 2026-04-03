from __future__ import annotations

from models import Employee


ACTIVE_ITEM_STATUSES = {'pending', 'in_progress', 'postponed', 'suspended', 'overdue'}


class WorkJourneyError(ValueError):
    pass


def ensure_employee(company_id: int, employee_id: int) -> Employee:
    employee = Employee.query.filter_by(company_id=company_id, id=employee_id).first()
    if not employee:
        raise WorkJourneyError('Colaborador não encontrado para a empresa informada.')
    return employee
