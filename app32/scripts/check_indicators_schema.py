from database.postgres_helper import connect
import json

def check_indicators_schema():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # List all columns for indicators
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'indicators'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        # Get a sample
        cursor.execute("SELECT * FROM indicators LIMIT 1")
        sample = cursor.fetchone()
        
        # Same for indicator_data, indicator_goals, indicator_groups
        tables = ['indicators', 'indicator_data', 'indicator_goals', 'indicator_groups']
        results = {}
        
        for table in tables:
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            cols = cursor.fetchall()
            
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")
            samp = cursor.fetchone()
            
            results[table] = {
                'columns': [dict(c) for c in cols],
                'sample': dict(samp) if samp else None
            }
            
        with open('indicator_schema_result.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        conn.close()
        print("Done! Result saved to indicator_schema_result.json")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_indicators_schema()
