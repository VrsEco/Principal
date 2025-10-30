"""
Product Model
Modelo de dados para produtos no Modelo & Mercado
"""

from datetime import datetime
from models import db


class Product(db.Model):
    """
    Modelo de Produto para análise de mercado e modelagem financeira
    
    Representa um produto/serviço comercializado pela empresa,
    incluindo preços, custos, despesas e metas de market share.
    """
    
    __tablename__ = 'plan_products'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id', ondelete='CASCADE'), nullable=False)
    
    # Identificação do Produto
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # a) Preço de Venda
    sale_price = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    sale_price_notes = db.Column(db.Text)
    
    # b) Custos Variáveis
    variable_costs_percent = db.Column(db.Numeric(5, 2), default=0.00)
    variable_costs_value = db.Column(db.Numeric(15, 2), default=0.00)
    variable_costs_notes = db.Column(db.Text)
    
    # c) Despesas Variáveis
    variable_expenses_percent = db.Column(db.Numeric(5, 2), default=0.00)
    variable_expenses_value = db.Column(db.Numeric(15, 2), default=0.00)
    variable_expenses_notes = db.Column(db.Text)
    
    # Margem de Contribuição Unitária (CALCULADO)
    unit_contribution_margin_percent = db.Column(db.Numeric(5, 2), default=0.00)
    unit_contribution_margin_value = db.Column(db.Numeric(15, 2), default=0.00)
    unit_contribution_margin_notes = db.Column(db.Text)
    
    # d) Tamanho do Mercado
    market_size_monthly_units = db.Column(db.Numeric(15, 2), default=0.00)
    market_size_monthly_revenue = db.Column(db.Numeric(15, 2), default=0.00)  # CALCULADO
    market_size_notes = db.Column(db.Text)
    
    # e) Alvo de Marketing Share
    market_share_goal_monthly_units = db.Column(db.Numeric(15, 2), default=0.00)
    market_share_goal_percent = db.Column(db.Numeric(5, 2), default=0.00)
    market_share_goal_notes = db.Column(db.Text)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relacionamentos
    def __repr__(self):
        return f'<Product {self.id}: {self.name}>'
    
    def calculate_contribution_margin(self):
        """
        Calcula a Margem de Contribuição Unitária
        
        Fórmula:
        MCU (valor) = Preço Venda - Custos Variáveis - Despesas Variáveis
        MCU (%) = (MCU valor / Preço Venda) * 100
        """
        if not self.sale_price or self.sale_price <= 0:
            self.unit_contribution_margin_value = 0.00
            self.unit_contribution_margin_percent = 0.00
            return
        
        # Calcular valores absolutos
        costs = float(self.variable_costs_value or 0)
        expenses = float(self.variable_expenses_value or 0)
        price = float(self.sale_price)
        
        # MCU = Preço - Custos - Despesas
        margin_value = price - costs - expenses
        
        # Percentual
        margin_percent = (margin_value / price) * 100 if price > 0 else 0
        
        self.unit_contribution_margin_value = round(margin_value, 2)
        self.unit_contribution_margin_percent = round(margin_percent, 2)
    
    def calculate_market_revenue(self):
        """
        Calcula o Faturamento Mensal do Mercado
        
        Fórmula:
        Faturamento Mensal = Tamanho Mercado (unidades) * Preço Venda
        """
        if not self.market_size_monthly_units or not self.sale_price:
            self.market_size_monthly_revenue = 0.00
            return
        
        units = float(self.market_size_monthly_units)
        price = float(self.sale_price)
        
        revenue = units * price
        self.market_size_monthly_revenue = round(revenue, 2)
    
    def to_dict(self):
        """Serializa o produto para dicionário"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'name': self.name,
            'description': self.description,
            
            # Preço de Venda
            'sale_price': float(self.sale_price) if self.sale_price else 0.00,
            'sale_price_notes': self.sale_price_notes,
            
            # Custos Variáveis
            'variable_costs_percent': float(self.variable_costs_percent) if self.variable_costs_percent else 0.00,
            'variable_costs_value': float(self.variable_costs_value) if self.variable_costs_value else 0.00,
            'variable_costs_notes': self.variable_costs_notes,
            
            # Despesas Variáveis
            'variable_expenses_percent': float(self.variable_expenses_percent) if self.variable_expenses_percent else 0.00,
            'variable_expenses_value': float(self.variable_expenses_value) if self.variable_expenses_value else 0.00,
            'variable_expenses_notes': self.variable_expenses_notes,
            
            # Margem de Contribuição
            'unit_contribution_margin_percent': float(self.unit_contribution_margin_percent) if self.unit_contribution_margin_percent else 0.00,
            'unit_contribution_margin_value': float(self.unit_contribution_margin_value) if self.unit_contribution_margin_value else 0.00,
            'unit_contribution_margin_notes': self.unit_contribution_margin_notes,
            
            # Tamanho do Mercado
            'market_size_monthly_units': float(self.market_size_monthly_units) if self.market_size_monthly_units else 0.00,
            'market_size_monthly_revenue': float(self.market_size_monthly_revenue) if self.market_size_monthly_revenue else 0.00,
            'market_size_notes': self.market_size_notes,
            
            # Market Share
            'market_share_goal_monthly_units': float(self.market_share_goal_monthly_units) if self.market_share_goal_monthly_units else 0.00,
            'market_share_goal_percent': float(self.market_share_goal_percent) if self.market_share_goal_percent else 0.00,
            'market_share_goal_notes': self.market_share_goal_notes,
            
            # Auditoria
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }
    
    @staticmethod
    def from_dict(data, product=None):
        """
        Cria ou atualiza um produto a partir de um dicionário
        
        Args:
            data (dict): Dados do produto
            product (Product, optional): Produto existente para atualizar
        
        Returns:
            Product: Instância do produto
        """
        if product is None:
            product = Product()
        
        # Campos básicos
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'plan_id' in data:
            product.plan_id = data['plan_id']
        
        # Preço de Venda
        if 'sale_price' in data:
            product.sale_price = float(data['sale_price']) if data['sale_price'] else 0.00
        if 'sale_price_notes' in data:
            product.sale_price_notes = data['sale_price_notes']
        
        # Custos Variáveis
        if 'variable_costs_percent' in data:
            product.variable_costs_percent = float(data['variable_costs_percent']) if data['variable_costs_percent'] else 0.00
        if 'variable_costs_value' in data:
            product.variable_costs_value = float(data['variable_costs_value']) if data['variable_costs_value'] else 0.00
        if 'variable_costs_notes' in data:
            product.variable_costs_notes = data['variable_costs_notes']
        
        # Despesas Variáveis
        if 'variable_expenses_percent' in data:
            product.variable_expenses_percent = float(data['variable_expenses_percent']) if data['variable_expenses_percent'] else 0.00
        if 'variable_expenses_value' in data:
            product.variable_expenses_value = float(data['variable_expenses_value']) if data['variable_expenses_value'] else 0.00
        if 'variable_expenses_notes' in data:
            product.variable_expenses_notes = data['variable_expenses_notes']
        
        # Margem de Contribuição (notas - valores são calculados)
        if 'unit_contribution_margin_notes' in data:
            product.unit_contribution_margin_notes = data['unit_contribution_margin_notes']
        
        # Tamanho do Mercado
        if 'market_size_monthly_units' in data:
            product.market_size_monthly_units = float(data['market_size_monthly_units']) if data['market_size_monthly_units'] else 0.00
        if 'market_size_notes' in data:
            product.market_size_notes = data['market_size_notes']
        
        # Market Share
        if 'market_share_goal_monthly_units' in data:
            product.market_share_goal_monthly_units = float(data['market_share_goal_monthly_units']) if data['market_share_goal_monthly_units'] else 0.00
        if 'market_share_goal_percent' in data:
            product.market_share_goal_percent = float(data['market_share_goal_percent']) if data['market_share_goal_percent'] else 0.00
        if 'market_share_goal_notes' in data:
            product.market_share_goal_notes = data['market_share_goal_notes']
        
        # Calcular campos automáticos
        product.calculate_contribution_margin()
        product.calculate_market_revenue()
        
        return product

