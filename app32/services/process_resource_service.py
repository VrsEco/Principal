from decimal import Decimal, InvalidOperation

from datetime import datetime

from models import (
    CapabilityDimension,
    Process,
    ProcessExecutionPlan,
    ProcessInstance,
    ProcessResourceLink,
    ProcessRoutine,
    ResourceCatalog,
    db,
)
from models.process_resource import (
    CAPABILITY_CRITICALITY_VALUES,
    RESOURCE_CAPACITY_PERIOD_VALUES,
    RESOURCE_CAPACITY_UNIT_VALUES,
    RESOURCE_TYPE_VALUES,
)


DEFAULT_CAPABILITY_DIMENSIONS = (
    ("Ativos e Estrutura Física", "Ativos, equipamentos, instalações e condições físicas habilitadoras.", 10),
    ("Pessoas, Papéis e Competências", "Papéis, equipes e competências necessários à execução.", 20),
    ("Tecnologia, Dados e Sistemas", "Sistemas, aplicações, integrações e dados necessários à execução.", 30),
    ("Documentos e Conhecimento", "Documentos, procedimentos, registros e conhecimento controlado.", 40),
    ("Materiais, Insumos e Serviços", "Materiais, insumos, fornecedores e serviços necessários à execução.", 50),
)

LEGACY_TYPE_TO_DIMENSION = {
    "people": "Pessoas, Papéis e Competências",
    "digital_it": "Tecnologia, Dados e Sistemas",
    "facilities": "Ativos e Estrutura Física",
    "equipment_tools": "Ativos e Estrutura Física",
    "inputs": "Materiais, Insumos e Serviços",
    "other": "Documentos e Conhecimento",
}

DIMENSION_TO_LEGACY_TYPE = {
    "Pessoas, Papéis e Competências": "people",
    "Tecnologia, Dados e Sistemas": "digital_it",
    "Ativos e Estrutura Física": "facilities",
    "Materiais, Insumos e Serviços": "inputs",
    "Documentos e Conhecimento": "other",
}


class ProcessResourceValidationError(ValueError):
    """Erro de validação funcional da camada de recursos habilitadores."""


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


def _percentage_or_none(value, *, field: str = "percentual", maximum: Decimal | None = None):
    parsed = _decimal_or_none(value, field=field)
    if parsed is not None and maximum is not None and parsed > maximum:
        raise ProcessResourceValidationError(f"{field} não pode ser maior que {maximum}.")
    return parsed


def _criticality_or_none(value):
    normalized = _clean_text(value)
    if normalized and normalized not in CAPABILITY_CRITICALITY_VALUES:
        raise ProcessResourceValidationError("criticidade da capacidade inválida.")
    return normalized


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


def _get_dimension_for_company(company_id: int, dimension_id: int) -> CapabilityDimension:
    dimension = CapabilityDimension.query.filter_by(id=dimension_id, company_id=company_id).first()
    if not dimension:
        raise ProcessResourceValidationError("Dimensão habilitadora não encontrada para este tenant.")
    return dimension


def ensure_default_capability_dimensions(company_id: int):
    existing = CapabilityDimension.query.filter_by(company_id=company_id).all()
    by_name = {item.name: item for item in existing}
    changed = False
    for name, description, order_index in DEFAULT_CAPABILITY_DIMENSIONS:
        if name in by_name:
            continue
        dimension = CapabilityDimension(
            company_id=company_id,
            name=name,
            description=description,
            order_index=order_index,
            is_active=True,
        )
        db.session.add(dimension)
        by_name[name] = dimension
        changed = True
    if changed:
        db.session.flush()
    return by_name


def list_capability_dimensions(company_id: int, *, active_only: bool = False):
    ensure_default_capability_dimensions(company_id)
    query = CapabilityDimension.query.filter_by(company_id=company_id)
    if active_only:
        query = query.filter(CapabilityDimension.is_active.is_(True))
    dimensions = query.order_by(CapabilityDimension.order_index.asc(), CapabilityDimension.name.asc()).all()
    db.session.commit()
    return dimensions


