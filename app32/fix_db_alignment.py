from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        columns_to_add = [
            ("company_id", "INTEGER"),
            ("vetor_type", "VARCHAR(20) DEFAULT 'bonus'"),
            ("impact_value", "NUMERIC(15, 4) DEFAULT 1.0"),
            ("use_indicator_goal", "BOOLEAN DEFAULT TRUE"),
            ("calculation_mode", "VARCHAR(30) DEFAULT 'ranges'"),
            ("ranges_config", "JSONB"),
            ("max_reduction", "NUMERIC(15, 4)"),
            ("incidencia", "VARCHAR(20) DEFAULT 'individual'"),
            ("order_index", "INTEGER DEFAULT 0")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE incentive_rules ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"✅ Coluna {col_name} adicionada.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️  Coluna {col_name} já existe.")
                else:
                    print(f"❌ Erro ao adicionar {col_name}: {e}")
        
    print("🚀 Sincronização concluída!")
