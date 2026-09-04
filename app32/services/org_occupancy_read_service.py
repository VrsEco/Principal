"""Leitura temporal sem dados de login, permissões ou custos."""
from datetime import date
from models import Company, Employee, Role, EmployeeRoleOccupancy
from services.employee_role_occupancy_service import _date


def build_occupancy_snapshot(company_id, as_of):
    reference = _date(as_of, required=True)
    Company.query.filter_by(id=company_id).first_or_404()
    roles = Role.query.filter_by(company_id=company_id).all()
    employees = Employee.query.filter_by(company_id=company_id).all()
    history = EmployeeRoleOccupancy.query.filter_by(company_id=company_id).all()
    return resolve_snapshot(company_id, reference, roles, employees, history, current_date=date.today())


def resolve_snapshot(company_id, reference, roles, employees, history, *, current_date):
    roles, employees, history = list(roles), list(employees), list(history)
    if type(company_id) is not int or company_id <= 0:
        raise ValueError("Empresa obrigatória.")
    if any(item.company_id != company_id for item in roles + employees + history):
        raise ValueError("Dados fora da empresa solicitada.")
    role_map = {item.id: item for item in roles}
    employee_map = {item.id: item for item in employees}
    if len(role_map) != len(roles) or len(employee_map) != len(employees):
        raise ValueError("Cadastro duplicado no snapshot.")
    temporal_employees, pairs, assignments = set(), set(), []
    for item in history:
        if item.employee_id not in employee_map or item.role_id not in role_map:
            raise ValueError("Ocupação com referência inválida.")
        temporal_employees.add(item.employee_id)
        if not (item.starts_on <= reference and (item.ends_on is None or reference < item.ends_on)):
            continue
        pair = (item.employee_id, item.role_id)
        if pair in pairs:
            raise ValueError("Ocupações sobrepostas do mesmo cargo.")
        pairs.add(pair)
        assignments.append({
            "employee_id": item.employee_id, "role_id": item.role_id,
            "employee_name": employee_map[item.employee_id].name,
            "role_title": role_map[item.role_id].title,
            "weekly_hours": str(item.weekly_hours) if item.weekly_hours is not None else None,
            "source": "temporal", "capacity_pending": item.weekly_hours is None,
        })
    pending = []
    for employee in employees:
        if employee.id in temporal_employees or employee.role_id is None:
            continue  # Não ressuscitar ocupação encerrada usando o campo legado.
        pending.append(employee.id)
        if employee.role_id not in role_map:
            continue
        if reference != current_date:
            continue  # O legado não comprova estrutura histórica ou futura.
        if (employee.status or "").strip().lower() not in {"", "active", "ativo", "vacation", "ferias", "férias"}:
            continue
        assignments.append({
            "employee_id": employee.id, "role_id": employee.role_id,
            "employee_name": employee.name, "role_title": role_map[employee.role_id].title,
            "weekly_hours": None, "source": "legacy_unverified", "capacity_pending": True,
        })
    assignments.sort(key=lambda item: (item["role_id"], item["employee_id"]))
    return {"company_id": company_id, "as_of": reference.isoformat(), "assignments": assignments,
            "distinct_people_count": len({item["employee_id"] for item in assignments}),
            "legacy_pending_employee_ids": sorted(pending),
            "legacy_reconciliation_complete": not pending,
            "status_note": "Vigências registradas; status atual do colaborador não comprova disponibilidade histórica."}