def create_capability_dimension(company_id: int, payload: dict) -> CapabilityDimension:
    name = _clean_text(payload.get("name"), required=True, field="nome da dimensão")
    duplicate = CapabilityDimension.query.filter_by(company_id=company_id, name=name).first()
    if duplicate:
        raise ProcessResourceValidationError("Já existe uma dimensão habilitadora com este nome.")
    dimension = CapabilityDimension(
        company_id=company_id,
        name=name,
        description=_clean_text(payload.get("description")),
        order_index=int(payload.get("order_index") or 0),
        is_active=_bool_or_default(payload.get("is_active"), True),
    )
    db.session.add(dimension)
    db.session.commit()
    return dimension


def update_capability_dimension(company_id: int, dimension_id: int, payload: dict) -> CapabilityDimension:
    dimension = _get_dimension_for_company(company_id, dimension_id)
    if "name" in payload:
        name = _clean_text(payload.get("name"), required=True, field="nome da dimensão")
        duplicate = CapabilityDimension.query.filter(
            CapabilityDimension.company_id == company_id,
            CapabilityDimension.name == name,
            CapabilityDimension.id != dimension.id,
        ).first()
        if duplicate:
            raise ProcessResourceValidationError("Já existe uma dimensão habilitadora com este nome.")
        dimension.name = name
    if "description" in payload:
        dimension.description = _clean_text(payload.get("description"))
    if "order_index" in payload:
        dimension.order_index = int(payload.get("order_index") or 0)
    if "is_active" in payload:
        dimension.is_active = bool(payload.get("is_active"))
    db.session.commit()
    return dimension


def deactivate_capability_dimension(company_id: int, dimension_id: int) -> CapabilityDimension:
    dimension = _get_dimension_for_company(company_id, dimension_id)
    if ResourceCatalog.query.filter_by(company_id=company_id, dimension_id=dimension.id, is_active=True).first():
        raise ProcessResourceValidationError("Dimensão com recursos habilitadores ativos não pode ser inativada.")
    dimension.is_active = False
    db.session.commit()
    return dimension


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


def _resolve_capability_dimension(company_id: int, payload: dict, *, current=None) -> CapabilityDimension:
    dimension_id = payload.get("dimension_id")
    if dimension_id not in (None, ""):
        dimension = _get_dimension_for_company(company_id, int(dimension_id))
        if not dimension.is_active:
            raise ProcessResourceValidationError("Dimensão habilitadora inativa não pode receber capacidades.")
        return dimension
    if current is not None and current.dimension_id:
        return _get_dimension_for_company(company_id, current.dimension_id)
    by_name = ensure_default_capability_dimensions(company_id)
    legacy_type = str(payload.get("type") or "other").strip()
    return by_name[LEGACY_TYPE_TO_DIMENSION.get(legacy_type, "Documentos e Conhecimento")]


def _legacy_type_for_dimension(dimension: CapabilityDimension, payload: dict, *, current=None) -> str:
    if payload.get("type") not in (None, ""):
        return _validate_resource_type(payload.get("type"))
    if current is not None and current.type:
        return current.type
    return DIMENSION_TO_LEGACY_TYPE.get(dimension.name, "other")


def _validate_capacity_unit(unit: str | None) -> str | None:
    normalized = _clean_text(unit)
    if normalized and normalized not in RESOURCE_CAPACITY_UNIT_VALUES:
        raise ProcessResourceValidationError("unidade de capacidade operacional inválida.")
    return normalized


def _validate_capacity_period(period: str | None) -> str | None:
    normalized = _clean_text(period)
    if normalized and normalized not in RESOURCE_CAPACITY_PERIOD_VALUES:
        raise ProcessResourceValidationError("período da capacidade operacional inválido.")
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


