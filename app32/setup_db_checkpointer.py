
import os
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

# URL do Banco de Produção (BDVERSUSV2)
DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"

def setup_langgraph_db():
    print("Conectando ao banco para configurar o checkpointer...")
    try:
        # Nota: PostgresSaver exige psycopg (v3)
        with psycopg.connect(DB_URL) as conn:
            print("Conectado com sucesso. Criando tabelas do LangGraph...")
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()
            print("✅ Tabelas do LangGraph (checkpoints, writes, etc) criadas com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao configurar banco: {e}")

if __name__ == "__main__":
    setup_langgraph_db()
