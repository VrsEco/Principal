import os
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:%2AParaiso1978@localhost:5432/bd_app_versus')

from database.postgres_helper import get_engine

ENGINE = get_engine()

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS plan_products (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    sale_price NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    sale_price_notes TEXT,
    variable_costs_percent NUMERIC(5, 2) DEFAULT 0.00,
    variable_costs_value NUMERIC(15, 2) DEFAULT 0.00,
    variable_costs_notes TEXT,
    variable_expenses_percent NUMERIC(5, 2) DEFAULT 0.00,
    variable_expenses_value NUMERIC(15, 2) DEFAULT 0.00,
    variable_expenses_notes TEXT,
    unit_contribution_margin_percent NUMERIC(5, 2) DEFAULT 0.00,
    unit_contribution_margin_value NUMERIC(15, 2) DEFAULT 0.00,
    unit_contribution_margin_notes TEXT,
    market_size_monthly_units NUMERIC(15, 2) DEFAULT 0.00,
    market_size_monthly_revenue NUMERIC(15, 2) DEFAULT 0.00,
    market_size_notes TEXT,
    market_share_goal_monthly_units NUMERIC(15, 2) DEFAULT 0.00,
    market_share_goal_percent NUMERIC(5, 2) DEFAULT 0.00,
    market_share_goal_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
'''

BASE_PAYLOAD = {
    'plan_id': 6,
    'name': 'Projetos Planejados',
    'description': 'Projetos planejados vendidos por marceneiros para os clientes deles',
    'sale_price': Decimal('10000.00'),
    'sale_price_notes': '',
    'variable_costs_percent': Decimal('32.00'),
    'variable_costs_value': Decimal('3200.00'),
    'variable_costs_notes': '',
    'variable_expenses_percent': Decimal('0.00'),
    'variable_expenses_value': Decimal('0.00'),
    'variable_expenses_notes': '',
    'unit_contribution_margin_percent': Decimal('68.00'),
    'unit_contribution_margin_value': Decimal('6800.00'),
    'unit_contribution_margin_notes': '',
    'market_size_monthly_units': Decimal('600.00'),
    'market_size_monthly_revenue': Decimal('6000000.00'),
    'market_size_notes': '',
    'market_share_goal_monthly_units': Decimal('120.00'),
    'market_share_goal_percent': Decimal('30.00'),
    'market_share_goal_notes': 'Validar'
}

SELECT_SQL = text('''
SELECT id FROM plan_products
WHERE plan_id = :plan_id AND name = :name AND is_deleted = FALSE
ORDER BY id LIMIT 1
''')

INSERT_SQL = text('''
INSERT INTO plan_products (
    plan_id,
    name,
    description,
    sale_price,
    sale_price_notes,
    variable_costs_percent,
    variable_costs_value,
    variable_costs_notes,
    variable_expenses_percent,
    variable_expenses_value,
    variable_expenses_notes,
    unit_contribution_margin_percent,
    unit_contribution_margin_value,
    unit_contribution_margin_notes,
    market_size_monthly_units,
    market_size_monthly_revenue,
    market_size_notes,
    market_share_goal_monthly_units,
    market_share_goal_percent,
    market_share_goal_notes,
    created_at,
    updated_at,
    is_deleted
) VALUES (
    :plan_id,
    :name,
    :description,
    :sale_price,
    :sale_price_notes,
    :variable_costs_percent,
    :variable_costs_value,
    :variable_costs_notes,
    :variable_expenses_percent,
    :variable_expenses_value,
    :variable_expenses_notes,
    :unit_contribution_margin_percent,
    :unit_contribution_margin_value,
    :unit_contribution_margin_notes,
    :market_size_monthly_units,
    :market_size_monthly_revenue,
    :market_size_notes,
    :market_share_goal_monthly_units,
    :market_share_goal_percent,
    :market_share_goal_notes,
    :created_at,
    :updated_at,
    FALSE
);
''')

UPDATE_SQL = text('''
UPDATE plan_products SET
    description = :description,
    sale_price = :sale_price,
    sale_price_notes = :sale_price_notes,
    variable_costs_percent = :variable_costs_percent,
    variable_costs_value = :variable_costs_value,
    variable_costs_notes = :variable_costs_notes,
    variable_expenses_percent = :variable_expenses_percent,
    variable_expenses_value = :variable_expenses_value,
    variable_expenses_notes = :variable_expenses_notes,
    unit_contribution_margin_percent = :unit_contribution_margin_percent,
    unit_contribution_margin_value = :unit_contribution_margin_value,
    unit_contribution_margin_notes = :unit_contribution_margin_notes,
    market_size_monthly_units = :market_size_monthly_units,
    market_size_monthly_revenue = :market_size_monthly_revenue,
    market_size_notes = :market_size_notes,
    market_share_goal_monthly_units = :market_share_goal_monthly_units,
    market_share_goal_percent = :market_share_goal_percent,
    market_share_goal_notes = :market_share_goal_notes,
    updated_at = :updated_at,
    is_deleted = FALSE
WHERE id = :id;
''')

with ENGINE.begin() as conn:
    conn.execute(text(CREATE_TABLE_SQL))

    params = BASE_PAYLOAD.copy()
    now = datetime.utcnow()
    params['created_at'] = now
    params['updated_at'] = now

    existing = conn.execute(SELECT_SQL, {k: params[k] for k in ('plan_id', 'name')}).fetchone()

    if existing:
        update_params = params.copy()
        update_params['id'] = existing.id
        conn.execute(UPDATE_SQL, update_params)
        print(f"Updated existing product ID {existing.id}")
    else:
        conn.execute(INSERT_SQL, params)
        print("Inserted new product")
