
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

def migrate_indicator_groups():
    print("\n--- Fase: Grupos de Indicadores ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    # APP31 indicator_groups
    cur31.execute("SELECT id, company_id, parent_id, code, name, description FROM indicator_groups")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    # Sorting to handle parents first (very simple recursive handling)
    # Since we might have deep trees, we process in levels or multiple passes
    remaining = [dict(zip(cols, r)) for r in rows]
    
    mapping['indicator_groups'] = {}
    
    passes = 0
    while remaining and passes < 5:
        to_process = []
        still_remaining = []
        for item in remaining:
            old_parent_id = str(item['parent_id']) if item['parent_id'] else None
            if not old_parent_id or old_parent_id in mapping['indicator_groups']:
                to_process.append(item)
            else:
                still_remaining.append(item)
        
        for item in to_process:
            old_id = str(item['id'])
            old_company_id = str(item['company_id'])
            if old_company_id not in mapping['companies']:
                continue
            
            new_company_id = mapping['companies'][old_company_id]
            new_parent_id = mapping['indicator_groups'].get(str(item['parent_id'])) if item['parent_id'] else None

            cur32.execute("""
                INSERT INTO indicator_groups (company_id, parent_id, code, name, description, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (new_company_id, new_parent_id, item['code'], item['name'], item['description'], datetime.now(), datetime.now()))
            
            new_id = cur32.fetchone()[0]
            mapping['indicator_groups'][old_id] = new_id
            print(f"Grupo: {item['name']} ({old_id} -> {new_id})")
        
        remaining = still_remaining
        passes += 1

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_indicators():
    print("\n--- Fase: Indicadores ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, group_id, company_id, code, name, unit, formula, polarity, data_source, notes, okr_reference, okr_level FROM indicators")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    mapping['indicators'] = {}

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        old_company_id = str(data['company_id'])
        
        if old_company_id not in mapping['companies']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_group_id = mapping['indicator_groups'].get(str(data['group_id']))
        
        # Obter client_code para desambiguar código do indicador
        cur32.execute("SELECT client_code FROM companies WHERE id = %s", (new_company_id,))
        client_code = cur32.fetchone()[0]
        new_code = f"{client_code}-{data['code']}"

        cur32.execute("""
            INSERT INTO indicators (company_id, group_id, code, name, unit, formula, polarity, data_source, notes, okr_reference, okr_level, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (new_company_id, new_group_id, new_code, data['name'], data['unit'], data['formula'], data['polarity'], data['data_source'], data['notes'], data['okr_reference'], data['okr_level'], datetime.now(), datetime.now()))
        
        new_id = cur32.fetchone()[0]
        mapping['indicators'][old_id] = new_id
        print(f"Indicador: {data['name']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_indicator_goals():
    print("\n--- Fase: Metas ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, indicator_id, company_id, code, goal_value, goal_date, responsible_id, status, notes, goal_type, period_start, period_end, evaluation_basis FROM indicator_goals")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    mapping['indicator_goals'] = {}

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        old_company_id = str(data['company_id'])
        old_indicator_id = str(data['indicator_id'])
        
        if old_company_id not in mapping['companies'] or old_indicator_id not in mapping['indicators']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_indicator_id = mapping['indicators'][old_indicator_id]
        new_responsible_id = mapping['employees'].get(str(data['responsible_id']))

        cur32.execute("""
            INSERT INTO indicator_goals (company_id, indicator_id, code, goal_value, goal_date, responsible_id, status, notes, goal_type, period_start, period_end, evaluation_basis, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (new_company_id, new_indicator_id, data['code'], data['goal_value'], data['goal_date'], new_responsible_id, data['status'], data['notes'], data['goal_type'], data['period_start'], data['period_end'], data['evaluation_basis'], datetime.now(), datetime.now()))
        
        new_id = cur32.fetchone()[0]
        mapping['indicator_goals'][old_id] = new_id
        print(f"Meta: {data['code']} para Indicador {old_indicator_id} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_indicator_data():
    print("\n--- Fase: Dados (Leituras) ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, company_id, goal_id, record_date, value, notes FROM indicator_data")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_goal_id = str(data['goal_id'])
        old_company_id = str(data['company_id'])
        
        if old_company_id not in mapping['companies'] or old_goal_id not in mapping['indicator_goals']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_goal_id = mapping['indicator_goals'][old_goal_id]

        cur32.execute("""
            INSERT INTO indicator_data (company_id, goal_id, record_date, value, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (new_company_id, new_goal_id, data['record_date'], data['value'], data['notes'], datetime.now(), datetime.now()))
        
        print(f"Dado: Registro {data['record_date']} para Meta {old_goal_id}")

    conn32.commit()
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_indicator_groups()
    migrate_indicators()
    migrate_indicator_goals()
    migrate_indicator_data()
