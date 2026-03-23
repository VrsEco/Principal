from app import create_app
from models import db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    
    # Check indicator_data
    if 'indicator_data' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('indicator_data')]
        if 'routine_id' not in columns:
            try:
                db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN routine_id INTEGER REFERENCES routines(id);"))
                db.session.commit()
                print("✅ Coluna routine_id adicionada com sucesso à tabela indicator_data.")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao adicionar coluna em indicator_data: {e}")
        else:
            print("ℹ️ Coluna routine_id já existe em indicator_data.")
