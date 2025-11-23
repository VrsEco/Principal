import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import connect

os.environ["CLOUD_SQL_CONNECTION_NAME"] = "vrs-eco-478714:southamerica-east1:gestaoversus-db-prod"

print("Verificando dados migrados no Cloud...")
try:
    conn = connect()
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM ui_pages_v2")
    pages_count = cur.fetchone()[0]
    print(f"✅ ui_pages_v2: {pages_count} registros")
    
    cur.execute("SELECT count(*) FROM ui_elements_v2")
    elements_count = cur.fetchone()[0]
    print(f"✅ ui_elements_v2: {elements_count} registros")
    
    # Sample
    cur.execute("SELECT page_code, page_name FROM ui_pages_v2 ORDER BY id LIMIT 5")
    print("\nAmostra de páginas:")
    for row in cur.fetchall():
        print(f"  {row[0]} - {row[1]}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
