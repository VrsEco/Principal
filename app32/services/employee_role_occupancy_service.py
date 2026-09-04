"""Escrita de ocupações: vigência [início, fim), sem alteração de cargo RBAC."""
from datetime import date, datetime
from decimal import Decimal

from models import db, Employee, Role, EmployeeRoleOccupancy
from services.company_role_hierarchy_service import CompanyRoleHierarchyService


def validate_schedule(candidate, existing, available_hours):
    start, end = candidate.starts_on, candidate.ends_on
    if end is not None and end <= start:
        raise ValueError("Fim deve ser posterior ao início.")
    overlaps = []
    for row in existing:
        if (end is None or row.starts_on < end) and (row.ends_on is None or start < row.ends_on):
            if row.role_id == candidate.role_id:
                raise ValueError("Já existe ocupação deste cargo no período informado.")
            overlaps.append(row)
    # Verifica cada mudança de intervalo, não a soma de períodos disjuntos.
    points = {start} | {max(start, row.starts_on) for row in overlaps}
    if available_hours is not None:
        for point in points:
            total = candidate.weekly_hours or Decimal(0)
            total += sum((row.weekly_hours or Decimal(0)) for row in overlaps
                         if row.starts_on <= point and (row.ends_on is None or point < row.ends_on))
            if total > available_hours:
                raise ValueError("Dedicação simultânea excede a jornada do colaborador.")


def _actor(actor_user_id):
    # Identidade autenticada deve vir do adaptador, nunca do JSON do usuário.
    if type(actor_user_id) is not int or actor_user_id <= 0:
        raise ValueError("Ator autenticado obrigatório.")
    return actor_user_id


def _date(value, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ValueError("Data obrigatória no formato AAAA-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Data inválida.") from exc
    if parsed.isoformat() != value:
        raise ValueError("Use AAAA-MM-DD.")
    return parsed


def validate_legacy_transition(employee, candidate, existing):
    if employee.role_id is None or employee.role_id == candidate.role_id:
        return
    # Nenhuma segunda ocupação antes de explicitar a dedicação do cargo legado.
    covered = any(row.role_id == employee.role_id and row.weekly_hours is not None
                  and row.starts_on <= candidate.starts_on
                  and (row.ends_on is None or (candidate.ends_on is not None and row.ends_on >= candidate.ends_on))
                  for row in existing)
    if not covered:
        raise ValueError("Reconcilie primeiro a vigência e dedicação do cargo principal legado.")


def create_occupancy(company_id, employee_id, role_id, payload, *, actor_user_id):
    actor = _actor(actor_user_id)
    if not isinstance(payload, dict) or set(payload) - {"starts_on", "ends_on", "weekly_hours"}:
        raise ValueError("Payload de ocupação inválido.")
    start = _date(payload.get("starts_on"), required=True)
    end = _date(payload.get("ends_on"))
    hours = CompanyRoleHierarchyService._normalize_payload(
        company_id, {"weekly_hours": payload.get("weekly_hours")}, role_id=role_id,
    )["weekly_hours"]
    # Todos os escritores de ocupações devem tomar este lock antes de validar.
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).with_for_update().first_or_404()
    Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    if (employee.status or "").strip().lower() not in {"", "active", "ativo"}:
        raise ValueError("Colaborador deve estar ativo.")
    existing = EmployeeRoleOccupancy.query.filter_by(company_id=company_id, employee_id=employee_id).all()
    candidate = EmployeeRoleOccupancy(company_id=company_id, employee_id=employee_id, role_id=role_id,
                                      starts_on=start, ends_on=end, weekly_hours=hours, created_by_user_id=actor)
    validate_legacy_transition(employee, candidate, existing)
    validate_schedule(candidate, existing, employee.weekly_hours)
    db.session.add(candidate)
    db.session.flush()
    # Commit/rollback pertence à unidade de trabalho do futuro adaptador.
    return candidate


def end_occupancy(company_id, employee_id, occupancy_id, payload, *, actor_user_id):
    actor = _actor(actor_user_id)
    if not isinstance(payload, dict) or set(payload) != {"ends_on"}:
        raise ValueError("Informe apenas ends_on.")
    end = _date(payload["ends_on"], required=True)
    Employee.query.filter_by(id=employee_id, company_id=company_id).with_for_update().first_or_404()
    occupancy = EmployeeRoleOccupancy.query.filter_by(
        id=occupancy_id, employee_id=employee_id, company_id=company_id,
    ).with_for_update().first_or_404()
    apply_end(occupancy, end, actor)
    db.session.flush()
    return occupancy


def apply_end(occupancy, end, actor):
    if end <= occupancy.starts_on:
        raise ValueError("Fim deve ser posterior ao início.")
    if occupancy.ended_at is not None:
        if occupancy.ends_on == end:
            return  # Retentativa não altera a autoria original.
        raise ValueError("Ocupação já encerrada; correção exige fluxo de auditoria.")
    if occupancy.ends_on is not None and end > occupancy.ends_on:
        raise ValueError("Encerramento não pode estender a vigência.")
    occupancy.ends_on = end
    occupancy.ended_by_user_id = actor
    occupancy.ended_at = datetime.utcnow()
