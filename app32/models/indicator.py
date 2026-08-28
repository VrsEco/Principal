from datetime import datetime
from . import db

INDICATOR_LINK_TARGET_TYPES = (
    "process",
    "project",
    "okr_global",
    "okr_area",
    "strategic_objective",
)

INDICATOR_LINK_ROLES = ("primary", "secondary", "diagnostic", "control")
INDICATOR_HEALTH_DIMENSIONS = (
    "prazo",
    "qualidade",
    "custo",
    "risco",
    "capacidade",
    "conformidade",
    "resultado",
    "estrategia",
)


class IndicatorGroup(db.Model):
    """Legacy Group for organizing indicators"""

    __tablename__ = "indicator_groups"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("indicator_groups.id"), nullable=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    children = db.relationship("IndicatorGroup", backref=db.backref("parent", remote_side=[id]))

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }

class IndicatorTree(db.Model):
    """
    Árvore de Indicadores (Plano de Contas).
    Estrutura hierárquica independente para organização corporativa.
    """
    __tablename__ = 'indicator_tree'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('indicator_tree.id'), nullable=True)
    
    code = db.Column(db.String(50), nullable=False) # Ex: "1", "1.1"
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    children = db.relationship("IndicatorTree", backref=db.backref("parent", remote_side=[id]))

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "description": self.description
        }

class Indicator(db.Model):
    """Main indicator model (KPI) - Independent entity"""

    __tablename__ = "indicators"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    
    # Hierarchical link (Accounting Plan)
    tree_id = db.Column(db.Integer, db.ForeignKey('indicator_tree.id'), nullable=True)
    full_code = db.Column(db.String(100), index=True, unique=True) # Ex: AA.I.1.1
    
    # Legacy link
    group_id = db.Column(db.Integer, db.ForeignKey("indicator_groups.id"), nullable=True)
    
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Types and Sources
    indicator_type = db.Column(db.String(50), nullable=False, default='result') # effort, result, impact
    source_module = db.Column(db.String(50), nullable=False, default='manual') 
    source_id = db.Column(db.Integer, nullable=True) # Specific ID of the source object (Process, Project, etc.)
    source_scope = db.Column(db.String(50), nullable=False, default='company') # company, department, individual
    source_config = db.Column(db.JSON) # JSON for extra rules (min_instances, filters, etc.)
    
    collection_mode = db.Column(db.String(30), nullable=False, default='manual') 
    aggregation_function = db.Column(db.String(30), nullable=False, default='sum') 
    
    # Metrics
    unit = db.Column(db.String(50), default='pts')  # e.g., "R$", "%", "Un"
    polarity = db.Column(db.String(20), default='positive')  # positive, negative
    measurement_frequency = db.Column(db.String(30), default='monthly')  # weekly, monthly, bimonthly, quarterly, four_monthly, semiannual, annual
    formula = db.Column(db.Text)
    
    # Context links
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    responsible_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    
    # Metadata
    collaborators = db.Column(db.JSON)  # List of collaborator IDs
    data_source = db.Column(db.Text)
    notes = db.Column(db.Text)
    okr_reference = db.Column(db.String(255))
    okr_level = db.Column(db.String(50))
    
    is_active = db.Column(db.Boolean, default=True)
    
    # Link com Rotina (Workflow)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    tree_node = db.relationship('IndicatorTree', backref='indicators', lazy=True)
    group = db.relationship('IndicatorGroup', backref='indicators', lazy=True)
    process = db.relationship('Process', backref='indicators', lazy=True)
    project = db.relationship('Project', backref='indicators', lazy=True)
    responsible = db.relationship("Employee", foreign_keys=[responsible_id], backref="indicators_managed")
    goals = db.relationship("IndicatorGoal", backref="indicator", lazy="dynamic", cascade="all, delete-orphan")
    routine = db.relationship("Routine", backref="indicators", lazy=True)
    entity_links = db.relationship(
        "IndicatorEntityLink",
        backref="indicator",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "tree_id": self.tree_id,
            "full_code": self.full_code,
            "code": self.code,
            "name": self.name,
            "aggregation_function": self.aggregation_function,
            "unit": self.unit,
            "polarity": self.polarity,
            "measurement_frequency": self.measurement_frequency,
            "formula": self.formula,
            "responsible_id": self.responsible_id,
            "notes": self.notes,
            "indicator_type": self.indicator_type,
            "routine_id": self.routine_id,
            "source_module": self.source_module,
            "source_id": self.source_id,
            "source_scope": self.source_scope,
            "source_config": self.source_config,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
        }


