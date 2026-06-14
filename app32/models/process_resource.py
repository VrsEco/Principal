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

RESOURCE_CAPACITY_UNIT_VALUES = ("hour", "day", "month")


class ResourceCatalog(db.Model):
    """Catálogo tenant-safe de recursos operacionais."""

    __tablename__ = "resource_catalog"
    __table_args__ = (
        db.CheckConstraint(
            "type IN ('people', 'inputs', 'facilities', 'digital_it', 'equipment_tools', 'other')",
            name="ck_resource_catalog_type",
        ),
        db.CheckConstraint(
            "operational_capacity_unit IS NULL OR operational_capacity_unit IN ('hour', 'day', 'month')",
            name="ck_resource_catalog_capacity_unit",
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
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
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

    def to_dict(self):
        def num(value):
            return float(value) if value is not None else None

        return {
            "id": self.id,
            "company_id": self.company_id,
            "type": self.type,
            "subtype": self.subtype,
            "item_name": self.item_name,
            "unit_value": num(self.unit_value),
            "quantity": num(self.quantity),
            "acquisition_total_amount": num(self.acquisition_total_amount),
            "installation_total_amount": num(self.installation_total_amount),
            "monthly_recurring_amount": num(self.monthly_recurring_amount),
            "operational_capacity_value": num(self.operational_capacity_value),
            "operational_capacity_unit": self.operational_capacity_unit,
            "estimated_useful_life": self.estimated_useful_life,
            "notes": self.notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessResourceLink(db.Model):
    """Vínculo tenant-safe entre recurso e processo/atividade/elemento BPMN."""

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
            "usage_percentage IS NULL OR (usage_percentage >= 0 AND usage_percentage <= 100)",
            name="ck_process_resource_links_usage_percentage_range",
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
    used_quantity = db.Column(db.Numeric(14, 2), nullable=True)
    usage_percentage = db.Column(db.Numeric(7, 4), nullable=True)
    allocated_monthly_cost = db.Column(db.Numeric(14, 2), nullable=True)
    estimated_cost_per_execution = db.Column(db.Numeric(14, 2), nullable=True)
    capacity_bottleneck_notes = db.Column(db.Text, nullable=True)
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
            "usage_percentage": num(self.usage_percentage),
            "allocated_monthly_cost": num(self.allocated_monthly_cost),
            "estimated_cost_per_execution": num(self.estimated_cost_per_execution),
            "capacity_bottleneck_notes": self.capacity_bottleneck_notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_resource:
            payload["resource"] = self.resource.to_dict() if self.resource else None
        return payload