def list_resources(
    company_id: int,
    *,
    resource_type: str | None = None,
    dimension_id: int | None = None,
    active_only: bool = False,
):
    query = ResourceCatalog.query.filter_by(company_id=company_id)
    if resource_type:
        query = query.filter(ResourceCatalog.type == _validate_resource_type(resource_type))
    if active_only:
        query = query.filter(ResourceCatalog.is_active.is_(True))
    if dimension_id:
        _get_dimension_for_company(company_id, int(dimension_id))
        query = query.filter(ResourceCatalog.dimension_id == int(dimension_id))
    return (
        query.join(CapabilityDimension, CapabilityDimension.id == ResourceCatalog.dimension_id)
        .order_by(CapabilityDimension.order_index.asc(), ResourceCatalog.subtype.asc(), ResourceCatalog.item_name.asc())
        .all()
    )


def _resource_capacity_total(resource: ResourceCatalog) -> float | None:
    """Capacidade operacional normalizada para um horizonte mensal."""
    if resource.operational_capacity_value is not None:
        value = float(resource.operational_capacity_value)
        factors = {"day": 22.0, "week": 52.0 / 12.0, "month": 1.0, "quarter": 1.0 / 3.0, "year": 1.0 / 12.0}
        return value * factors.get(resource.operational_capacity_period or "month", 1.0)
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
        usage_percentage = (monthly_used / Decimal(str(capacity_total))) * Decimal("100")
    elif "usage_percentage" in payload:
        usage_percentage = _percentage_or_none(payload.get("usage_percentage"))

    cost_per_execution = _decimal_or_none(
        payload.get("estimated_cost_per_execution"),
        field="custo estimado por execução",
    ) if ("estimated_cost_per_execution" in payload or link is None) else link.estimated_cost_per_execution
    if cost_per_execution is None and used_per_execution is not None and resource.unit_value is not None:
        cost_per_execution = used_per_execution * Decimal(str(resource.unit_value))
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
    actual_quantity = sum(
        float(link.used_quantity_per_execution or 0) * _actual_monthly_instances(company_id, link.process_id)
        for link in links
    )
    capacity_total = _resource_capacity_total(resource)
    available_quantity = capacity_total - used_quantity if capacity_total is not None else None
    used_percentage_total = (
        (used_quantity / capacity_total) * 100
        if capacity_total and capacity_total > 0
        else sum(float(link.usage_percentage or 0) for link in links)
    )
    return {
        "capacity_total": capacity_total,
        "capacity_horizon": "month",
        "planned_demand": used_quantity,
        "planned_utilization_percentage": used_percentage_total,
        "actual_demand": actual_quantity,
        "actual_utilization_percentage": ((actual_quantity / capacity_total) * 100) if capacity_total else None,
        "remaining_planned_capacity": available_quantity,
        "used_quantity_total": used_quantity,
        "available_quantity": available_quantity,
        "usage_percentage_total": used_percentage_total,
        "is_overloaded": bool(used_percentage_total > 100),
        "max_recommended_utilization_pct": float(resource.max_recommended_utilization_pct or 100),
        "is_above_recommended": bool(used_percentage_total > float(resource.max_recommended_utilization_pct or 100)),
        "active_allocations_count": len(links),
    }


def serialize_resource_with_usage(resource: ResourceCatalog) -> dict:
    payload = resource.to_dict()
    payload["usage"] = get_resource_usage_summary(resource.company_id, resource.id)
    return payload


