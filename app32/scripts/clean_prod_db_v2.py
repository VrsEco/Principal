
import psycopg2
import sys

def clean_db():
    try:
        conn = psycopg2.connect('postgresql://postgres:*Paraiso1978@localhost:5432/postgres')
        conn.autocommit = True
        cur = conn.cursor()
        
        # Kill all connections to bdversusv2
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'bdversusv2' AND pid <> pg_backend_pid()
        """)
        
        # Now connect to bdversusv2
        conn2 = psycopg2.connect('postgresql://postgres:*Paraiso1978@localhost:5432/bdversusv2')
        conn2.autocommit = True
        cur2 = conn2.cursor()
        
        # Drop all tables, sequences, views, etc.
        cur2.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
                FOR r IN (SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE relkind = 'S' AND n.nspname = 'public') LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.relname) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        print("Database cleaned successfully.")
        
        cur2.close()
        conn2.close()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        # Try as regular user if postgres fails
        try:
             conn = psycopg2.connect('postgresql://app:*Paraiso1978@localhost:5432/bdversusv2')
             conn.autocommit = True
             cur = conn.cursor()
             cur.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
             print("Database cleaned as regular user.")
        except Exception as e2:
             print(f"Error as regular user: {e2}")
             sys.exit(1)

if __name__ == "__main__":
    clean_db()
