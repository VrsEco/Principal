from database.postgres_helper import connect
import json

def check_schema(table_name):
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)
    columns = [dict(zip(['name', 'type', 'default', 'null'], row)) for row in cursor.fetchall()]
    print(f"Schema for {table_name}:")
    print(json.dumps(columns, indent=2))
        
    conn.close()

if __name__ == "__main__":
    check_schema('routines')
    print("\n" + "="*50 + "\n")
    check_schema('process_routines')
