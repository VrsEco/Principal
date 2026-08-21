from datetime import datetime

from . import db


RESOURCE_TYPE_VALUES = (
    "people",
    "inputs",
    "facilities",
    "digital_it",
    "equipment_tools",
    "other",
)

RESOURCE_CAPACITY_UNIT_VALUES = ("hour", "unit", "transaction", "license", "person", "item")
RESOURCE_CAPACITY_PERIOD_VALUES = ("day", "week", "month", "quarter", "year")
CAPABILITY_CRITICALITY_VALUES = ("low", "medium", "high", "critical")


class CapabilityDimension(db.Model):
    """Dimensão habilitadora do catálogo corporativo do tenant."""

    __tablename__ = "capability_dimensions"
    __table_args__ = (
        db.UniqueConstraint("company_id", "name", name="uq_capability_dimensions_company_name"),
        db.Index("ix_capability_dimensions_company_order", "company_id", "order_index"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "order_index": self.order_index,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ResourceCatalog(db.Model):
    """Recurso habilitador tenant-safe (tabela legada preservada)."""

    __tablename__ = "resource_catalog"
    __table_args__ = (
        db.CheckConstraint(
            "type IN ('people', 'inputs', 'facilities', 'digital_it', 'equipment_tools', 'other')",
            name="ck_resource_catalog_type",
        ),
        db.CheckConstraint(
            "operational_capacity_unit IS NULL OR operational_capacity_unit IN ('hour', 'unit', 'transaction', 'license', 'person', 'item')",
            name="ck_resource_catalog_capacity_unit",
        ),
        db.CheckConstraint(
            "operational_capacity_period IS NULL OR operational_capacity_period IN ('day', 'week', 'month', 'quarter', 'year')",
            name="ck_resource_catalog_capacity_period",
        ),
        db.CheckConstraint(
            "max_recommended_utilization_pct IS NULL OR (max_recommended_utilization_pct >= 0 AND max_recommended_utilization_pct <= 100)",
            name="ck_resource_catalog_max_utilization",
        ),
        db.CheckConstraint("unit_value IS NULL OR unit_value >= 0", name="ck_resource_catalog_unit_value_non_negative"),
        db.CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_resource_catalog_quantity_non_negative"),
        db.CheckConstraint(
            "acquisition_total_amount IS NULL OR acquisition_total_amount >= 0",
            name="ck_resource_catalog_acquisition_non_negative",
        ),
        db.CheckConstraint(
            "installation_total_amount IS NULL OR installation_total_amount >= 0",
            name="ck_resource_catalog_installation_non_negative",
        ),
        db.CheckConstraint(
            "monthly_recurring_amount IS NULL OR monthly_recurring_amount >= 0",
            name="ck_resource_catalog_monthly_non_negative",
        ),
        db.Index("ix_resource_catalog_company_type", "company_id", "type"),
        db.Index("ix_resource_catalog_company_subtype", "company_id", "subtype"),
        db.Index("ix_resource_catalog_company_dimension", "company_id", "dimension_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    dimension_id = db.Column(
        db.Integer,
        db.ForeignKey("capability_dimensions.id"),
        nullable=False,
        index=True,
    )
    type = db.Column(db.String(40), nullable=False)
    subtype = db.Column(db.String(120), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    unit_value = db.Column(db.Numeric(14, 2), nullable=True)
    quantity = db.Column(db.Numeric(14, 2), nullable=True)
    acquisition_total_amount = db.Column(db.Numeric(14, 2), nullable=True)
    installation_total_amount = db.Column(db.Numeric(14, 2), nullable=True)
    monthly_recurring_amount = db.Column(db.Numeric(14, 2), nullable=True)
    operational_capacity_value = db.Column(db.Numeric(14, 2), nullable=True)
    operational_capacity_unit = db.Column(db.String(20), nullable=True)
    operational_capacity_period = db.Column(db.String(20), nullable=True, default="month")
    max_recommended_utilization_pct = db.Column(db.Numeric(5, 2), nullable=True, default=100)
    estimated_useful_life = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process_links = db.relationship(
        "ProcessResourceLink",
        backref="resource",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    dimension = db.relationship(
        "CapabilityDimension",
        backref=db.backref("capabilities", lazy="dynamic"),
    )

    def to_dict(self):
        def num(value):
            return float(value) if value is not None else None

        return {
            "id": self.id,
            "company_id": self.company_id,
            "dimension_id": self.dimension_id,
            "dimension": self.dimension.to_dict() if self.dimension else None,
            "type": self.type,
            "subtype": self.subtype,
            "item_name": self.item_name,
            "name": self.item_name,
            "unit_value": num(self.unit_value),
            "quantity": num(self.quantity),
            "acquisition_total_amount": num(self.acquisition_total_amount),
            "installation_total_amount": num(self.installation_total_amount),
            "monthly_recurring_amount": num(self.monthly_recurring_amount),
            "operational_capacity_value": num(self.operational_capacity_value),
            "operational_capacity_unit": self.operational_capacity_unit,
            "operational_capacity_period": self.operational_capacity_period,
            "max_recommended_utilization_pct": num(self.max_recommended_utilization_pct),
            "estimated_useful_life": self.estimated_useful_life,
            "notes": self.notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessResourceLink(db.Model):
    """Vínculo tenant-safe entre capacidade e processo/atividade/elemento BPMN."""

    __tablename__ = "process_resource_links"
    __table_args__ = (
        db.CheckConstraint(
            "allocated_monthly_cost IS NULL OR allocated_monthly_cost >= 0",
            name="ck_process_resource_links_allocated_monthly_non_negative",
        ),
        db.CheckConstraint(
            "estimated_cost_per_execution IS NULL OR estimated_cost_per_execution >= 0",
            name="ck_process_resource_links_execution_cost_non_negative",
        ),
        db.CheckConstraint(
            "used_quantity IS NULL OR used_quantity >= 0",
            name="ck_process_resource_links_used_quantity_non_negative",
        ),
        db.CheckConstraint(
            "used_quantity_per_execution IS NULL OR used_quantity_per_execution >= 0",
            name="ck_process_resource_links_used_per_execution_non_negative",
        ),
        db.CheckConstraint(
            "estimated_monthly_instances IS NULL OR estimated_monthly_instances >= 0",
            name="ck_process_resource_links_instances_non_negative",
        ),
        db.CheckConstraint(
            "monthly_used_quantity IS NULL OR monthly_used_quantity >= 0",
            name="ck_process_resource_links_monthly_used_non_negative",
        ),
        db.CheckConstraint("usage_percentage IS NULL OR usage_percentage >= 0", name="ck_process_resource_links_usage_percentage_non_negative"),
        db.CheckConstraint(
            "criticality IS NULL OR criticality IN ('low', 'medium', 'high', 'critical')",
            name="ck_process_resource_links_criticality",
        ),
        db.Index("ix_process_resource_links_company_process", "company_id", "process_id"),
        db.Index("ix_process_resource_links_company_resource", "company_id", "resource_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    process_routine_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), nullable=True, index=True)
    bpmn_element_id = db.Column(db.String(255), nullable=True, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource_catalog.id"), nullable=False, index=True)
    used_quantity = db.Column(db.Numeric(14, 2), nullable=True)  # compat: consumo mensal estimado
    used_quantity_per_execution = db.Column(db.Numeric(14, 2), nullable=True)
    estimated_monthly_instances = db.Column(db.Numeric(14, 2), nullable=True)
    monthly_used_quantity = db.Column(db.Numeric(14, 2), nullable=True)
    usage_percentage = db.Column(db.Numeric(7, 4), nullable=True)
    allocated_monthly_cost = db.Column(db.Numeric(14, 2), nullable=True)
    estimated_cost_per_execution = db.Column(db.Numeric(14, 2), nullable=True)
    capacity_bottleneck_notes = db.Column(db.Text, nullable=True)
    required_condition = db.Column(db.Text, nullable=True)
    criticality = db.Column(db.String(20), nullable=True)
    gap_notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process = db.relationship("Process", backref=db.backref("resource_links", lazy="dynamic", cascade="all, delete-orphan"))
    process_routine = db.relationship("ProcessRoutine", backref=db.backref("resource_links", lazy="dynamic"))

    def to_dict(self, include_resource: bool = True):
        def num(value):
            return float(value) if value is not None else None

        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "process_routine_id": self.process_routine_id,
            "bpmn_element_id": self.bpmn_element_id,
            "resource_id": self.resource_id,
            "used_quantity": num(self.used_quantity),
            "used_quantity_per_execution": num(self.used_quantity_per_execution),
            "estimated_monthly_instances": num(self.estimated_monthly_instances),
            "monthly_used_quantity": num(self.monthly_used_quantity),
            "usage_percentage": num(self.usage_percentage),
            "allocated_monthly_cost": num(self.allocated_monthly_cost),
            "estimated_cost_per_execution": num(self.estimated_cost_per_execution),
            "capacity_bottleneck_notes": self.capacity_bottleneck_notes,
            "required_condition": self.required_condition,
            "criticality": self.criticality,
            "gap_notes": self.gap_notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_resource:
            payload["resource"] = self.resource.to_dict() if self.resource else None
            payload["enabling_resource"] = payload["resource"]
            payload["capability"] = payload["resource"]
        return payload


# Aliases canônicos para código novo, preservando consumidores legados.
EnablingResource = ResourceCatalog
ProcessEnablingResourceLink = ProcessResourceLink
# Aliases transitórios da primeira nomenclatura proposta.
EnablingCapability = ResourceCatalog
ProcessCapabilityLink = ProcessResourceLink


class ProcessExecutionPlan(db.Model):
    """Planejamento único de recorrência do processo, normalizado para análise mensal."""

    __tablename__ = "process_execution_plans"
    __table_args__ = (
        db.UniqueConstraint("company_id", "process_id", name="uq_process_execution_plans_company_process"),
        db.CheckConstraint("frequency_period IN ('day', 'week', 'month', 'quarter', 'year')", name="ck_process_execution_plans_period"),
        db.CheckConstraint("frequency_count >= 0", name="ck_process_execution_plans_count"),
        db.CheckConstraint("working_days_per_month > 0", name="ck_process_execution_plans_working_days"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    frequency_count = db.Column(db.Numeric(14, 2), nullable=False, default=1)
    frequency_period = db.Column(db.String(20), nullable=False, default="month")
    working_days_per_month = db.Column(db.Numeric(6, 2), nullable=False, default=22)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def monthly_instances(self):
        count = float(self.frequency_count or 0)
        factors = {
            "day": float(self.working_days_per_month or 22),
            "week": 52.0 / 12.0,
            "month": 1.0,
            "quarter": 1.0 / 3.0,
            "year": 1.0 / 12.0,
        }
        return count * factors.get(self.frequency_period, 1.0)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "frequency_count": float(self.frequency_count or 0),
            "frequency_period": self.frequency_period,
            "working_days_per_month": float(self.working_days_per_month or 22),
            "planned_monthly_instances": self.monthly_instances(),
            "notes": self.notes,
        }
