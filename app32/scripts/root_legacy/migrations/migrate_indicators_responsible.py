from app import create_app
from models import db, Indicator
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("--- Altering Table indicators ---")
    cols_to_add = [
        ("polarity", "VARCHAR(20) DEFAULT 'positive'"),
        ("formula", "TEXT"),
        ("responsible_id", "INTEGER REFERENCES employees(id)"),
        ("notes", "TEXT")
    ]
    
    for col_name, col_type in cols_to_add:
        try:
            db.session.execute(text(f"ALTER TABLE indicators ADD COLUMN {col_name} {col_type}"))
            db.session.commit()
            print(f"Coluna {col_name} adicionada com sucesso.")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao adicionar {col_name} (provavelmente já existe): {e}")

    print("--- Finalizing ---")