def create_resource(company_id: int, payload: dict) -> ResourceCatalog:
    dimension = _resolve_capability_dimension(company_id, payload)
    resource_type = _legacy_type_for_dimension(dimension, payload)
    subtype = _clean_text(payload.get("subtype")) or dimension.name
    notes = _clean_text(payload.get("notes"))

    resource = ResourceCatalog(
        company_id=company_id,
        dimension_id=dimension.id,
        type=resource_type,
        subtype=subtype,
        item_name=_clean_text(payload.get("name", payload.get("item_name")), required=True, field="nome da capacidade"),
        unit_value=_decimal_or_none(payload.get("unit_value"), field="valor unitário"),
        quantity=_decimal_or_none(payload.get("quantity"), field="quantidade"),
        acquisition_total_amount=_decimal_or_none(payload.get("acquisition_total_amount"), field="gasto total de aquisição"),
        installation_total_amount=_decimal_or_none(payload.get("installation_total_amount"), field="gasto total de instalação"),
        monthly_recurring_amount=_decimal_or_none(payload.get("monthly_recurring_amount"), field="gasto mensal recorrente"),
        operational_capacity_value=_decimal_or_none(payload.get("operational_capacity_value"), field="capacidade operacional"),
        operational_capacity_unit=_validate_capacity_unit(payload.get("operational_capacity_unit")),
        operational_capacity_period=_validate_capacity_period(payload.get("operational_capacity_period")) or "month",
        max_recommended_utilization_pct=_percentage_or_none(payload.get("max_recommended_utilization_pct", 100), field="utilização máxima recomendada", maximum=Decimal("100")),
        estimated_useful_life=_clean_text(payload.get("estimated_useful_life")),
        notes=notes,
        is_active=_bool_or_default(payload.get("is_active"), True),
    )
    db.session.add(resource)
    db.session.commit()
    return resource


def update_resource(company_id: int, resource_id: int, payload: dict) -> ResourceCatalog:
    resource = _get_resource_for_company(company_id, resource_id)
    dimension = _resolve_capability_dimension(company_id, payload, current=resource)
    resource.dimension_id = dimension.id
    if "type" in payload:
        resource.type = _validate_resource_type(payload.get("type"))
    elif "dimension_id" in payload:
        resource.type = _legacy_type_for_dimension(dimension, payload)
    if "subtype" in payload:
        resource.subtype = _clean_text(payload.get("subtype")) or dimension.name
    if "item_name" in payload or "name" in payload:
        resource.item_name = _clean_text(payload.get("name", payload.get("item_name")), required=True, field="nome da capacidade")
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
    if "operational_capacity_period" in payload:
        resource.operational_capacity_period = _validate_capacity_period(payload.get("operational_capacity_period")) or "month"
    if "max_recommended_utilization_pct" in payload:
        resource.max_recommended_utilization_pct = _percentage_or_none(payload.get("max_recommended_utilization_pct"), field="utilização máxima recomendada", maximum=Decimal("100"))
    if "estimated_useful_life" in payload:
        resource.estimated_useful_life = _clean_text(payload.get("estimated_useful_life"))
    if "notes" in payload:
        resource.notes = _clean_text(payload.get("notes"))
    if "is_active" in payload:
        resource.is_active = bool(payload.get("is_active"))

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


def get_process_execution_plan(company_id: int, process_id: int) -> ProcessExecutionPlan | None:
    _get_process_for_company(company_id, process_id)
    return ProcessExecutionPlan.query.filter_by(company_id=company_id, process_id=process_id).first()


