
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

# Empresas para migrar (Client Codes)
ALLOWED_COMPANIES = ['AS', 'AU', 'AB', 'AW', 'AL', 'AI', 'AV', 'AA', 'AN']

# Mapeamento Global para persistência entre fases
MAPPING_FILE = "migration_mapping.json"

def load_mapping():
    try:
        with open(MAPPING_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "companies": {},
            "users": {},
            "roles": {},
            "employees": {},
            "indicators": {},
            "processes": {},
            "projects": {}
        }

def save_mapping(mapping):
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f, indent=4)

def connect_db(config):
    return psycopg2.connect(**config)

def clean_value(val):
    if isinstance(val, str) and val.strip() == "":
        return None
    return val

def migrate_companies():
    print("\n--- Fase: Empresas ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, name, legal_name, cnpj, industry, size, city, state, client_code, created_at FROM companies")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        if data['client_code'] not in ALLOWED_COMPANIES:
            continue
        
        # Check if already migrated
        old_id = str(data['id'])
        if old_id in mapping['companies']:
            print(f"Empresa {data['name']} já migrada.")
            continue

        # Prepare for APP32
        created_at = data['created_at']
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()

        cur32.execute("""
            INSERT INTO companies (name, legal_name, cnpj, industry, size, city, state, client_code, created_at, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (data['name'], data['legal_name'], data['cnpj'], data['industry'], data['size'], data['city'], data['state'], data['client_code'], created_at, created_at, True))
        
        new_id = cur32.fetchone()[0]
        mapping['companies'][old_id] = new_id
        print(f"Migrada: {data['name']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_users():
    print("\n--- Fase: Usuários ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, name, email, password_hash, role FROM users")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        
        # Check if email exists in APP32
        cur32.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
        exist = cur32.fetchone()
        if exist:
            mapping['users'][old_id] = exist[0]
            print(f"Usuário {data['email']} já existe. Mapeado.")
            continue

        now = datetime.now()
        cur32.execute("""
            INSERT INTO users (name, email, password_hash, role, created_at, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (data['name'], data['email'], data['password_hash'], data['role'], now, now, True))
        
        new_id = cur32.fetchone()[0]
        mapping['users'][old_id] = new_id
        print(f"Migrado: {data['email']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_roles():
    print("\n--- Fase: Cargos (Roles) ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, title, department, reports_to, weekly_hours, color, company_id FROM roles")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        old_company_id = str(data['company_id'])

        if old_company_id not in mapping['companies']:
            continue
        
        new_company_id = mapping['companies'][old_company_id]

        cur32.execute("""
            INSERT INTO roles (title, department, reports_to, weekly_hours, color, company_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (data['title'], data['department'], data['reports_to'], data['weekly_hours'], data['color'], new_company_id, datetime.now(), datetime.now()))
        
        new_id = cur32.fetchone()[0]
        mapping['roles'][old_id] = new_id
        print(f"Role: {data['title']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

def migrate_employees():
    print("\n--- Fase: Colaboradores (Employees) ---")
    mapping = load_mapping()
    conn31 = connect_db(DB_APP31)
    conn32 = connect_db(DB_APP32)
    cur31 = conn31.cursor()
    cur32 = conn32.cursor()

    cur31.execute("SELECT id, company_id, role_id, user_id, name, email, phone, whatsapp, department, hire_date, status, weekly_hours FROM employees")
    cols = [desc[0] for desc in cur31.description]
    rows = cur31.fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        old_id = str(data['id'])
        old_company_id = str(data['company_id'])
        
        if old_company_id not in mapping['companies']:
            continue
            
        new_company_id = mapping['companies'][old_company_id]
        new_user_id = mapping['users'].get(str(data['user_id']))
        new_role_id = mapping['roles'].get(str(data['role_id']))

        # Data conversion
        hire_date = None
        if data['hire_date']:
            try:
                hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except:
                pass

        cur32.execute("""
            INSERT INTO employees (company_id, user_id, role_id, name, email, phone, whatsapp, department, hire_date, status, weekly_hours, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (new_company_id, new_user_id, new_role_id, data['name'], data['email'], data['phone'], data['whatsapp'], data['department'], hire_date, data['status'], data['weekly_hours'], datetime.now(), datetime.now()))
        
        new_id = cur32.fetchone()[0]
        mapping['employees'][old_id] = new_id
        print(f"Colaborador: {data['name']} ({old_id} -> {new_id})")

    conn32.commit()
    save_mapping(mapping)
    cur31.close()
    cur32.close()
    conn31.close()
    conn32.close()

if __name__ == "__main__":
    migrate_companies()
    migrate_users()
    migrate_roles()
    migrate_employees()
