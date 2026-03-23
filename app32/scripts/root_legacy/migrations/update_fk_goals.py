
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Atualizando FK de indicator_goals para incentive_indicators...")
    
    try:
        # PostgreSQL syntax for dropping and adding foreign key
        db.session.execute(text("ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS indicator_goals_indicator_id_fkey"))
        db.session.execute(text("ALTER TABLE indicator_goals ADD CONSTRAINT indicator_goals_incentive_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES incentive_indicators(id)"))
        print("FK de indicator_goals atualizada.")
    except Exception as e:
        print(f"Erro ao atualizar FK: {e}")
        db.session.rollback()

    db.session.commit()
    print("Migracao de FK concluida!")
