from datetime import datetime
from . import db

class IncentiveIndicator(db.Model):
    """
    Catálogo de KPIs mensuráveis para o sistema de incentivos.

    source_module  : processo | projeto | okr | ocorrencia | manual | api_externa | mcp_tool
    collection_mode: auto_interno | manual | api_externa | mcp_tool
    aggregation    : sum | avg | count | min | max | score_ratio (pontos obtidos/possíveis)
    """
    __tablename__ = 'incentive_indicators'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Tipo do indicador no plano
    # eligibility | individual | collective | risk | exception
    indicator_type = db.Column(db.String(50), nullable=False, default='individual')

    # Módulo fonte dos dados
    # processo | projeto | okr | ocorrencia | manual | api_externa | mcp_tool
    source_module = db.Column(db.String(50), nullable=False, default='manual')

    # ID específico da entidade fonte (opcional — None = todos da empresa)
    source_id = db.Column(db.Integer, nullable=True)

    # Modo de coleta → determina quem/o que alimenta o IncentiveFact
    # auto_interno | manual | api_externa | mcp_tool
    collection_mode = db.Column(db.String(30), nullable=False, default='auto_interno')

    # Função de agregação para consolidar múltiplos fatos num único valor do período
    # sum | avg | count | min | max | score_ratio
    aggregation_function = db.Column(db.String(30), nullable=False, default='score_ratio')

    # Unidade de exibição (%, pts, R$, un, h)
    unit = db.Column(db.String(20), default='pts')

    # Configurações adicionais livres (ex: webhook URL, filtros de status, etc.)
    source_detail = db.Column(db.JSON, nullable=True)

    # Categoria / Árvore (Plano de Contas)
    tree_id = db.Column(db.Integer, db.ForeignKey('incentive_indicator_tree.id'), nullable=True)
    
    # Categoria legado / Agrupamento (opcional, herdado do modelo Indicator geral)
    group_id = db.Column(db.Integer, db.ForeignKey('indicator_groups.id'), nullable=True)
    
    # Código completo (ex: AA.I.1.1)
    full_code = db.Column(db.String(100), index=True, unique=True)

    # Polaridade: positive (quanto maior melhor) | negative (quanto menor melhor)
    polarity = db.Column(db.String(20), default='positive')

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tree_node = db.relationship('IncentiveIndicatorTree', backref='indicators', lazy=True)
    group = db.relationship('IndicatorGroup', backref='incentive_indicators', lazy=True)
    goals = db.relationship("IndicatorGoal", backref="incentive_indicator", lazy="dynamic", viewonly=True)
    targets = db.relationship("IncentiveTarget", backref="indicator", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "tree_id": self.tree_id,
            "code": self.code,
            "full_code": self.full_code,
            "name": self.name,
            "description": self.description,
            "indicator_type": self.indicator_type,
            "source_module": self.source_module,
            "source_id": self.source_id,
            "collection_mode": self.collection_mode,
            "aggregation_function": self.aggregation_function,
            "unit": self.unit,
            "source_detail": self.source_detail,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class IncentiveIndicatorTree(db.Model):
    """
    Árvore de Indicadores (Plano de Contas).
    Permite organizar indicadores em níveis hierárquicos.
    """
    __tablename__ = 'incentive_indicator_tree'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('incentive_indicator_tree.id'), nullable=True)
    
    code = db.Column(db.String(50), nullable=False) # Ex: "1", "1.1"
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    children = db.relationship("IncentiveIndicatorTree", backref=db.backref("parent", remote_side=[id]))

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "description": self.description
        }

class IncentiveTarget(db.Model):
    """
    Meta do Indicador para um determinado período.
    """
    __tablename__ = 'incentive_targets'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('incentive_indicators.id'), nullable=False)
    
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    target_value = db.Column(db.Numeric(15, 4), nullable=False)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "indicator_id": self.indicator_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "target_value": float(self.target_value)
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
    valid_to = db.Column(db.Date)  # Optional end date for a specific seasonal program
    
    # Redutor Máximo Global do Plano (ex: 0.50 significa que redutores não podem bater mais que 50% do bônus)
    max_red_total = db.Column(db.Numeric(15, 4))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "periodicity": self.periodicity,
            "max_red_total": float(self.max_red_total) if self.max_red_total else None,
            "is_active": self.is_active
        }

