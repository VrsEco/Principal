
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

def connect_db(config):
    return psycopg2.connect(**config)

def migrate_occurrences():
    print("\n--- Fase: Ocorrências ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT company_id, employee_id, process_id, project_id, score, title, description, type, created_at FROM occurrences")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_company_id = str(data['company_id'])
        if old_company_id not in mapping['companies']: continue
        
        new_company_id = mapping['companies'][old_company_id]
        new_emp_id = mapping['employees'].get(str(data['employee_id']))
        new_proc_id = mapping['processes'].get(str(data['process_id']))
        new_proj_id = mapping['projects'].get(str(data['project_id']))

        # Created_at conversion
        dt = data['created_at']
        if isinstance(dt, str):
            try: dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except: dt = datetime.now()

        cur32.execute("""
            INSERT INTO occurrences (company_id, employee_id, process_id, project_id, score, title, description, type, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_company_id, new_emp_id, new_proc_id, new_proj_id, data['score'], data['title'], data['description'], data['type'], dt, dt))
        print(f"Ocorrência: {data['title'][:30]}")

    conn32.commit()
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_meetings():
    print("\n--- Fase: Reuniões ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT company_id, project_id, title, status, scheduled_date, actual_date, scheduled_time, actual_time, meeting_notes, participants_json, agenda_json, discussions_json, activities_json FROM meetings")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_company_id = str(data['company_id'])
        if old_company_id not in mapping['companies']: continue
        
        new_company_id = mapping['companies'][old_company_id]
        new_proj_id = mapping['projects'].get(str(data['project_id']))

        cur32.execute("""
            INSERT INTO meetings (company_id, project_id, title, status, scheduled_date, actual_date, scheduled_time, actual_time, meeting_notes, participants_json, agenda_json, discussions_json, activities_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_company_id, new_proj_id, data['title'], data['status'], data['scheduled_date'], data['actual_date'], data['scheduled_time'], data['actual_time'], data['meeting_notes'], data['participants_json'], data['agenda_json'], data['discussions_json'], data['activities_json'], datetime.now(), datetime.now()))
        print(f"Reunião: {data['title'][:30]}")

    conn32.commit()
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_occurrences()
    migrate_meetings()
