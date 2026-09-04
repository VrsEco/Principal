"""Projeção pura de snapshot autorizado; não lê banco nem concede acesso a custos.

O chamador deve selecionar uma data de referência e apenas vigências aplicáveis.
Valores monetários permanecem Decimal até a serialização pelo adaptador autorizado.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _number(value, *, positive=False, integer=False):
    if value is None:
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or (positive and number == 0):
            raise ValueError()
        if integer and number != number.to_integral_value():
            raise ValueError()
        return number
    except (ValueError, InvalidOperation) as exc:
        raise ValueError("Valor quantitativo inválido.") from exc


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if value is not None else None


def project_organogram(company_id, roles, employees, occupancies):
    """Cada coleção é um snapshot de dicionários do mesmo tenant, sem duplicatas."""
    if type(company_id) is not int or company_id <= 0:
        raise ValueError("Empresa obrigatória.")
    roles, employees, occupancies = list(roles), list(employees), list(occupancies)
    for record in roles + employees + occupancies:
        if record.get("company_id") != company_id:
            raise ValueError("Snapshot contém dados de outra empresa.")
    def index(records):
        result = {}
        for row in records:
            key = row.get("id")
            if type(key) is not int or key <= 0 or key in result:
                raise ValueError("Identificador inválido ou duplicado.")
            result[key] = row
        return result
    role_map, employee_map = index(roles), index(employees)
    pairs, allocated, by_role = set(), {}, {key: [] for key in role_map}
    for item in occupancies:
        pair = (item.get("role_id"), item.get("employee_id"))
        if pair in pairs or pair[0] not in role_map or pair[1] not in employee_map:
            raise ValueError("Ocupação duplicada ou referência inválida.")
        pairs.add(pair)
        hours = _number(item.get("weekly_hours"), positive=True)
        allocated[pair[1]] = allocated.get(pair[1], Decimal(0)) + (hours or 0)
        by_role[pair[0]].append((pair[1], hours))
    unknown_employee_capacity = set()
    for employee_id, used in allocated.items():
        available = _number(employee_map[employee_id].get("weekly_hours"), positive=True)
        if available is None:
            unknown_employee_capacity.add(employee_id)
        elif used > available:
            raise ValueError("Dedicação total excede a jornada do colaborador.")
    currencies, output = set(), []
    for role_id, role in role_map.items():
        planned = _number(role.get("headcount_planned"), integer=True)
        standard = _number(role.get("weekly_hours"), positive=True)
        cost = _number(role.get("monthly_cost_per_fte"))
        currency = role.get("currency")
        if cost is not None:
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
                raise ValueError("Moeda obrigatória no formato de três letras maiúsculas.")
            currencies.add(currency)
        occupants = by_role[role_id]
        complete_hours = all(hours is not None for _, hours in occupants)
        hours = sum((value for _, value in occupants if value is not None), Decimal(0))
        fte = (hours / standard) if standard and complete_hours else (Decimal(0) if not occupants else None)
        planned_cost = planned * cost if planned is not None and cost is not None else None
        occupied_cost = fte * cost if fte is not None and cost is not None else None
        output.append({
            "role_id": role_id, "people_count": len(occupants), "occupied_fte": fte,
            "nominal_vacancies": max(int(planned) - len(occupants), 0) if planned is not None else None,
            "excess_people": max(len(occupants) - int(planned), 0) if planned is not None else None,
            "planned_monthly_cost": _money(planned_cost), "occupied_monthly_cost_estimate": _money(occupied_cost),
            "capacity_pending": not complete_hours or bool(occupants and standard is None) or any(emp in unknown_employee_capacity for emp, _ in occupants),
        })
    if len(currencies) > 1:
        raise ValueError("Não é permitido consolidar moedas diferentes.")
    known = [row["planned_monthly_cost"] for row in output if row["planned_monthly_cost"] is not None]
    subtotal = sum(known, Decimal("0.00"))
    return {
        "company_id": company_id, "currency": next(iter(currencies), None), "roles": output,
        "distinct_people_count": len(allocated), "costed_roles_count": len(known),
        "total_roles_count": len(output), "known_planned_monthly_subtotal": subtotal,
        "planned_monthly_total": subtotal if len(known) == len(output) else None,
    }
