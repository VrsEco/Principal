import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

try:
    from config import Config
    print('✅ Config importado')
    config = Config()
    print('✅ Config criado')
    from sqlalchemy import create_engine, text
    print('✅ SQLAlchemy importado')
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
    print('✅ Engine criado')
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print(f'✅ Conexão OK! PostgreSQL: {version[:30]}...')

        # Contar tabelas
        result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        table_count = result.fetchone()[0]
        print(f'📊 Tabelas: {table_count}')

except Exception as e:
    print(f'❌ Erro: {e}')
    import traceback
    traceback.print_exc()













