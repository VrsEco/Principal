from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()
columns = db._get_existing_columns(cursor, 'plan_structure_installments')
print(columns)
conn.close()
