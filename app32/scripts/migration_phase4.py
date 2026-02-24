
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

STATUS_MAP_PROJ = {
    "em_aberto": "planned",
    "em_andamento": "in_progress",
    "concluido": "completed",
    "atrasado": "in_progress",
    "cancelado": "cancelled"
}

STATUS_MAP_TASK = {
    "em_aberto": "planned",
    "em_andamento": "in_progress",
    "concluido": "completed",
    "atrasado": "in_progress",
    "cancelado": "cancelled",
    "planned": "planned",
    "in_progress": "in_progress",
    "completed": "completed"
}

STAGE_MAP = {
    "inbox": "inbox",
    "waiting": "waiting",
    "executing": "executing",
    "pending": "pending",
    "suspended": "suspended",
    "completed": "completed",
    "concluido": "completed"
}

def migrate_projects():
    print("\n--- Fase: Projetos ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, company_id, title, status, priority, end_date, notes, owner FROM company_projects")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    mapping['projects'] = {}

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        old_company_id = str(data['company_id'])
        
        if old_company_id not in mapping['companies']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_status = STATUS_MAP_PROJ.get(data['status'], "planned")
        new_priority = data['priority'] if data['priority'] in ['low', 'medium', 'high'] else 'medium'

        cur32.execute("""
            INSERT INTO projects (company_id, title, status, priority, deadline, notes, owner, created_at, updated_at, progress)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (new_company_id, data['title'], new_status, new_priority, data['end_date'], data['notes'], data['owner'], datetime.now(), datetime.now(), 0))
        
        new_id = cur32.fetchone()[0]
        mapping['projects'][old_id] = new_id
        print(f"Projeto: {data['title']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_tasks():
    print("\n--- Fase: Tarefas de Projeto ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    # APP31 project_activities
    cur31.execute("SELECT id, project_id, title, description, status, stage, priority, deadline, estimated_hours, worked_hours, amount FROM project_activities")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_proj_id = str(data['project_id'])
        
        if old_proj_id not in mapping['projects']:
            continue
            
        new_proj_id = mapping['projects'][old_proj_id]
        new_status = STATUS_MAP_TASK.get(data['status'], "planned")
        new_stage = STAGE_MAP.get(data['stage'], "inbox")
        
        # Determine score weight based on priority
        sw = 1.0
        if data['priority'] == 'high': sw = 1.5
        elif data['priority'] == 'urgent': sw = 2.0

        cur32.execute("""
            INSERT INTO project_tasks (project_id, what, how, status, stage, priority, due_date, estimated_hours, worked_hours, amount, score_weight, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_proj_id, data['title'], data['description'], new_status, new_stage, data['priority'], data['deadline'], data['estimated_hours'], data['worked_hours'], str(data['amount']), sw, datetime.now(), datetime.now()))
        
        print(f"Tarefa: {data['title'][:30]}...")

    conn32.commit()
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_projects()
    migrate_tasks()