def upsert_process_execution_plan(company_id: int, process_id: int, payload: dict) -> ProcessExecutionPlan:
    _get_process_for_company(company_id, process_id)
    plan = ProcessExecutionPlan.query.filter_by(company_id=company_id, process_id=process_id).first()
    if plan is None:
        plan = ProcessExecutionPlan(company_id=company_id, process_id=process_id)
        db.session.add(plan)
    if "frequency_count" in payload:
        plan.frequency_count = _decimal_or_none(payload.get("frequency_count"), field="quantidade de execuções") or Decimal("0")
    if "frequency_period" in payload:
        period = _clean_text(payload.get("frequency_period"), required=True, field="período da frequência")
        if period not in RESOURCE_CAPACITY_PERIOD_VALUES:
            raise ProcessResourceValidationError("período da frequência inválido.")
        plan.frequency_period = period
    if "working_days_per_month" in payload:
        days = _decimal_or_none(payload.get("working_days_per_month"), field="dias úteis por mês")
        if days is None or days <= 0:
            raise ProcessResourceValidationError("dias úteis por mês deve ser maior que zero.")
        plan.working_days_per_month = days
    if "notes" in payload:
        plan.notes = _clean_text(payload.get("notes"))
    db.session.flush()
    monthly_instances = Decimal(str(plan.monthly_instances()))
    links = ProcessResourceLink.query.filter_by(company_id=company_id, process_id=process_id, is_active=True).all()
    for link in links:
        link.estimated_monthly_instances = monthly_instances
        if link.used_quantity_per_execution is not None:
            link.monthly_used_quantity = link.used_quantity_per_execution * monthly_instances
            link.used_quantity = link.monthly_used_quantity
            capacity = _resource_capacity_total(link.resource)
            link.usage_percentage = link.monthly_used_quantity / Decimal(str(capacity)) * Decimal("100") if capacity else None
    db.session.commit()
    return plan


def _actual_monthly_instances(company_id: int, process_id: int) -> int:
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    next_month = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1)
    return ProcessInstance.query.filter(
        ProcessInstance.company_id == company_id,
        ProcessInstance.process_id == process_id,
        ProcessInstance.status == "completed",
        ProcessInstance.completed_at >= month_start,
        ProcessInstance.completed_at < next_month,
    ).count()


def create_process_resource_link(company_id: int, process_id: int, payload: dict) -> ProcessResourceLink:
    _get_process_for_company(company_id, process_id)
    resource = _get_resource_for_company(company_id, int(payload.get("resource_id") or 0))
    if not resource.is_active:
        raise ProcessResourceValidationError("Recurso inativo não pode ser vinculado a novo processo.")
    process_routine_id = payload.get("process_routine_id")
    process_routine_id = int(process_routine_id) if process_routine_id not in (None, "") else None
    _validate_process_routine(company_id, process_id, process_routine_id)

    metrics_payload = dict(payload)
    plan = get_process_execution_plan(company_id, process_id)
    if plan is not None:
        metrics_payload["estimated_monthly_instances"] = plan.monthly_instances()

    link = ProcessResourceLink(
        company_id=company_id,
        process_id=process_id,
        process_routine_id=process_routine_id,
        bpmn_element_id=_clean_text(payload.get("bpmn_element_id")),
        resource_id=resource.id,
        **_calculate_link_usage_metrics(resource, metrics_payload),
        capacity_bottleneck_notes=_clean_text(payload.get("capacity_bottleneck_notes")),
        required_condition=_clean_text(payload.get("required_condition")),
        criticality=_criticality_or_none(payload.get("criticality")),
        gap_notes=_clean_text(payload.get("gap_notes")),
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
    if "required_condition" in payload:
        link.required_condition = _clean_text(payload.get("required_condition"))
    if "criticality" in payload:
        link.criticality = _criticality_or_none(payload.get("criticality"))
    if "gap_notes" in payload:
        link.gap_notes = _clean_text(payload.get("gap_notes"))
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
    plan = get_process_execution_plan(company_id, process_id)
    actual_instances = _actual_monthly_instances(company_id, process_id)
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
    grouped_by_dimension = {}
    for link in links:
        payload = link.to_dict(include_resource=True)
        resource = payload.get("resource") or {}
        if link.resource:
            usage = get_resource_usage_summary(company_id, link.resource.id)
            actual_demand = float(link.used_quantity_per_execution or 0) * actual_instances
            capacity_total = usage.get("capacity_total")
            payload["actual_monthly_instances"] = actual_instances
            payload["actual_used_quantity"] = actual_demand
            payload["actual_usage_percentage"] = ((actual_demand / capacity_total) * 100) if capacity_total else None
            payload.setdefault("resource", {})["usage"] = usage
        serialized_links.append(payload)
        grouped.setdefault(resource.get("type") or "other", []).append(payload)
        dimension = resource.get("dimension") or {}
        dimension_key = str(dimension.get("id") or "unclassified")
        grouped_by_dimension.setdefault(
            dimension_key,
            {"dimension": dimension, "enabling_resources": [], "capabilities": []},
        )["enabling_resources"].append(payload)
        grouped_by_dimension[dimension_key]["capabilities"].append(payload)
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
            "macro_process_id": process.macro_id,
        },
        "execution_plan": plan.to_dict() if plan else None,
        "actual_monthly_instances": actual_instances,
        "resource_types": list(RESOURCE_TYPE_VALUES),
        "criticality_values": list(CAPABILITY_CRITICALITY_VALUES),
        "capacity_units": list(RESOURCE_CAPACITY_UNIT_VALUES),
        "totals": totals,
        "links": serialized_links,
        "grouped": grouped,
        "grouped_by_dimension": list(grouped_by_dimension.values()),
    }


