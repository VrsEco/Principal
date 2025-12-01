from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url)

with engine.connect() as conn:
    print("Tables:")
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    for row in result:
        print(f"- {row[0]}")

    print("\nAlembic Version:")
    try:
        result = conn.execute(text("SELECT * FROM alembic_version"))
        for row in result:
            print(f"- {row[0]}")
    except Exception as e:
        print(f"Error reading alembic_version: {e}")
