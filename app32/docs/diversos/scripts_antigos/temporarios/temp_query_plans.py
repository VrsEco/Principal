import os
from sqlalchemy import text

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:%2AParaiso1978@localhost:5432/bd_app_versus",
)
from database.postgres_helper import get_engine

engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, name FROM plans LIMIT 5")).fetchall()
for row in rows:
    print(dict(row._mapping))
