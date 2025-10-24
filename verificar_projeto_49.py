#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config_database import get_db

print("=" * 70)
print("  VERIFICANDO PROJETO ID 49")
print("=" * 70)
print()

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

print("📋 Buscando projeto ID 49...")
cursor.execute("SELECT * FROM company_projects WHERE id = 49")
projeto = cursor.fetchone()

if projeto:
    projeto_dict = dict(projeto)
    print(f"✅ Projeto encontrado!")
    print(f"   ID: {projeto_dict.get('id')}")
    print(f"   Título: {projeto_dict.get('title')}")
    print(f"   Company ID: {projeto_dict.get('company_id')}")
    print(f"   Plan ID: {projeto_dict.get('plan_id')}")
    print(f"   Plan Type: {projeto_dict.get('plan_type')}")
    print(f"   Status: {projeto_dict.get('status')}")
else:
    print("❌ Projeto 49 NÃO encontrado!")

print()
print("📋 Listando todos os projetos da empresa 5...")
cursor.execute("SELECT id, title, plan_id, plan_type FROM company_projects WHERE company_id = 5 ORDER BY id DESC LIMIT 10")
projetos = cursor.fetchall()

if projetos:
    print(f"   Encontrados {len(projetos)} projetos:")
    for p in projetos:
        p_dict = dict(p)
        print(f"      ID {p_dict.get('id')}: {p_dict.get('title')} (plan_id={p_dict.get('plan_id')}, type={p_dict.get('plan_type')})")
else:
    print("   ❌ Nenhum projeto encontrado!")

cursor.close()
conn.close()

print()
print("=" * 70)

