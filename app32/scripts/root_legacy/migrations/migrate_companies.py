
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

def add_column_if_not_exists(cur, table, column, data_type):
    cur.execute(f"""
        SELECT count(*) 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}';
    """)
    if cur.fetchone()[0] == 0:
        print(f"Adding column {column} to {table}...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {data_type};")
    else:
        print(f"Column {column} already exists in {table}.")

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Missing columns based on model and error
    add_column_if_not_exists(cur, 'companies', 'cnpj', 'VARCHAR(18)')
    add_column_if_not_exists(cur, 'companies', 'city', 'VARCHAR(100)')
    add_column_if_not_exists(cur, 'companies', 'state', 'VARCHAR(2)')
    add_column_if_not_exists(cur, 'companies', 'coverage_physical', 'VARCHAR(50)')
    add_column_if_not_exists(cur, 'companies', 'coverage_online', 'VARCHAR(50)')
    add_column_if_not_exists(cur, 'companies', 'experience_total', 'VARCHAR(50)')
    add_column_if_not_exists(cur, 'companies', 'experience_segment', 'VARCHAR(50)')
    add_column_if_not_exists(cur, 'companies', 'logo_primary', 'VARCHAR(500)')
    add_column_if_not_exists(cur, 'companies', 'logo_secondary', 'VARCHAR(500)')
    add_column_if_not_exists(cur, 'companies', 'logo_icon', 'VARCHAR(500)')
    add_column_if_not_exists(cur, 'companies', 'created_at', 'TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP')
    add_column_if_not_exists(cur, 'companies', 'updated_at', 'TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP')
    add_column_if_not_exists(cur, 'companies', 'is_active', 'BOOLEAN DEFAULT TRUE')
    
    # Ensure they have data if needed
    cur.execute("UPDATE companies SET is_active = TRUE WHERE is_active IS NULL;")
    cur.execute("UPDATE companies SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;")
    cur.execute("UPDATE companies SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;")
    
    print("Migration completed successfully.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
