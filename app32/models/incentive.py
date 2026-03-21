from datetime import datetime
from . import db

class IncentiveRuleSet(db.Model):
    """
    Versões de Planos de Incentivo. 
    Define o conjunto de regras e indicadores que compõem a remuneração variável de um período.
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
    valid_to = db.Column(db.Date)
    
    # Redutores/Multiplicadores Máximos Globais
    max_red_total = db.Column(db.Numeric(15, 4))
    max_mult_total = db.Column(db.Numeric(15, 4))
    deleted_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "periodicity": self.periodicity,
            "max_red_total": float(self.max_red_total) if self.max_red_total else None,
            "max_mult_total": float(self.max_mult_total) if self.max_mult_total else None,
            "is_active": self.is_active
        }

class IncentiveRule(db.Model):
    """
    Regra de Premiação (Vetor) - Como um Indicador impacta o bônus neste RuleSet.
    As regras 'buscam' os indicadores independentes.
    """
    __tablename__ = 'incentive_rules'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    
    # Link para o indicador independente
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)

    vetor_type = db.Column(db.String(20), nullable=False, default='bonus') # bonus, multiplicador, redutor, bloqueador
    impact_value = db.Column(db.Numeric(15, 4), default=1.0)
    weight = db.Column(db.Numeric(10, 4), default=1.0)
    
    # Parâmetros de enquadramento (podem variar por plano para o mesmo indicador)
    use_indicator_goal = db.Column(db.Boolean, default=True) # Busca Meta/Ranges do IndicatorGoal
    calculation_mode = db.Column(db.String(30), default='ranges') # linear, ranges, step
    
    # Configuração de valores por faixa: [{color: 'red', value: 0.5}, {color: 'yellow', value: 0.8}, ...]
    ranges_config = db.Column(db.JSON)
    
    target_value = db.Column(db.Numeric(15, 4))
    min_threshold = db.Column(db.Numeric(15, 4))
    max_cap = db.Column(db.Numeric(15, 4))
    max_reduction = db.Column(db.Numeric(15, 4))
    
    impact_type = db.Column(db.String(20), default='multiplier')
    incidencia = db.Column(db.String(20), default='individual') # individual, coletiva_equipe, coletiva_empresa
    order_index = db.Column(db.Integer, default=0)
    deleted_at = db.Column(db.DateTime)

    # Relationships
    indicator = db.relationship('Indicator', backref='incentive_rules')
    rule_set = db.relationship('IncentiveRuleSet', backref='rules')

    def to_dict(self):
        return {
            "id": self.id,
            "rule_set_id": self.rule_set_id,
            "indicator_id": self.indicator_id,
            "indicator_name": self.indicator.name if self.indicator else None,
            "vetor_type": self.vetor_type,
            "weight": float(self.weight) if self.weight else 1.0,
            "impact_value": float(self.impact_value) if self.impact_value else 1.0,
            "use_indicator_goal": self.use_indicator_goal,
            "calculation_mode": self.calculation_mode,
            "ranges_config": self.ranges_config,
            "target": float(self.target_value) if self.target_value else None,
            "min_threshold": float(self.min_threshold) if self.min_threshold else None,
            "max_cap": float(self.max_cap) if self.max_cap else None,
            "max_reduction": float(self.max_reduction) if self.max_reduction else None,
            "incidencia": self.incidencia
        }

class IncentiveGovernabilityMatrix(db.Model):
    """Matriz de Governabilidade: quanto um cargo influencia um indicador."""
    __tablename__ = 'incentive_governability_matrix'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    governability_level = db.Column(db.String(20), default='direct')
    weight_override = db.Column(db.Numeric(10, 4))

class IncentiveCalculation(db.Model):
    """Resultados de um processamento de incentivos."""
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
    results_payload = db.Column(db.JSON)
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class IncentiveParticipant(db.Model):
    """Colaboradores que participam de um RuleSet específico."""
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
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', backref='incentive_participations')
    rule_set = db.relationship('IncentiveRuleSet', backref='participants')

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "valor_base": float(self.valor_base) if self.valor_base else 0.0,
            "elegivel": self.elegivel
        }
