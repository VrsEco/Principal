import os
import psycopg2
import psycopg2.extras

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

db_url = os.environ.get("DATABASE_URL", "")
if "host.docker.internal" in db_url:
    db_url = db_url.replace("host.docker.internal", "localhost")

if not db_url:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "bd_app_versus")
    user = os.environ.get("POSTGRES_USER", "postgres")
    pwd = os.environ.get("POSTGRES_PASSWORD", "*Paraiso1978")
    db_url = "postgresql://{}:{}@{}:{}/{}".format(user, pwd, host, port, dbname)

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Todas as tabelas no schema public
cur.execute(
    "SELECT table_name, table_type FROM information_schema.tables "
    "WHERE table_schema='public' ORDER BY table_name"
)
rows = cur.fetchall()

lines = ["=== TODAS AS TABELAS/VIEWS NO BANCO LOCAL ==="]
for r in rows:
    lines.append("{}: {}".format(r["table_name"], r["table_type"]))

result = "\n".join(lines)
print(result)

with open("all_tables_local.txt", "w", encoding="utf-8") as f:
    f.write(result)

cur.close()
conn.close()
print("\n>> Salvo em all_tables_local.txt")
