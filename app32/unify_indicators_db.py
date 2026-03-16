
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Atualizando Schema de Incentive Indicators para Unificacao...")
    
    try:
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN group_id INTEGER REFERENCES indicator_groups(id)"))
        db.session.execute(text("ALTER TABLE incentive_indicators ADD COLUMN polarity VARCHAR(20) DEFAULT 'positive'"))
        print("Tabela incentive_indicators atualizada com group_id e polarity.")
    except Exception as e:
        print(f"Erro ao atualizar schema: {e}")
        db.session.rollback()

    db.session.commit()
    print("Schema unificado com sucesso!")
