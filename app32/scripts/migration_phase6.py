
import psycopg2
from psycopg2 import sql
import json
from datetime import datetime

# Configurações
DB_APP31 = {
    "dbname": "bd_app31_temp",
    "user": "postgres",
    "password": "*Paraiso1978",
    "host": "localhost",
    "port": "5432"
}

DB_APP32 = {
    "dbname": "bdversusv2",
    "user": "postgres",
    "password": "*Paraiso1978",
    "host": "localhost",
    "port": "5432"
}

MAPPING_FILE = "migration_mapping.json"

def load_mapping():
    with open(MAPPING_FILE, 'r') as f:
        return json.load(f)

def save_mapping(mapping):
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f, indent=4)

def connect_db(config):
    return psycopg2.connect(**config)

def migrate_plans():
    print("\n--- Fase: Planos ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, company_id, name, description, plan_mode, status, year, created_at, updated_at FROM plans")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    mapping['plans'] = {}

    for row in rows:
        data = dict(zip(cols, row))
        old_company_id = str(data['company_id'])
        if old_company_id not in mapping['companies']: continue
        
        new_company_id = mapping['companies'][old_company_id]
        
        # Casting dates
        created_at = data['created_at']
        if isinstance(created_at, str):
            try: created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except: created_at = datetime.now()
        
        updated_at = data['updated_at'] if data['updated_at'] else created_at

        cur32.execute("""
            INSERT INTO plans (company_id, title, description, mode, status, progress, meta_data, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (new_company_id, data['name'], data['description'], data['plan_mode'] or 'growth', data['status'] or 'draft', 0, json.dumps({"year": data['year']}), created_at, updated_at))
        
        new_id = cur32.fetchone()[0]
        mapping['plans'][str(data['id'])] = new_id
        print(f"Plano: {data['name']} ({data['id']} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_plans()
