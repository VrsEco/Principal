import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import connect

print("Tentando conectar via helper...")
try:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Conexão OK!")
    
    # Check ui_pages
    try:
        cur.execute("SELECT count(*) FROM ui_pages")
        print(f"ui_pages count: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"ui_pages erro: {e}")
        conn.rollback()

    # Check ui_pages_v2
    try:
        cur.execute("SELECT count(*) FROM ui_pages_v2")
        print(f"ui_pages_v2 count: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"ui_pages_v2 erro: {e}")
        conn.rollback()

except Exception as e:
    print(f"Erro geral: {e}")
