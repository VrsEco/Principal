from src.core.database import db
from app import create_app
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        print("Verificando/Adicionando coluna is_active na tabela companies...")
        # Adiciona a coluna se não existir
        conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
        # Garante que registros nulos sejam TRUE
        conn.execute(text("UPDATE companies SET is_active = TRUE WHERE is_active IS NULL"))
        conn.commit()
        print("Migração de companies concluída com sucesso.")
