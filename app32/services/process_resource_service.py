from decimal import Decimal, InvalidOperation

from models import db, Process, ProcessResourceLink, ProcessRoutine, ResourceCatalog
from models.process_resource import RESOURCE_CAPACITY_UNIT_VALUES, RESOURCE_TYPE_VALUES


class ProcessResourceValidationError(ValueError):
    """Erro de validação funcional da camada Estrutura/Recursos."""


def _clean_text(value, *, required: bool = False, field: str = "campo"):
    text = str(value or "").strip()
    if required and not text:
        raise ProcessResourceValidationError(f"{field} é obrigatório.")
    return text or None


def _decimal_or_none(value, *, field: str):
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ProcessResourceValidationError(f"{field} deve ser numérico.")
    if parsed < 0:
        raise ProcessResourceValidationError(f"{field} não pode ser negativo.")
    return parsed


def _percentage_or_none(value, *, field: str = "percentual de uso"):
    parsed = _decimal_or_none(value, field=field)
    if parsed is not None and parsed > 100:
        raise ProcessResourceValidationError(f"{field} não pode ser maior que 100.")
    return parsed


def _bool_or_default(value, default=True):
    if value is None:
        return default
    return bool(value)


def _get_process_for_company(company_id: int, process_id: int) -> Process:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process:
        raise ProcessResourceValidationError("Processo não encontrado para este tenant.")
    return process


def _get_resource_for_company(company_id: int, resource_id: int) -> ResourceCatalog:
    resource = ResourceCatalog.query.filter_by(id=resource_id, company_id=company_id).first()
    if not resource:
        raise ProcessResourceValidationError("Recurso não encontrado para este tenant.")
    return resource


def _get_link_for_company(company_id: int, process_id: int, link_id: int) -> ProcessResourceLink:
    link = ProcessResourceLink.query.filter_by(
        id=link_id,
        company_id=company_id,
        process_id=process_id,
    ).first()
    if not link:
        raise ProcessResourceValidationError("Vínculo de recurso não encontrado para este tenant/processo.")
    return link


def _validate_resource_type(resource_type: str) -> str:
    normalized = _clean_text(resource_type, required=True, field="tipo")
    if normalized not in RESOURCE_TYPE_VALUES:
        raise ProcessResourceValidationError("tipo de recurso inválido.")
    return normalized


def _validate_capacity_unit(unit: str | None) -> str | None:
    normalized = _clean_text(unit)
    if normalized and normalized not in RESOURCE_CAPACITY_UNIT_VALUES:
        raise ProcessResourceValidationError("unidade de capacidade operacional inválida.")
    return normalized


def _validate_other_subtype(resource_type: str, subtype: str | None, notes: str | None):
    if resource_type == "other" and (not subtype or not notes):
        raise ProcessResourceValidationError("Recursos do tipo Outros exigem subtipo e observações.")


def _validate_process_routine(company_id: int, process_id: int, process_routine_id: int | None):
    if not process_routine_id:
        return None
    routine = ProcessRoutine.query.filter_by(
        id=process_routine_id,
        company_id=company_id,
        process_id=process_id,
    ).first()
    if not routine:
        raise ProcessResourceValidationError("Atividade/POP não pertence ao processo informado.")
    return routine


def list_resources(company_id: int, *, resource_type: str | None = None, active_only: bool = False):
    query = ResourceCatalog.query.filter_by(company_id=company_id)
    if resource_type:
        query = query.filter(ResourceCatalog.type == _validate_resource_type(resource_type))
    if active_only:
        query = query.filter(ResourceCatalog.is_active.is_(True))
    return query.order_by(ResourceCatalog.type.asc(), ResourceCatalog.subtype.asc(), ResourceCatalog.item_name.asc()).all()


def _resource_capacity_total(resource: ResourceCatalog) -> float | None:
    """Capacidade operacional total para rateio/uso mensal.

    Preferimos operational_capacity_value (ex.: 220 horas/mês). Se não existir,
    usamos quantity como fallback para manter compatibilidade com cadastros simples.
    """
    if resource.operational_capacity_value is not None:
        return float(resource.operational_capacity_value)
    if resource.quantity is not None:
        return float(resource.quantity)
    return None


def _link_monthly_used_quantity(link: ProcessResourceLink) -> float:
    if link.monthly_used_quantity is not None:
        return float(link.monthly_used_quantity)
    if link.used_quantity_per_execution is not None and link.estimated_monthly_instances is not None:
        return float(link.used_quantity_per_execution or 0) * float(link.estimated_monthly_instances or 0)
    return float(link.used_quantity or 0)


