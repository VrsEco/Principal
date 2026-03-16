import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app import create_app
from models import db

app = create_app()
with app.app_context():
    print("--- INICIANDO CORREÇÃO DE SCHEMA: indicator_data ---")
    try:
        # 1. Adicionar indicator_id
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS indicator_id INTEGER"))
        
        # 2. Popular indicator_id a partir de indicator_goals se goal_id existir
        db.session.execute(text("""
            UPDATE indicator_data 
            SET indicator_id = indicator_goals.indicator_id 
            FROM indicator_goals 
            WHERE indicator_data.goal_id = indicator_goals.id 
            AND indicator_data.indicator_id IS NULL
        """))
        
        # 3. Renomear record_date para measured_date
        db.session.execute(text("ALTER TABLE indicator_data RENAME COLUMN record_date TO measured_date"))
        
        # 4. Renomear value para measured_value e mudar tipo
        db.session.execute(text("ALTER TABLE indicator_data RENAME COLUMN value TO measured_value"))
        db.session.execute(text("ALTER TABLE indicator_data ALTER COLUMN measured_value TYPE NUMERIC(15, 4)"))
        
        # 5. Adicionar colunas faltantes
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS period_start DATE"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS period_end DATE"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS employee_id INTEGER REFERENCES employees(id)"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS collaborator_id INTEGER REFERENCES employees(id)"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS source_ref VARCHAR(255)"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS evidence_payload JSON"))
        
        # 6. Corrigir tipos de timestamp se necessário (estão como TEXT na inspeção anterior?)
        # A inspeção disse TEXT para created_at/updated_at em indicator_data
        db.session.execute(text("ALTER TABLE indicator_data ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at::timestamp"))
        db.session.execute(text("ALTER TABLE indicator_data ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at::timestamp"))
        
        db.session.commit()
        print("--- SCHEMA CORRIGIDO COM SUCESSO! ---")
    except Exception as e:
        db.session.rollback()
        print(f"Erro na migração: {e}")