class IncentiveRule(db.Model):
    """
    Vetor de Premiação — define como um Indicador impacta o bônus de um colaborador.

    vetor_type:
      - desconto_base → abate valor fixo ou % direto do valor base antes dos multiplicadores
      - multiplicador  → soma ao cálculo de bônus (ex: atingiu meta financeira)
      - redutor       → desconta proporcionalmente do montante conquistado (ex: falhas)
      - bloqueador    → trava o pagamento total se o piso não for atingido

    incidencia:
      - individual → calculado por colaborador separadamente
      - coletivo   → valor único aplicado a todos no plano

    formula de cálculo (Nova):
      bonus_final = (valor_base - sum(descontos_base)) * (sum(multiplicadores) - sum(redutores))
      
      * Redutores são limitados individualmente por max_reduction e globalmente por max_red_total.
      * Multiplicadores podem somar valores superiores a 1.0 (100%).
    """
    __tablename__ = 'incentive_rules'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('incentive_indicators.id'), nullable=False)

    # Tipo de Vetor de Premiação
    # bonus | redutor | bloqueador
    vetor_type = db.Column(db.String(20), nullable=False, default='bonus')

    # Valor do impacto no cálculo (substitui conceito de peso relativo)
    impact_value = db.Column(db.Numeric(15, 4), default=1.0)
    
    # Peso legado (manter para compatibilidade se necessário, mas usar impact_value na lógica nova)
    weight = db.Column(db.Numeric(10, 4), default=1.0)

    # Meta esperada do indicador neste vetor
    target_value = db.Column(db.Numeric(15, 4))

    # Piso mínimo para ativação (abaixo = bloqueador ativa / bonus = 0)
    min_threshold = db.Column(db.Numeric(15, 4))

    # Teto máximo de impacto (cap de ganho)
    max_cap = db.Column(db.Numeric(15, 4))

    # Redutor máximo para este indicador específico
    max_reduction = db.Column(db.Numeric(15, 4))

    # Legacy / compatibilidade
    impact_type = db.Column(db.String(20), default='multiplier')

    # Incidência: individual (por colaborador) | coletivo (todos no plano igual)
    incidencia = db.Column(db.String(20), default='individual')

    # Ordem de processamento no pipeline de cálculo
    order_index = db.Column(db.Integer, default=0)

    # Relationships
    indicator = db.relationship('IncentiveIndicator', backref='rules')
    rule_set = db.relationship('IncentiveRuleSet', backref='rules')

    def to_dict(self):
        return {
            "id": self.id,
            "rule_set_id": self.rule_set_id,
            "indicator_id": self.indicator_id,
            "indicator_name": self.indicator.name if self.indicator else None,
            "indicator_code": self.indicator.code if self.indicator else None,
            "vetor_type": self.vetor_type,
            "weight": float(self.weight) if self.weight else 1.0,
            "impact_value": float(self.impact_value) if self.impact_value else 1.0,
            "target_value": float(self.target_value) if self.target_value else None,
            "min_threshold": float(self.min_threshold) if self.min_threshold else None,
            "max_cap": float(self.max_cap) if self.max_cap else None,
            "max_reduction": float(self.max_reduction) if self.max_reduction else None,
            "incidencia": self.incidencia,
            "order_index": self.order_index,
        }

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
    
    # Store JSON results for quick retrieval
    results_payload = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IncentiveParticipant(db.Model):
    """
    Vínculo entre um Colaborador e um Plano de Incentivo.
    Define o valor base individual e a elegibilidade desse colaborador.
    """
    __tablename__ = 'incentive_participants'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    rule_set_id = db.Column(db.Integer, db.ForeignKey('incentive_rule_sets.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)

    # Valor base de referência para cálculo do bônus (pode ser salário, valor-alvo, etc.)
    valor_base = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # Elegível para receber bônus neste plano
    elegivel = db.Column(db.Boolean, default=True)

    # Data de entrada neste plano (pode ser diferente da contratação)
    data_entrada = db.Column(db.Date, nullable=True)

    # Observações do gestor sobre este participante no plano
    notas = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', backref='incentive_participations')
    rule_set = db.relationship('IncentiveRuleSet', backref='participants')

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "rule_set_id": self.rule_set_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "valor_base": float(self.valor_base) if self.valor_base else 0.0,
            "elegivel": self.elegivel,
            "data_entrada": self.data_entrada.isoformat() if self.data_entrada else None,
            "notas": self.notas,
        }