def _calculate_link_usage_metrics(resource: ResourceCatalog, payload: dict, link: ProcessResourceLink | None = None) -> dict:
    used_per_execution = _decimal_or_none(
        payload.get("used_quantity_per_execution", payload.get("used_quantity")),
        field="quantidade usada por instância",
    ) if ("used_quantity_per_execution" in payload or "used_quantity" in payload or link is None) else link.used_quantity_per_execution
    estimated_instances = _decimal_or_none(
        payload.get("estimated_monthly_instances"),
        field="instâncias estimadas por mês",
    ) if ("estimated_monthly_instances" in payload or link is None) else link.estimated_monthly_instances

    explicit_monthly = _decimal_or_none(payload.get("monthly_used_quantity"), field="consumo mensal estimado") if "monthly_used_quantity" in payload else None
    if explicit_monthly is not None:
        monthly_used = explicit_monthly
    elif used_per_execution is not None and estimated_instances is not None:
        monthly_used = used_per_execution * estimated_instances
    elif link is not None and link.monthly_used_quantity is not None and "used_quantity_per_execution" not in payload and "estimated_monthly_instances" not in payload:
        monthly_used = link.monthly_used_quantity
    else:
        monthly_used = used_per_execution

    capacity_total = _resource_capacity_total(resource)
    usage_percentage = None
    if monthly_used is not None and capacity_total and capacity_total > 0:
        usage_percentage = min((monthly_used / Decimal(str(capacity_total))) * Decimal("100"), Decimal("100"))
    elif "usage_percentage" in payload:
        usage_percentage = _percentage_or_none(payload.get("usage_percentage"))

    cost_per_execution = _decimal_or_none(
        payload.get("estimated_cost_per_execution"),
        field="custo estimado por execução",
    ) if ("estimated_cost_per_execution" in payload or link is None) else link.estimated_cost_per_execution
    monthly_cost = _decimal_or_none(payload.get("allocated_monthly_cost"), field="custo mensal alocado") if "allocated_monthly_cost" in payload else None
    if monthly_cost is None and cost_per_execution is not None and estimated_instances is not None:
        monthly_cost = cost_per_execution * estimated_instances
    elif monthly_cost is None and link is not None and "estimated_cost_per_execution" not in payload and "estimated_monthly_instances" not in payload:
        monthly_cost = link.allocated_monthly_cost

    return {
        "used_quantity_per_execution": used_per_execution,
        "estimated_monthly_instances": estimated_instances,
        "monthly_used_quantity": monthly_used,
        "used_quantity": monthly_used,
        "usage_percentage": usage_percentage,
        "estimated_cost_per_execution": cost_per_execution,
        "allocated_monthly_cost": monthly_cost,
    }


def get_resource_usage_summary(company_id: int, resource_id: int) -> dict:
    resource = _get_resource_for_company(company_id, resource_id)
    links = ProcessResourceLink.query.filter_by(
        company_id=company_id,
        resource_id=resource.id,
        is_active=True,
    ).all()
    used_quantity = sum(_link_monthly_used_quantity(link) for link in links)
    capacity_total = _resource_capacity_total(resource)
    available_quantity = max(capacity_total - used_quantity, 0) if capacity_total is not None else None
    used_percentage_total = (
        min((used_quantity / capacity_total) * 100, 100)
        if capacity_total and capacity_total > 0
        else sum(float(link.usage_percentage or 0) for link in links)
    )
    return {
        "capacity_total": capacity_total,
        "used_quantity_total": used_quantity,
        "available_quantity": available_quantity,
        "usage_percentage_total": used_percentage_total,
        "active_allocations_count": len(links),
    }


def serialize_resource_with_usage(resource: ResourceCatalog) -> dict:
    payload = resource.to_dict()
    payload["usage"] = get_resource_usage_summary(resource.company_id, resource.id)
    return payload


def create_resource(company_id: int, payload: dict) -> ResourceCatalog:
    resource_type = _validate_resource_type(payload.get("type"))
    subtype = _clean_text(payload.get("subtype"), required=True, field="subtipo")
    notes = _clean_text(payload.get("notes"))
    _validate_other_subtype(resource_type, subtype, notes)

    resource = ResourceCatalog(
        company_id=company_id,
        type=resource_type,
        subtype=subtype,
        item_name=_clean_text(payload.get("item_name"), required=True, field="nome do item"),
        unit_value=_decimal_or_none(payload.get("unit_value"), field="valor unitário"),
        quantity=_decimal_or_none(payload.get("quantity"), field="quantidade"),
        acquisition_total_amount=_decimal_or_none(payload.get("acquisition_total_amount"), field="gasto total de aquisição"),
        installation_total_amount=_decimal_or_none(payload.get("installation_total_amount"), field="gasto total de instalação"),
        monthly_recurring_amount=_decimal_or_none(payload.get("monthly_recurring_amount"), field="gasto mensal recorrente"),
        operational_capacity_value=_decimal_or_none(payload.get("operational_capacity_value"), field="capacidade operacional"),
        operational_capacity_unit=_validate_capacity_unit(payload.get("operational_capacity_unit")),
        estimated_useful_life=_clean_text(payload.get("estimated_useful_life")),
        notes=notes,
        is_active=_bool_or_default(payload.get("is_active"), True),
    )
    db.session.add(resource)
    db.session.commit()
    return resource


