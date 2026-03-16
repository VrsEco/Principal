from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE incentive_rule_sets ADD COLUMN max_mult_total NUMERIC(15, 4)"))
            conn.commit()
            print("✅ Coluna max_mult_total adicionada em incentive_rule_sets.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ Coluna max_mult_total já existe.")
            else:
                print(f"❌ Erro: {e}")
