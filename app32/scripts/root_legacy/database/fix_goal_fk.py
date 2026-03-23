from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Fixing indicator_goals foreign key...")
    try:
        # 1. Identificar e Dropar as constraints erradas que apontam para incentive_indicators
        # O erro indicou: indicator_goals_incentive_indicator_id_fkey ou indicator_goals_indicator_id_fkey
        # Vamos rodar comandos para garantir que removemos a errada.
        
        db.session.execute(text("ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS indicator_goals_indicator_id_fkey"))
        db.session.execute(text("ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS indicator_goals_incentive_indicator_id_fkey"))
        
        # 2. Criar a contraint correta apontando para indicators(id)
        db.session.execute(text("""
            ALTER TABLE indicator_goals 
            ADD CONSTRAINT indicator_goals_indicator_id_fkey 
            FOREIGN KEY (indicator_id) REFERENCES indicators(id)
        """))
        
        db.session.commit()
        print("Constraint fixed successfully: indicator_goals now points correctly to indicators(id).")
    except Exception as e:
        db.session.rollback()
        print(f"Error fixing constraint: {e}")
