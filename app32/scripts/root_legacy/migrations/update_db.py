from app import create_app
from models import db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tabelas encontradas: {tables}")
    
    if 'indicator_goals' in tables:
        columns = [c['name'] for c in inspector.get_columns('indicator_goals')]
        print(f"Colunas de indicator_goals: {columns}")
        if 'routine_id' not in columns:
            try:
                db.session.execute(text("ALTER TABLE indicator_goals ADD COLUMN routine_id INTEGER REFERENCES routines(id);"))
                db.session.commit()
                print("✅ Coluna routine_id adicionada com sucesso à tabela indicator_goals.")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao adicionar coluna em indicator_goals: {e}")
        else:
            print("ℹ️ Coluna routine_id já existe em indicator_goals.")

    if 'indicators' in tables:
        columns = [c['name'] for c in inspector.get_columns('indicators')]
        print(f"Colunas de indicators: {columns}")
        # O usuário disse: "Fizemos errado, na verdade temos que indicar a rotina na meta."
        # Mas manter a coluna no indicador pode não quebrar nada, a menos que cause confusão.
        # Por enquanto vamos focar na meta.
