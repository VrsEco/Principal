from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url)

tables_to_check = ['users', 'companies', 'employees', 'plans', 'projects']

with engine.connect() as conn:
    for table in tables_to_check:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"{table}: {count} registros")
        except Exception as e:
            print(f"{table}: ERRO - {e}")
