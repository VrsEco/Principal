from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url, isolation_level="AUTOCOMMIT")


with engine.connect() as conn:
    print("Dropping schema public...")
    conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    print("Recreating schema public...")
    conn.execute(text("CREATE SCHEMA public"))
    # Permissions
    conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    print("Done. Database is clean.")