def update_resource(company_id: int, resource_id: int, payload: dict) -> ResourceCatalog:
    resource = _get_resource_for_company(company_id, resource_id)
    if "type" in payload:
        resource.type = _validate_resource_type(payload.get("type"))
    if "subtype" in payload:
        resource.subtype = _clean_text(payload.get("subtype"), required=True, field="subtipo")
    if "item_name" in payload:
        resource.item_name = _clean_text(payload.get("item_name"), required=True, field="nome do item")
    for attr, label in (
        ("unit_value", "valor unitário"),
        ("quantity", "quantidade"),
        ("acquisition_total_amount", "gasto total de aquisição"),
        ("installation_total_amount", "gasto total de instalação"),
        ("monthly_recurring_amount", "gasto mensal recorrente"),
        ("operational_capacity_value", "capacidade operacional"),
    ):
        if attr in payload:
            setattr(resource, attr, _decimal_or_none(payload.get(attr), field=label))
    if "operational_capacity_unit" in payload:
        resource.operational_capacity_unit = _validate_capacity_unit(payload.get("operational_capacity_unit"))
    if "estimated_useful_life" in payload:
        resource.estimated_useful_life = _clean_text(payload.get("estimated_useful_life"))
    if "notes" in payload:
        resource.notes = _clean_text(payload.get("notes"))
    if "is_active" in payload:
        resource.is_active = bool(payload.get("is_active"))

    _validate_other_subtype(resource.type, resource.subtype, resource.notes)
    db.session.commit()
    return resource


def deactivate_resource(company_id: int, resource_id: int) -> ResourceCatalog:
    resource = _get_resource_for_company(company_id, resource_id)
    resource.is_active = False
    db.session.commit()
    return resource


def list_process_resource_links(company_id: int, process_id: int):
    _get_process_for_company(company_id, process_id)
    return (
        ProcessResourceLink.query.filter_by(company_id=company_id, process_id=process_id)
        .join(ResourceCatalog, ResourceCatalog.id == ProcessResourceLink.resource_id)
        .order_by(ResourceCatalog.type.asc(), ResourceCatalog.subtype.asc(), ResourceCatalog.item_name.asc())
        .all()
    )


def create_process_resource_link(company_id: int, process_id: int, payload: dict) -> ProcessResourceLink:
    _get_process_for_company(company_id, process_id)
    resource = _get_resource_for_company(company_id, int(payload.get("resource_id") or 0))
    if not resource.is_active:
        raise ProcessResourceValidationError("Recurso inativo não pode ser vinculado a novo processo.")
    process_routine_id = payload.get("process_routine_id")
    process_routine_id = int(process_routine_id) if process_routine_id not in (None, "") else None
    _validate_process_routine(company_id, process_id, process_routine_id)

    link = ProcessResourceLink(
        company_id=company_id,
        process_id=process_id,
        process_routine_id=process_routine_id,
        bpmn_element_id=_clean_text(payload.get("bpmn_element_id")),
        resource_id=resource.id,
        **_calculate_link_usage_metrics(resource, payload),
        capacity_bottleneck_notes=_clean_text(payload.get("capacity_bottleneck_notes")),
        is_active=_bool_or_default(payload.get("is_active"), True),
    )
    db.session.add(link)
    db.session.commit()
    return link


