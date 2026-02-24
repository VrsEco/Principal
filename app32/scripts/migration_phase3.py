
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

def migrate_process_hierarchy():
    print("\n--- Fase: Hierarquia de Processos ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    # Areas
    cur31.execute("SELECT id, company_id, code, name, description, order_index, color FROM process_areas")
    areas = [dict(zip([d[0] for d in cur31.description], r)) for r in cur31.fetchall()]
    mapping['process_areas'] = {}
    for a in areas:
        old_company_id = str(a['company_id'])
        if old_company_id not in mapping['companies']: continue
        cur32.execute("INSERT INTO process_areas (company_id, code, name, description, order_index, color, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                      (mapping['companies'][old_company_id], a['code'], a['name'], a['description'], a['order_index'], a['color'], datetime.now(), datetime.now()))
        mapping['process_areas'][str(a['id'])] = cur32.fetchone()[0]

    # Macros
    cur31.execute("SELECT id, company_id, area_id, code, name, owner, description, order_index FROM macro_processes")
    macros = [dict(zip([d[0] for d in cur31.description], r)) for r in cur31.fetchall()]
    mapping['macro_processes'] = {}
    for m in macros:
        old_company_id = str(m['company_id'])
        old_area_id = str(m['area_id'])
        if old_company_id not in mapping['companies'] or old_area_id not in mapping['process_areas']: continue
        cur32.execute("INSERT INTO macro_processes (company_id, area_id, code, name, owner, description, order_index, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                      (mapping['companies'][old_company_id], mapping['process_areas'][old_area_id], m['code'], m['name'], m['owner'], m['description'], m['order_index'], datetime.now(), datetime.now()))
        mapping['macro_processes'][str(m['id'])] = cur32.fetchone()[0]

    # Processes
    cur31.execute("SELECT id, company_id, macro_id, code, name, description, responsible, structuring_level, performance_level, order_index, flow_document FROM processes")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    mapping['processes'] = {}
    for p in rows:
        data = dict(zip(cols, p))
        old_company_id = str(data['company_id'])
        old_macro_id = str(data['macro_id'])
        if old_company_id not in mapping['companies'] or old_macro_id not in mapping['macro_processes']: continue
        
        cur32.execute("INSERT INTO processes (company_id, macro_id, code, name, description, responsible, structuring_level, performance_level, order_index, flow_document, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                      (mapping['companies'][old_company_id], mapping['macro_processes'][old_macro_id], data['code'], data['name'], data['description'], data['responsible'], data['structuring_level'], data['performance_level'], data['order_index'], data['flow_document'], True, datetime.now()))
        mapping['processes'][str(data['id'])] = cur32.fetchone()[0]

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()
    print("Hierarquia de processos migrada.")

def migrate_process_instances():
    print("\n--- Fase: Instâncias de Processos ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, company_id, process_id, instance_code, title, description, status, priority, due_date, started_at, completed_at, worked_hours, estimated_hours, actual_hours, notes, created_by, trigger_type FROM process_instances")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_company_id = str(data['company_id'])
        old_process_id = str(data['process_id'])
        
        if old_company_id not in mapping['companies'] or old_process_id not in mapping['processes']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_process_id = mapping['processes'][old_process_id]

        cur32.execute("""
            INSERT INTO process_instances (company_id, process_id, instance_code, title, description, status, priority, due_date, started_at, completed_at, worked_hours, estimated_hours, actual_hours, notes, created_by, trigger_type, created_at, updated_at, score_weight)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_company_id, new_process_id, data['instance_code'], data['title'], data['description'], data['status'], data['priority'], data['due_date'], data['started_at'], data['completed_at'], data['worked_hours'], data['estimated_hours'], data['actual_hours'], data['notes'], data['created_by'], data['trigger_type'], datetime.now(), datetime.now(), 1.0))
        
        print(f"Instância: {data['title']} ({data['instance_code']})")

    conn32.commit()
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_process_hierarchy()
    migrate_process_instances()
