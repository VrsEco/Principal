import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import connect

def apply_schema():
    print("Aplicando schema v2 no banco conectado...")
    
    sql_path = PROJECT_ROOT / "scripts" / "create_ui_refs_v2.sql"
    if not sql_path.exists():
        print(f"Erro: Arquivo SQL não encontrado em {sql_path}")
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql_content)
        conn.commit()
        print("✅ Tabelas ui_pages_v2 e ui_elements_v2 criadas/verificadas com sucesso!")
        
        # Verificar se foram criadas
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('ui_pages_v2', 'ui_elements_v2')")
        count = cur.fetchone()[0]
        print(f"   Tabelas encontradas no schema: {count}/2")
        
    except Exception as e:
        print(f"❌ Erro ao aplicar schema: {e}")

if __name__ == "__main__":
    apply_schema()
