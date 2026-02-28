from datetime import datetime
from . import db


class IndicatorGroup(db.Model):
    """Group for organizing indicators"""

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
    indicators = db.relationship("Indicator", backref="group", lazy="dynamic")
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


class Indicator(db.Model):
    """Main indicator model (KPI)"""

    __tablename__ = "indicators"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("indicator_groups.id"), nullable=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    
    # Context links
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=True)
    
    # Relationships
    process = db.relationship('Process', backref='indicators', lazy=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    department_id = db.Column(db.Integer, nullable=True)
    okr_id = db.Column(db.Integer, nullable=True)
    
    # Detailed info
    collaborators = db.Column(db.JSON)  # List of collaborator IDs
    unit = db.Column(db.String(50))  # e.g., "R$", "%", "Un"
    formula = db.Column(db.Text)
    polarity = db.Column(db.String(20))  # positive, negative
    data_source = db.Column(db.Text)
    notes = db.Column(db.Text)
    okr_reference = db.Column(db.String(255))
    okr_level = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    goals = db.relationship("IndicatorGoal", backref="indicator", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "group_id": self.group_id,
            "code": self.code,
            "name": self.name,
            "unit": self.unit,
            "polarity": self.polarity,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
        }


class IndicatorGoal(db.Model):
    """Goals for an indicator"""

    __tablename__ = "indicator_goals"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id"), nullable=False)
    
    code = db.Column(db.String(50))
    goal_value = db.Column(db.Numeric(15, 2), nullable=False)
    goal_date = db.Column(db.Date, nullable=False)
    responsible_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(50), default="active")
    notes = db.Column(db.Text)
    
    goal_type = db.Column(db.String(50))  # single, monthly, quarterly
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    evaluation_basis = db.Column(db.String(50)) # value, percentage
    
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
    """Actual measured values for an indicator goal"""

    __tablename__ = "indicator_data"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("indicator_goals.id"), nullable=False)
    
    record_date = db.Column(db.Date, nullable=False)
    value = db.Column(db.Numeric(15, 2), nullable=False)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "record_date": self.record_date.isoformat() if hasattr(self.record_date, 'isoformat') else self.record_date,
            "value": float(self.value),
            "notes": self.notes,
        }
