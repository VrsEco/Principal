from sqlalchemy import create_engine
import os
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
print(f"Connecting to {url}")
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        from sqlalchemy import text
        print(conn.scalar(text("SELECT version()")))
except Exception as e:
    print(f"Error: {e}")
