from datetime import datetime
from . import db

class IncentiveIndicator(db.Model):
    """
    Catalog of all measurable items for incentives (KPIs)
    """
    __tablename__ = 'incentive_indicators'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Types: eligibility, individual, collective, risk, exception
    indicator_type = db.Column(db.String(50), nullable=False)
    
    # Sources: process, project, okr, occurrence, manual
    source_module = db.Column(db.String(50), nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "indicator_type": self.indicator_type,
            "source_module": self.source_module,
            "is_active": self.is_active
        }

class IncentiveRuleSet(db.Model):
    """
    Versioned sets of rules for a company. 
    Guarantees that historical calculations remain immutable.
    """
    __tablename__ = 'incentive_rule_sets'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    
    # periodicity: weekly, monthly, quarterly, yearly
    periodicity = db.Column(db.String(20), nullable=False)
    
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date) # Optional end date for a specific seasonal program
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IncentiveRule(db.Model):
    """
    Actual mathematical rules within a versioned rule set.
    """
    __tablename__ = 'incentive_rules'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('incentive_indicators.id'), nullable=False)
    
    # Weight applied in the pipeline calculation (0.00 to 1.00)
    weight = db.Column(db.Numeric(10, 4), default=1.0)
    
    # Range of target values
    target_value = db.Column(db.Numeric(15, 4))
    min_threshold = db.Column(db.Numeric(15, 4))
    max_cap = db.Column(db.Numeric(15, 4))
    
    # impact_type: multiplier (0.0-1.2), deduction (fixed value), eligibility_block (binary)
    impact_type = db.Column(db.String(20), default='multiplier')
    
    # Sort order for the calculation pipeline
    order_index = db.Column(db.Integer, default=0)

class IncentiveGovernabilityMatrix(db.Model):
    """
    Maps Roles to Indicators with accountability levels (Governance).
    "Who is responsible for what signal?"
    """
    __tablename__ = 'incentive_governability_matrix'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('incentive_indicators.id'), nullable=False)
    
    # governability_level: direct (controlled), indirect (influenced), contextual (informed only)
    governability_level = db.Column(db.String(20), default='direct')
    weight_override = db.Column(db.Numeric(10, 4)) # Custom weight for this specific role if needed

class IncentiveFact(db.Model):
    """
    The Anti-Corruption Layer: Clean, normalized data points (Sinais).
    The calculation engine consumes FACTS, not raw module data.
    """
    __tablename__ = 'incentive_facts'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('incentive_indicators.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True) # None if it's a collective fact
    
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # The normalized numerical signal for the calculation
    value = db.Column(db.Numeric(15, 4), nullable=False)
    
    # Evidence backup: JSON of references (IDs, links to evidences)
    evidence_payload = db.Column(db.JSON)
    
    # status: draft (open), verified (audited), frozen (used in final calculation)
    status = db.Column(db.String(20), default='draft')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IncentiveCalculation(db.Model):
    """
    Execution header of a calculation (Pre-Snapshot).
    Calculated values per participant for a period.
    """
    __tablename__ = 'incentive_calculations'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # status: preview, approved, closed (results in snapshot)
    status = db.Column(db.String(20), default='preview')
    
    total_distributed = db.Column(db.Numeric(15, 2))
    participants_count = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
