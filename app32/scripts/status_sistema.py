#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status do Sistema APP30 - PostgreSQL
Execute este script para verificar o status geral
"""

import requests
from config_database import get_db
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

print("\n" + "=" * 80)
print(" " * 20 + "STATUS DO SISTEMA APP30")
print("=" * 80)

# 1. Database
print("\n DATABASE")
print("-" * 80)
try:
    db = get_db()
    companies = db.get_companies()

    print(f"   Tipo: PostgreSQL")
    print(f"   Status: ONLINE")
    print(f"   Empresas: {len(companies)}")

    for company in companies:
        print(f"      - {company['name']}")

except Exception as e:
    print(f"   Status: ERRO - {e}")

# 2. Servidor
print("\n SERVIDOR WEB")
print("-" * 80)
try:
    r = requests.get("http://127.0.0.1:5002", timeout=3, allow_redirects=False)
    print(f"   URL: http://127.0.0.1:5002")
    print(f"   Status: ONLINE")
    print(f"   Codigo: {r.status_code}")
except Exception as e:
    print(f"   Status: OFFLINE - {e}")

# 3. Resumo de Dados
print("\n DADOS NO SISTEMA")
print("-" * 80)
try:
    from database.postgres_helper import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        # Contar registros principais
        tables = [
            ("companies", "Empresas"),
            ("users", "Usuários"),
            ("company_projects", "Projetos"),
            ("meetings", "Reuniões"),
            ("employees", "Colaboradores"),
            ("processes", "Processos"),
            ("indicators", "Indicadores"),
            ("portfolios", "Portfólios"),
        ]

        for table, label in tables:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = result.fetchone()[0]
            print(f"   {label:20s}: {count:4d}")

except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "=" * 80)
print(" " * 25 + "SISTEMA OPERACIONAL")
print("=" * 80 + "\n")
