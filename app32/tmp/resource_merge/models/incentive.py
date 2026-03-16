from datetime import datetime
from . import db


class IncentiveRuleSet(db.Model):
    """Versões de Planos de Incentivo compatíveis com o schema atual."""
    __tablename__ = 'incentive_rule_sets'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    periodicity = db.Column(db.String(20), nullable=False)
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    _max_red_total_cache = None

    @property
    def max_red_total(self):
        return self._max_red_total_cache

    @max_red_total.setter
    def max_red_total(self, value):
        self._max_red_total_cache = value

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'periodicity': self.periodicity,
            'is_active': self.is_active,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
        }


class IncentiveRule(db.Model):
    """Regra de incentivo compatível com o schema atual do banco."""
    __tablename__ = 'incentive_rules'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    weight = db.Column(db.Numeric(10, 4), default=1.0)
    target_value = db.Column(db.Numeric(15, 4))
    min_threshold = db.Column(db.Numeric(15, 4))
    max_cap = db.Column(db.Numeric(15, 4))
    impact_type = db.Column(db.String(20), default='multiplier')
    order_index = db.Column(db.Integer, default=0)
    vetor_type = db.Column(db.String(20), default='bonus')
    incidencia = db.Column(db.String(20), default='individual')

    indicator = db.relationship('Indicator', backref='incentive_rules')
    rule_set = db.relationship('IncentiveRuleSet', backref='rules')

    _ranges_config_cache = None
    _calculation_mode_cache = None
    _use_indicator_goal_cache = None

    @property
    def ranges_config(self):
        return self._ranges_config_cache

    @ranges_config.setter
    def ranges_config(self, value):
        self._ranges_config_cache = value

    @property
    def calculation_mode(self):
        return self._calculation_mode_cache

    @calculation_mode.setter
    def calculation_mode(self, value):
        self._calculation_mode_cache = value

    @property
    def use_indicator_goal(self):
        return True if self._use_indicator_goal_cache is None else bool(self._use_indicator_goal_cache)

    @use_indicator_goal.setter
    def use_indicator_goal(self, value):
        self._use_indicator_goal_cache = value

    @property
    def impact_value(self):
        return self.weight

    @impact_value.setter
    def impact_value(self, value):
        self.weight = value

    @property
    def max_reduction(self):
        return None

    @max_reduction.setter
    def max_reduction(self, value):
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'rule_set_id': self.rule_set_id,
            'indicator_id': self.indicator_id,
            'indicator_name': self.indicator.name if self.indicator else None,
            'vetor_type': self.vetor_type,
            'weight': float(self.weight) if self.weight is not None else 1.0,
            'impact_value': float(self.weight) if self.weight is not None else 1.0,
            'target_value': float(self.target_value) if self.target_value is not None else None,
            'min_threshold': float(self.min_threshold) if self.min_threshold is not None else None,
            'max_cap': float(self.max_cap) if self.max_cap is not None else None,
            'impact_type': self.impact_type,
            'incidencia': self.incidencia,
            'order_index': self.order_index,
            'ranges_config': self.ranges_config or [],
            'calculation_mode': self.calculation_mode or 'ranges',
            'use_indicator_goal': self.use_indicator_goal,
        }


class IncentiveGovernabilityMatrix(db.Model):
    __tablename__ = 'incentive_governability_matrix'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    governability_level = db.Column(db.String(20), default='direct')
    weight_override = db.Column(db.Numeric(10, 4))


class IncentiveCalculation(db.Model):
    __tablename__ = 'incentive_calculations'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='preview')
    total_distributed = db.Column(db.Numeric(15, 2))
    participants_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    _results_payload_cache = None

    @property
    def results_payload(self):
        return self._results_payload_cache

    @results_payload.setter
    def results_payload(self, value):
        self._results_payload_cache = value


class IncentiveParticipant(db.Model):
    __tablename__ = 'incentive_participants'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    valor_base = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    elegivel = db.Column(db.Boolean, default=True)
    data_entrada = db.Column(db.Date, nullable=True)
    notas = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    _max_red_total_cache = None

    @property
    def max_red_total(self):
        return self._max_red_total_cache

    @max_red_total.setter
    def max_red_total(self, value):
        self._max_red_total_cache = value

    employee = db.relationship('Employee', backref='incentive_participations')
    rule_set = db.relationship('IncentiveRuleSet', backref='participants')

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'valor_base': float(self.valor_base) if self.valor_base else 0.0,
            'elegivel': self.elegivel,
        }
