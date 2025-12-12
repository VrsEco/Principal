print("🚀 Testando SQLAlchemy...")
try:
    import sys
    sys.path.insert(0, '.')
    from config import Config
    print("✅ Config importado")
    config = Config()
    print("✅ Config criado")
    from sqlalchemy import create_engine, text
    print("✅ SQLAlchemy importado")
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
    print("✅ Engine criado")
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print(f"✅ Conexão OK: {result.fetchone()}")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()














