import psycopg2
from urllib.parse import unquote, urlparse
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus")
print(f"Connecting to: {db_url}")

try:
    # Manual parsing because of potential quote issues
    # But let's try direct first
    conn = psycopg2.connect(db_url.replace("host.docker.internal", "localhost"))
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(f"✅ Direct Psycopg2 Success: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Direct Psycopg2 Failure: {e}")
