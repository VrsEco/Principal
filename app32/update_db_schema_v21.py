
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Aplicando Schema V2.1 no banco...")
    
    # 2. Regras (Vetores)
    try:
        db.session.execute(text("ALTER TABLE incentive_rules ADD COLUMN company_id INTEGER REFERENCES companies(id)"))
        print("Tabela incentive_rules atualizada (company_id).")
    except Exception as e:
        print(f"Erro em rules (company_id): {e}")
        db.session.rollback()
        
    db.session.commit()
    print("Schema atualizado!")
