from app import create_app
from models import db

app = create_app()

with app.app_context():
    try:
        result = db.session.execute(db.text('SELECT 1')).scalar()
        print(f"✅ Banco de dados conectado! (result: {result})")
        
        # Verificar se tabela plans existe
        tables_query = db.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'plans'
        """)
        plans_exists = db.session.execute(tables_query).scalar()
        
        if plans_exists:
            print(f"✅ Tabela 'plans' já existe!")
        else:
            print(f"⚠️  Tabela 'plans' NÃO existe - migrations precisam ser executadas")
            
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