def update_process_resource_link(company_id: int, process_id: int, link_id: int, payload: dict) -> ProcessResourceLink:
    _get_process_for_company(company_id, process_id)
    link = _get_link_for_company(company_id, process_id, link_id)
    if "resource_id" in payload:
        resource = _get_resource_for_company(company_id, int(payload.get("resource_id") or 0))
        link.resource_id = resource.id
    if "process_routine_id" in payload:
        process_routine_id = payload.get("process_routine_id")
        link.process_routine_id = int(process_routine_id) if process_routine_id not in (None, "") else None
        _validate_process_routine(company_id, process_id, link.process_routine_id)
    if "bpmn_element_id" in payload:
        link.bpmn_element_id = _clean_text(payload.get("bpmn_element_id"))
    if any(field in payload for field in ("used_quantity", "used_quantity_per_execution", "estimated_monthly_instances", "monthly_used_quantity", "usage_percentage", "allocated_monthly_cost", "estimated_cost_per_execution", "resource_id")):
        resource = _get_resource_for_company(company_id, int(link.resource_id or 0))
        metrics = _calculate_link_usage_metrics(resource, payload, link)
        link.used_quantity = metrics["used_quantity"]
        link.used_quantity_per_execution = metrics["used_quantity_per_execution"]
        link.estimated_monthly_instances = metrics["estimated_monthly_instances"]
        link.monthly_used_quantity = metrics["monthly_used_quantity"]
        link.usage_percentage = metrics["usage_percentage"]
        link.allocated_monthly_cost = metrics["allocated_monthly_cost"]
        link.estimated_cost_per_execution = metrics["estimated_cost_per_execution"]
    if "capacity_bottleneck_notes" in payload:
        link.capacity_bottleneck_notes = _clean_text(payload.get("capacity_bottleneck_notes"))
    if "is_active" in payload:
        link.is_active = bool(payload.get("is_active"))
    db.session.commit()
    return link


def deactivate_process_resource_link(company_id: int, process_id: int, link_id: int) -> ProcessResourceLink:
    link = _get_link_for_company(company_id, process_id, link_id)
    link.is_active = False
    db.session.commit()
    return link


def build_process_resources_bundle(company_id: int, process_id: int) -> dict:
    process = _get_process_for_company(company_id, process_id)
    links = list_process_resource_links(company_id, process_id)
    grouped = {resource_type: [] for resource_type in RESOURCE_TYPE_VALUES}
    totals = {
        "allocated_monthly_cost": 0.0,
        "estimated_cost_per_execution": 0.0,
        "capex_registered": 0.0,
        "monthly_recurring_registered": 0.0,
        "used_quantity_total": 0.0,
    }

    serialized_links = []
    for link in links:
        payload = link.to_dict(include_resource=True)
        resource = payload.get("resource") or {}
        if link.resource:
            payload.setdefault("resource", {})["usage"] = get_resource_usage_summary(company_id, link.resource.id)
        serialized_links.append(payload)
        grouped.setdefault(resource.get("type") or "other", []).append(payload)
        totals["allocated_monthly_cost"] += float(link.allocated_monthly_cost or 0)
        totals["estimated_cost_per_execution"] += float(link.estimated_cost_per_execution or 0)
        totals["used_quantity_total"] += _link_monthly_used_quantity(link)
        if link.resource:
            totals["capex_registered"] += float(link.resource.acquisition_total_amount or 0) + float(link.resource.installation_total_amount or 0)
            totals["monthly_recurring_registered"] += float(link.resource.monthly_recurring_amount or 0)

    return {
        "process": {
            "id": process.id,
            "company_id": process.company_id,
            "code": process.code,
            "name": process.name,
        },
        "resource_types": list(RESOURCE_TYPE_VALUES),
        "capacity_units": list(RESOURCE_CAPACITY_UNIT_VALUES),
        "totals": totals,
        "links": serialized_links,
        "grouped": grouped,
    }


def build_resource_catalog_bundle(company_id: int, *, resource_type: str | None = None, active_only: bool = False) -> dict:
    resources = list_resources(company_id, resource_type=resource_type, active_only=active_only)
    grouped = {resource_type_key: [] for resource_type_key in RESOURCE_TYPE_VALUES}
    totals = {
        "resources_count": len(resources),
        "quantity_total": 0.0,
        "used_quantity_total": 0.0,
        "available_quantity_total": 0.0,
        "allocated_monthly_cost_total": 0.0,
    }
    serialized = []
    for resource in resources:
        payload = serialize_resource_with_usage(resource)
        usage = payload.get("usage") or {}
        serialized.append(payload)
        grouped.setdefault(resource.type, []).append(payload)
        totals["quantity_total"] += float(resource.quantity or 0)
        totals["used_quantity_total"] += float(usage.get("used_quantity_total") or 0)
        totals["available_quantity_total"] += float(usage.get("available_quantity") or 0)
        totals["allocated_monthly_cost_total"] += sum(
            float(link.allocated_monthly_cost or 0)
            for link in ProcessResourceLink.query.filter_by(
                company_id=company_id,
                resource_id=resource.id,
                is_active=True,
            ).all()
        )
    return {
        "resource_types": list(RESOURCE_TYPE_VALUES),
        "capacity_units": list(RESOURCE_CAPACITY_UNIT_VALUES),
        "totals": totals,
        "resources": serialized,
        "grouped": grouped,
    }
