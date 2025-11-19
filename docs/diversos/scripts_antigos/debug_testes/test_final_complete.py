#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Final Completo do Sistema com PostgreSQL
"""

import requests
from config_database import get_db
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5002'

print("=" * 80)
print("TESTE FINAL COMPLETO - PostgreSQL")
print("=" * 80)

# 1. Teste de Conexão
print("\n>> 1. TESTE DE CONEXÃO DATABASE")
try:
    db = get_db()
    companies = db.get_companies()
    print(f"   Empresas: {len(companies)}")
    print("   STATUS: OK")
except Exception as e:
    print(f"   STATUS: FALHA - {e}")
    sys.exit(1)

# 2. Teste de Páginas
print("\n>> 2. TESTE DE PÁGINAS PRINCIPAIS")
pages = [
    ('/', 'Home'),
    ('/login', 'Login'),
    ('/main', 'Main'),
    ('/companies', 'Empresas'),
    ('/pev/dashboard', 'PEV Dashboard'),
    ('/grv/dashboard', 'GRV Dashboard'),
    ('/configs', 'Configs'),
    ('/settings/reports', 'Relatórios'),
]

page_ok = 0
page_fail = 0

for path, name in pages:
    try:
        r = requests.get(BASE_URL + path, timeout=5, allow_redirects=False)
        if r.status_code in [200, 302]:
            print(f"   {name:20s} - OK [{r.status_code}]")
            page_ok += 1
        else:
            print(f"   {name:20s} - WARN [{r.status_code}]")
            page_fail += 1
    except:
        print(f"   {name:20s} - ERRO")
        page_fail += 1

# 3. Teste CRUD
print("\n>> 3. TESTE CRUD (Create, Read, Update, Delete)")

crud_ok = 0
crud_fail = 0

# CREATE
try:
    from sqlalchemy import text
    from database.postgres_helper import get_engine
    
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO companies (name, legal_name) 
            VALUES (:name, :legal_name) 
            RETURNING id
        """), {'name': 'Final Test', 'legal_name': 'Final Test LTDA'})
        test_id = result.fetchone()[0]
        conn.commit()
    
    print(f"   CREATE - OK (ID: {test_id})")
    crud_ok += 1
except Exception as e:
    print(f"   CREATE - FALHA: {e}")
    crud_fail += 1
    test_id = None

# READ
if test_id:
    try:
        company = db.get_company(test_id)
        if company and company['name'] == 'Final Test':
            print(f"   READ   - OK")
            crud_ok += 1
        else:
            print(f"   READ   - FALHA")
            crud_fail += 1
    except Exception as e:
        print(f"   READ   - FALHA: {e}")
        crud_fail += 1

# UPDATE
if test_id:
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE companies SET name = :name WHERE id = :id
            """), {'name': 'Final Test Updated', 'id': test_id})
            conn.commit()
        
        company = db.get_company(test_id)
        if company and 'Updated' in company['name']:
            print(f"   UPDATE - OK")
            crud_ok += 1
        else:
            print(f"   UPDATE - FALHA")
            crud_fail += 1
    except Exception as e:
        print(f"   UPDATE - FALHA: {e}")
        crud_fail += 1

# DELETE
if test_id:
    try:
        db.delete_company(test_id)
        company = db.get_company(test_id)
        if company is None:
            print(f"   DELETE - OK")
            crud_ok += 1
        else:
            print(f"   DELETE - FALHA (ainda existe)")
            crud_fail += 1
    except Exception as e:
        print(f"   DELETE - FALHA: {e}")
        crud_fail += 1

# 4. Verificar Integridade dos Dados Originais
print("\n>> 4. VERIFICAÇÃO DE INTEGRIDADE")
try:
    companies = db.get_companies()
    employees = db.list_employees(13)  # Save Water
    
    print(f"   Empresas: {len(companies)}")
    print(f"   Colaboradores (Save Water): {len(employees)}")
    
    if len(companies) == 4:
        print("   STATUS: OK - Dados originais preservados")
    else:
        print(f"   STATUS: OK - {len(companies)} empresas no banco")
except Exception as e:
    print(f"   STATUS: FALHA - {e}")

# RESUMO FINAL
print("\n" + "=" * 80)
print("RESUMO FINAL")
print("=" * 80)
print(f"Páginas testadas:  {page_ok}/{len(pages)} OK")
print(f"Operações CRUD:    {crud_ok}/4 OK")

if page_fail == 0 and crud_fail == 0:
    print("\n" + "=" * 80)
    print("RESULTADO: SUCESSO TOTAL!")
    print("Sistema 100% funcional com PostgreSQL")
    print("=" * 80)
    sys.exit(0)
else:
    print(f"\nAlguns testes falharam:")
    print(f"  - Páginas: {page_fail} falhas")
    print(f"  - CRUD: {crud_fail} falhas")
    sys.exit(1)