class IndicatorEntityLink(db.Model):
    """Vínculo N:N tenant-safe entre indicador e objetos monitorados.

    Substitui gradualmente os vínculos diretos legados `process_id` e
    `project_id`, permitindo que um indicador monitore vários processos,
    projetos e objetos estratégicos — e vice-versa.
    """

    __tablename__ = "indicator_entity_links"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "indicator_id",
            "target_type",
            "target_ref",
            name="uq_indicator_entity_links_company_indicator_target",
        ),
        db.ForeignKeyConstraint(
            ["company_id", "indicator_id"],
            ["indicators.company_id", "indicators.id"],
            ondelete="CASCADE",
            name="fk_indicator_entity_links_company_indicator",
        ),
        db.CheckConstraint(
            f"target_type IN {INDICATOR_LINK_TARGET_TYPES}",
            name="ck_indicator_entity_links_target_type",
        ),
        db.CheckConstraint(
            f"role IN {INDICATOR_LINK_ROLES}",
            name="ck_indicator_entity_links_role",
        ),
        db.CheckConstraint(
            f"health_dimension IS NULL OR health_dimension IN {INDICATOR_HEALTH_DIMENSIONS}",
            name="ck_indicator_entity_links_health_dimension",
        ),
        db.Index("ix_indicator_entity_links_company_target", "company_id", "target_type", "target_ref"),
        db.Index("ix_indicator_entity_links_company_indicator", "company_id", "indicator_id"),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    indicator_id = db.Column(db.Integer, nullable=False, index=True)
    target_type = db.Column(db.String(40), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=True, index=True)
    target_ref = db.Column(db.String(180), nullable=False, index=True)
    target_label = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(30), nullable=False, default="primary")
    health_dimension = db.Column(db.String(40), nullable=True)
    weight = db.Column(db.Numeric(7, 4), nullable=True)
    relationship_type = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "indicator_id": self.indicator_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_ref": self.target_ref,
            "target_label": self.target_label,
            "role": self.role,
            "health_dimension": self.health_dimension,
            "weight": float(self.weight) if self.weight is not None else None,
            "relationship_type": self.relationship_type,
            "notes": self.notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }


class IndicatorGoal(db.Model):
    """Goals/Targets for an indicator"""

    __tablename__ = "indicator_goals"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50)) # Novo campo para codificação AB.M.1
    name = db.Column(db.String(255), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    
    goal_value = db.Column(db.Numeric(15, 4), nullable=False)
    goal_date = db.Column(db.Date, nullable=True) # Agora Prazo Final é opcional na criação
    
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    
    responsible_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(50), default="active")
    goal_type = db.Column(db.String(50), default="monthly") # single, weekly, monthly, quarterly, annual, etc.
    goal_kind = db.Column(db.String(30), nullable=False, default="base") # base, campaign
    goal_scope = db.Column(db.String(30), nullable=False, default="team") # team, individual
    composition_mode = db.Column(db.String(30), nullable=False, default="independent") # independent, additive
    notes = db.Column(db.Text)
    
    # Faixas de desempenho (Default: <=80 Red, 81-90 Yellow, 91-110 Green, >111 Blue)
    performance_ranges = db.Column(db.JSON) 
    
    # Link com Rotina (Workflow de medição para este período)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id'), nullable=True)
    
    # Canal de alimentação (manual, api, webhook, mcp)
    collection_method = db.Column(db.String(50), default="manual")
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    records = db.relationship("IndicatorData", backref="goal", lazy="dynamic", cascade="all, delete-orphan")
    responsible = db.relationship("Employee", foreign_keys=[responsible_id])
    routine_links = db.relationship(
        "IndicatorGoalRoutine",
        back_populates="goal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def routine_ids(self):
        """IDs de todas as rotinas vinculadas, incluindo o legado 1:1."""
        ids = [link.routine_id for link in self.routine_links]
        if self.routine_id and self.routine_id not in ids:
            ids.insert(0, self.routine_id)
        return ids

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "indicator_id": self.indicator_id,
            "goal_value": float(self.goal_value),
            "start_date": self.period_start.isoformat() if self.period_start else None,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "goal_date": self.goal_date.isoformat() if self.goal_date else None,
            "status": self.status,
            "goal_type": self.goal_type,
            "goal_kind": self.goal_kind,
            "goal_scope": self.goal_scope,
            "composition_mode": self.composition_mode,
            "responsible_id": self.responsible_id,
            "performance_ranges": self.performance_ranges,
            "routine_id": self.routine_id,
            "routine_ids": self.routine_ids,
            "collection_method": self.collection_method,
            "notes": self.notes,
        }


class IndicatorGoalRoutine(db.Model):
    """Vínculo tenant-safe N:N entre uma meta e seus workflows de medição."""

    __tablename__ = "indicator_goal_routines"
    __table_args__ = (
        db.UniqueConstraint("company_id", "goal_id", "routine_id", name="uq_indicator_goal_routine"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("indicator_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    goal = db.relationship("IndicatorGoal", back_populates="routine_links")
    routine = db.relationship("Routine")


class IndicatorData(db.Model):
    """Actual measured values (facts) for an indicator"""

    __tablename__ = "indicator_data"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("indicator_goals.id"), nullable=True)
    
    # Vínculo com a execução (Opcional)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), nullable=True)
    # Vínculo com a instância de processo que originou este lançamento (Opcional)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), nullable=True)
    
    measured_value = db.Column(db.Numeric(15, 4), nullable=False)
    measured_date = db.Column(db.Date, nullable=False)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True) # Alias/Legacy
    
    source_ref = db.Column(db.String(255)) # Reference to external source ID
    evidence_payload = db.Column(db.JSON)
    notes = db.Column(db.Text)
    
    # Governance & Audit
    status = db.Column(db.String(30), default='draft') # draft, verified, manual_override
    is_manual = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    indicator = db.relationship("Indicator", backref="data_records")
    routine = db.relationship("Routine", backref="measurements")
    employee = db.relationship("Employee", foreign_keys=[employee_id])

    def to_dict(self):
        return {
            "id": self.id,
            "indicator_id": self.indicator_id,
            "routine_id": self.routine_id,
            "employee_id": self.employee_id,
            "measured_value": float(self.measured_value),
            "measured_date": self.measured_date.isoformat() if hasattr(self.measured_date, 'isoformat') else self.measured_date,
            "status": self.status,
            "is_manual": self.is_manual
        }
