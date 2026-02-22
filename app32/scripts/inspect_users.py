from sqlalchemy import create_engine, text, inspect
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url)

inspector = inspect(engine)
columns = inspector.get_columns('users')
print("Users table columns:")
for col in columns:
    print(f"- {col['name']} ({col['type']})")

print("\nNotes table exists?", inspector.has_table("notes"))
