
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Aplicando Schema V2 no banco...")
    
    # 1. Indicadores
    try:
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN collection_mode VARCHAR(30) NOT NULL DEFAULT 'auto_interno'"))
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN aggregation_function VARCHAR(30) NOT NULL DEFAULT 'score_ratio'"))
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN unit VARCHAR(20) DEFAULT 'pts'"))
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN source_detail JSON"))
        print("Tabela incentive_indicators atualizada.")
    except Exception as e:
        print(f"Erro em indicators: {e}")
        db.session.rollback()

    # 2. Regras (Vetores)
    try:
        db.session.execute(text("ALTER TABLE incentive_rules ADD COLUMN vetor_type VARCHAR(20) NOT NULL DEFAULT 'bonus'"))
        db.session.execute(text("ALTER TABLE incentive_rules ADD COLUMN incidencia VARCHAR(20) DEFAULT 'individual'"))
        print("Tabela incentive_rules atualizada.")
    except Exception as e:
        print(f"Erro em rules: {e}")
        db.session.rollback()
        
    db.session.commit()
    print("Schema atualizado com sucesso!")
