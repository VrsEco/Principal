
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

try:
    password = quote_plus("*Paraiso1978")
    url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
    engine = create_engine(url)

    tables = ['users', 'companies', 'projects', 'process_instances']

    print("--- Verification Results ---")
    with engine.connect() as conn:
        for t in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"Table '{t}': {result} rows")
            except Exception as e:
                print(f"Table '{t}': Error ({e})")
                
except Exception as e:
    print(f"Connection failed: {e}")
