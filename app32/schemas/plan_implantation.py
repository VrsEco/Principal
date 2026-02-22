from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class BaseSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

# --- ALIGNMENT ---
class AlignmentMember(BaseSchema):
    name: str = Field(..., min_length=2)
    role: Optional[str] = None
    motivation: Optional[str] = None
    commitment: Optional[str] = None
    risk: Optional[str] = None

class AlignmentAgendaItem(BaseSchema):
    what: str
    who: Optional[str] = None
    when: Optional[str] = None
    how: Optional[str] = None

class AlignmentSchema(BaseSchema):
    shared_vision: Optional[str] = None
    financial_goals: Optional[str] = None
    decision_criteria: List[str] = Field(default_factory=list)
    partners: List[AlignmentMember] = Field(default_factory=list)
    agenda: List[AlignmentAgendaItem] = Field(default_factory=list)

# --- MARKET & MODEL ---
class MarketPersona(BaseSchema):
    name: str
    age: Optional[str] = None
    profile: Optional[str] = None
    goals: List[str] = Field(default_factory=list) # Objetivos
    challenges: List[str] = Field(default_factory=list) # Desafios
    journey: List[str] = Field(default_factory=list) # Jornada

class ProductRampEntry(BaseSchema):
    month_period: str # YYYY.MM format
    percentage: float # 0.0 to 100.0

class MarketProduct(BaseSchema):
    name: str
    description: Optional[str] = None
    sale_price: float = 0.0
    sale_price_notes: Optional[str] = None
    
    # Costs & Expenses
    variable_costs_value: float = 0.0
    variable_costs_percent: float = 0.0
    variable_expenses_value: float = 0.0
    variable_expenses_percent: float = 0.0
    
    # Strategy
    market_size_monthly_units: float = 0.0
    market_share_goal_monthly_units: float = 0.0
    market_share_goal_percent: float = 0.0
    
    # Ramp-up
    ramp_up_entries: List[ProductRampEntry] = Field(default_factory=list)

class DifferentialCriterion(BaseSchema):
    criterion: str
    our_company: Optional[str] = None
    competitor_a: Optional[str] = None
    competitor_b: Optional[str] = None
    observation: Optional[str] = None

class MarketSegment(BaseSchema):
    name: str
    description: Optional[str] = None
    audiences: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    solution: Optional[str] = None
    differentials: List[str] = Field(default_factory=list)
    evidences: List[str] = Field(default_factory=list)
    revenue_sources: List[str] = Field(default_factory=list)
    cost_structure: List[str] = Field(default_factory=list)
    key_partners: List[str] = Field(default_factory=list)
    
    # Strategy & Positioning
    positioning: Optional[str] = None
    central_promise: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)
    
    # Differential Matrix
    differential_matrix: List[DifferentialCriterion] = Field(default_factory=list)
    
    personas: List[MarketPersona] = Field(default_factory=list)
    
    # Link to Products (Segment can have specific product goals)
    product_ids: List[str] = Field(default_factory=list)

class ModelMarketSchema(BaseSchema):
    segments: List[MarketSegment] = Field(default_factory=list)
    products: List[MarketProduct] = Field(default_factory=list)

# --- EXECUTION ---
class PaymentItem(BaseSchema):
    date: str
    amount: float

class ExecutionItem(BaseSchema):
    description: str
    item_type: Optional[str] = None # pessoas, imoveis, maquinas, ti, outros
    classification: str = "aquisição" # contratação, aquisição
    value: float = 0.0 # total value
    acquisition_date: Optional[str] = None
    availability_date: Optional[str] = None
    payments: List[PaymentItem] = Field(default_factory=list)
    operational_capacity_revenue: float = 0.0
    repetition: str = "unica" # unica, mensal
    supplier: Optional[str] = None
    notes: Optional[str] = None


class ExecutionArea(BaseSchema):
    items: List[ExecutionItem] = Field(default_factory=list)

class ExecutionSchema(BaseSchema):
    areas: Dict[str, ExecutionArea] = Field(default_factory=dict) # keys: comercial, operacional, admin

# --- FINANCE ---
class WorkingCapitalLine(BaseSchema):
    value: float = 0.0
    contribution_date: Optional[str] = None # Data do Aporte (YYYY.MM)
    availability_date: Optional[str] = None # Data da Disponibilização (YYYY.MM)
    description: Optional[str] = None

class FinanceWorkingCapital(BaseSchema):
    cash_reserve: float = 0.0
    receivables_days: int = 30
    inventory_days: int = 30
    payable_days: int = 30
    initial_setup: float = 0.0 # Valor inicial para capital de giro
    
    # Detailed items requested by user
    cash_items: List[WorkingCapitalLine] = Field(default_factory=list)
    receivables_items: List[WorkingCapitalLine] = Field(default_factory=list)
    inventory_items: List[WorkingCapitalLine] = Field(default_factory=list)

class FinanceInvestment(BaseSchema):
    description: str
    category: str # capex, capital_giro
    amount: float
    notes: Optional[str] = None

class FinanceProfitDistribution(BaseSchema):
    description: str
    percentage: float # 0 to 100
    type: str = "socio" # socio, outras
    start_date: Optional[str] = None

class FinanceAnalysisParams(BaseSchema):
    period_months: int = 60
    opportunity_cost_annual: float = 12.0
    start_date: Optional[str] = None

class FinanceSourceV2(BaseSchema):
    name: str
    amount: float
    type: str = "propria" # propria, financiamento, outras
    date: str = "" # YYYY.MM

class FinanceSchema(BaseSchema):
    # Parameters & Summary
    analysis_params: FinanceAnalysisParams = Field(default_factory=FinanceAnalysisParams)
    executive_summary: Optional[str] = None
    
    # Working Capital
    working_capital: FinanceWorkingCapital = Field(default_factory=FinanceWorkingCapital)
    
    # Investments (Old compatibility + new manual ones)
    investments: List[FinanceInvestment] = Field(default_factory=list) # Manual extra investments
    
    # Sources
    sources: Dict[str, float] = Field(default_factory=dict) # key-value for specific sources
    source_dates: Dict[str, str] = Field(default_factory=dict) # key: date (YYYY.MM)
    sources_v2: List[FinanceSourceV2] = Field(default_factory=list)
    
    # Profit Distribution
    profit_distribution: List[FinanceProfitDistribution] = Field(default_factory=list)
    
    # Calculations / State (to be updated by service)
    results_notes: Optional[str] = None
    notes: Optional[str] = None
