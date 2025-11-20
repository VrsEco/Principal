"""Migration simples para ModeFin"""
from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

print("Criando tabela plan_finance_capital_giro...")

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    contribution_date DATE NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
)
"""
)

conn.commit()
print("✅ Tabela criada!")

cursor.execute(
    """
CREATE INDEX IF NOT EXISTS idx_capital_giro_plan_id 
ON plan_finance_capital_giro(plan_id)
"""
)

conn.commit()
print("✅ Índice criado!")

cursor.execute(
    """
ALTER TABLE plan_finance_metrics 
ADD COLUMN IF NOT EXISTS executive_summary TEXT
"""
)

conn.commit()
print("✅ Coluna executive_summary adicionada!")

conn.close()

print("\n" + "=" * 50)
print("✅ MIGRATION COMPLETA!")
print("=" * 50)