def build_resource_catalog_bundle(
    company_id: int,
    *,
    resource_type: str | None = None,
    dimension_id: int | None = None,
    active_only: bool = False,
) -> dict:
    dimensions = list_capability_dimensions(company_id, active_only=False)
    resources = list_resources(
        company_id,
        resource_type=resource_type,
        dimension_id=dimension_id,
        active_only=active_only,
    )
    grouped = {resource_type_key: [] for resource_type_key in RESOURCE_TYPE_VALUES}
    totals = {
        "resources_count": len(resources),
        "quantity_total": 0.0,
        "used_quantity_total": 0.0,
        "available_quantity_total": 0.0,
        "allocated_monthly_cost_total": 0.0,
    }
    serialized = []
    grouped_by_dimension = {
        str(dimension.id): {"dimension": dimension.to_dict(), "enabling_resources": [], "capabilities": []}
        for dimension in dimensions
    }
    for resource in resources:
        payload = serialize_resource_with_usage(resource)
        usage = payload.get("usage") or {}
        serialized.append(payload)
        grouped.setdefault(resource.type, []).append(payload)
        grouped_by_dimension.setdefault(
            str(resource.dimension_id),
            {"dimension": resource.dimension.to_dict() if resource.dimension else {}, "enabling_resources": [], "capabilities": []},
        )["enabling_resources"].append(payload)
        grouped_by_dimension[str(resource.dimension_id)]["capabilities"].append(payload)
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
        "dimensions": [dimension.to_dict() for dimension in dimensions],
        "capacity_units": list(RESOURCE_CAPACITY_UNIT_VALUES),
        "capacity_periods": list(RESOURCE_CAPACITY_PERIOD_VALUES),
        "totals": totals,
        "resources": serialized,
        "grouped": grouped,
        "grouped_by_dimension": list(grouped_by_dimension.values()),
    }


# Contratos canônicos.
list_enabling_resources = list_resources
create_enabling_resource = create_resource
update_enabling_resource = update_resource
deactivate_enabling_resource = deactivate_resource
create_process_enabling_resource_link = create_process_resource_link
update_process_enabling_resource_link = update_process_resource_link
deactivate_process_enabling_resource_link = deactivate_process_resource_link
build_enabling_resource_catalog_bundle = build_resource_catalog_bundle
build_process_enabling_resources_bundle = build_process_resources_bundle

# Aliases transitórios da nomenclatura anterior.
list_capabilities = list_resources
create_capability = create_resource
update_capability = update_resource
deactivate_capability = deactivate_resource
create_process_capability_link = create_process_resource_link
update_process_capability_link = update_process_resource_link
deactivate_process_capability_link = deactivate_process_resource_link
build_capability_catalog_bundle = build_resource_catalog_bundle
build_process_capabilities_bundle = build_process_resources_bundle
