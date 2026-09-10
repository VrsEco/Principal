"""Service interna; adaptador deve autorizar custos e controlar a transação."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from models import db, Role, RoleCostProfile
from models.role_cost_profile import COST_COMPONENTS
from services.employee_role_occupancy_service import _date, _actor


def normalize_cost_profile(payload):
    if not isinstance(payload, dict) or set(payload) - {*COST_COMPONENTS, "starts_on", "ends_on", "currency"}:
        raise ValueError("Perfil de custo inválido.")
    start = _date(payload.get("starts_on"), required=True)
    end = _date(payload.get("ends_on"))
    if end is not None and end <= start:
        raise ValueError("Fim deve ser posterior ao início.")
    currency = payload.get("currency")
    if not isinstance(currency, str) or re.fullmatch(r"[A-Z]{3}", currency) is None:
        raise ValueError("Informe a moeda com três letras maiúsculas.")
    values = {"starts_on": start, "ends_on": end, "currency": currency}
    for field in COST_COMPONENTS:
        raw = payload.get(field)
        if raw is None:
            values[field] = None
            continue
        try:
            amount = Decimal(str(raw))
            if not amount.is_finite() or not 0 <= amount <= Decimal("999999999999.99") or amount != amount.quantize(Decimal("0.01")):
                raise ValueError()
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(f"Valor inválido em {field}: use valor não negativo com até duas casas decimais.") from exc
        values[field] = amount
    return values


def create_cost_profile(company_id, role_id, payload, *, actor_user_id):
    actor = _actor(actor_user_id)
    values = normalize_cost_profile(payload)
    Role.query.filter_by(id=role_id, company_id=company_id).with_for_update().first_or_404()
    existing = RoleCostProfile.query.filter_by(company_id=company_id, role_id=role_id).all()
    for item in existing:
        if (values["ends_on"] is None or item.starts_on < values["ends_on"]) and (item.ends_on is None or values["starts_on"] < item.ends_on):
            raise ValueError("Já existe perfil de custo vigente neste período.")
    profile = RoleCostProfile(company_id=company_id, role_id=role_id, created_by_user_id=actor, **values)
    db.session.add(profile)
    db.session.flush()
    return profile


def build_planned_cost_snapshot(company_id, as_of):
    reference = _date(as_of, required=True)
    roles = Role.query.filter_by(company_id=company_id).all()
    profiles = RoleCostProfile.query.filter(
        RoleCostProfile.company_id == company_id,
        RoleCostProfile.starts_on <= reference,
        (RoleCostProfile.ends_on.is_(None) | (RoleCostProfile.ends_on > reference)),
    ).all()
    return planned_cost_snapshot(company_id, reference, roles, profiles)


def planned_cost_snapshot(company_id, reference, roles, profiles):
    roles, profiles = list(roles), list(profiles)
    if any(item.company_id != company_id for item in roles + profiles):
        raise ValueError("Dados fora da empresa solicitada.")
    role_ids = {role.id for role in roles}
    selected = {}
    for profile in profiles:
        if profile.role_id not in role_ids:
            raise ValueError("Perfil sem cargo válido na empresa.")
        if not (profile.starts_on <= reference and (profile.ends_on is None or reference < profile.ends_on)):
            continue
        if profile.role_id in selected:
            raise ValueError("Perfis de custo sobrepostos; corrija antes de consolidar.")
        selected[profile.role_id] = profile
    output = []
    currencies = set()
    known_costs = []
    for role in roles:
        profile = selected.get(role.id)
        try:
            planned = Decimal(str(role.headcount_planned if role.headcount_planned is not None else 0))
            if not planned.is_finite() or planned < 0 or planned != planned.to_integral_value():
                raise ValueError
        except (ValueError, InvalidOperation, TypeError) as exc:
            raise ValueError(f"Quantidade planejada inválida no cargo {role.title}.") from exc
        monthly_cost_per_fte = profile.amounts()["monthly_cost_per_fte"] if profile else None
        if monthly_cost_per_fte is not None:
            currencies.add(profile.currency)
            planned_cost = (planned * monthly_cost_per_fte).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            known_costs.append(planned_cost)
        else:
            planned_cost = None
        output.append({
            "role_id": role.id,
            "role_title": role.title,
            "planned_monthly_cost": str(planned_cost) if planned_cost is not None else None,
        })
    if len(currencies) > 1:
        raise ValueError("Não é permitido consolidar moedas diferentes.")
    subtotal = sum(known_costs, Decimal("0.00"))
    return {
        "company_id": company_id, "as_of": reference.isoformat(),
        "basis": "Quantidade planejada atual dos cargos × custo por FTE vigente na data. Não é folha realizada nem reconstrução histórica do quadro.",
        "currency": next(iter(currencies), None),
        "costed_roles_count": len(known_costs),
        "total_roles_count": len(output),
        "known_planned_monthly_subtotal": str(subtotal),
        "planned_monthly_total": str(subtotal) if len(known_costs) == len(output) else None,
        "roles": output,
    }
