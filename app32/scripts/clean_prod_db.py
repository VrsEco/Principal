
import psycopg2
import sys

def clean_db():
    try:
        conn = psycopg2.connect('postgresql://app:*Paraiso1978@localhost:5432/bdversusv2')
        conn.autocommit = True
        cur = conn.cursor()
        
        # Get all tables in public schema
        cur.execute("""
            SELECT tablename FROM pg_tables WHERE schemaname = 'public'
        """)
        tables = [r[0] for r in cur.fetchall()]
        
        if tables:
            print(f"Dropping {len(tables)} tables...")
            # Use CASCADE to handle dependencies
            tables_str = ", ".join([f'"{t}"' for t in tables])
            cur.execute(f"DROP TABLE {tables_str} CASCADE")
            print("Tables dropped successfully.")
        else:
            print("No tables found to drop.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    clean_db()
