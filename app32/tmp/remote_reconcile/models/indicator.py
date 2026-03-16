from datetime import datetime
from . import db


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
    indicator_type = db.Column(db.String(50), nullable=False, default='individual') # individual, coletivo
    source_module = db.Column(db.String(50), nullable=False, default='manual') # manual, processo, projeto, api, webhook
    source_id = db.Column(db.Integer, nullable=True)
    collection_mode = db.Column(db.String(30), nullable=False, default='manual') 
    aggregation_function = db.Column(db.String(30), nullable=False, default='sum') # sum, avg, max, min, score_ratio
    
    # Metrics
    unit = db.Column(db.String(50), default='pts')  # e.g., "R$", "%", "Un"
    polarity = db.Column(db.String(20), default='positive')  # positive, negative
    formula = db.Column(db.Text)
    
    # Context links
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    
    # Metadata
    collaborators = db.Column(db.JSON)  # List of collaborator IDs
    data_source = db.Column(db.Text)
    notes = db.Column(db.Text)
    okr_reference = db.Column(db.String(255))
    okr_level = db.Column(db.String(50))
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    tree_node = db.relationship('IndicatorTree', backref='indicators', lazy=True)
    group = db.relationship('IndicatorGroup', backref='indicators', lazy=True)
    process = db.relationship('Process', backref='indicators', lazy=True)
    goals = db.relationship("IndicatorGoal", backref="indicator", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "tree_id": self.tree_id,
            "full_code": self.full_code,
            "code": self.code,
            "name": self.name,
            "unit": self.unit,
            "polarity": self.polarity,
            "indicator_type": self.indicator_type,
            "source_module": self.source_module,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
        }


class IndicatorGoal(db.Model):
    """Goals/Targets for an indicator"""

    __tablename__ = "indicator_goals"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    
    goal_value = db.Column(db.Numeric(15, 4), nullable=False)
    goal_date = db.Column(db.Date, nullable=False)
    
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    
    responsible_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(50), default="active")
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    records = db.relationship("IndicatorData", backref="goal", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "indicator_id": self.indicator_id,
            "goal_value": float(self.goal_value),
            "goal_date": self.goal_date.isoformat() if hasattr(self.goal_date, 'isoformat') else self.goal_date,
            "status": self.status,
        }

class IndicatorData(db.Model):
    """Actual measured values (facts) for an indicator"""

    __tablename__ = "indicator_data"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("indicator_goals.id"), nullable=True)
    
    measured_value = db.Column(db.Numeric(15, 4), nullable=False)
    measured_date = db.Column(db.Date, nullable=False)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True) # Alias/Legacy
    
    source_ref = db.Column(db.String(255)) # Reference to external source ID
    evidence_payload = db.Column(db.JSON)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "indicator_id": self.indicator_id,
            "measured_value": float(self.measured_value),
            "measured_date": self.measured_date.isoformat() if hasattr(self.measured_date, 'isoformat') else self.measured_date,
        }
