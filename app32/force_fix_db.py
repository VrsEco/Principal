from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Usando conexão direta com autocommit para evitar bloqueios de transação
    engine = db.engine.execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        commands = [
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS company_id INTEGER",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS vetor_type VARCHAR(20) DEFAULT 'bonus'",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS impact_value NUMERIC(15, 4) DEFAULT 1.0",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS use_indicator_goal BOOLEAN DEFAULT TRUE",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS calculation_mode VARCHAR(30) DEFAULT 'ranges'",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS ranges_config JSONB",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS max_reduction NUMERIC(15, 4)",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS incidencia VARCHAR(20) DEFAULT 'individual'",
            "ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0"
        ]
        
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                print(f"✅ Executado: {cmd}")
            except Exception as e:
                print(f"❌ Erro ao executar '{cmd}': {e}")

    print("🚀 Sincronização de Banco de Dados Finalizada!")
