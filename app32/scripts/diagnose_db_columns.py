
import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL não configurada.")
    exit(1)

engine = create_engine(db_url)
inspector = inspect(engine)

print(f"--- Colunas da tabela 'agent_actions' ---")
try:
    columns = inspector.get_columns('agent_actions')
    for column in columns:
        print(f"- {column['name']} ({column['type']})")
except Exception as e:
    print(f"Erro ao ler colunas: {e}")

# Tenta uma inserção de teste para ver onde quebra
print("\n--- Testando inserção na 'agent_actions' ---")
try:
    with engine.connect() as conn:
        # Tenta inserir um registro fake
        conn.execute(text("""
            INSERT INTO agent_actions (type, status, requesting_agent, handling_agent, title, description, company_id)
            VALUES ('test', 'pending', 'diagnose', 'diagnose', 'Test', 'Diagnose execution', 1)
        """))
        conn.commit()
        print("Sucesso: Inserção básica funciona.")
        
        # Agora testa as novas colunas
        try:
            conn.execute(text("""
                UPDATE agent_actions SET original_file = 'test.txt' WHERE type = 'test'
            """))
            conn.commit()
            print("Sucesso: Coluna 'original_file' existe.")
        except Exception as e:
            print(f"ERRO: Coluna 'original_file' provavelmente falta: {e}")
            
except Exception as e:
    print(f"Erro no teste de inserção: {e}")
