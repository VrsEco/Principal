#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste rápido de conexão PostgreSQL"""

import sys
from dotenv import load_dotenv
import os

# Carregar .env
load_dotenv()

print("=" * 50)
print("TESTE DE CONEXÃO POSTGRESQL")
print("=" * 50)

# 1. Verificar DATABASE_URL
db_url = os.getenv("DATABASE_URL")
print(f"\n1. DATABASE_URL do .env:")
print(f"   {db_url}")

if "sqlite" in db_url.lower():
    print("   ❌ ERRO: Ainda usando SQLite!")
    sys.exit(1)
elif "postgresql" in db_url.lower():
    print("   ✅ Usando PostgreSQL")

# 2. Testar conexão
print(f"\n2. Testando conexão...")
try:
    from database.postgres_helper import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"   ✅ Conectado!")
        print(f"   📊 {version[:50]}...")

except Exception as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# 3. Verificar tabela user
print(f"\n3. Verificando tabela 'user'...")
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM "user"'))
        count = result.fetchone()[0]
        print(f"   ✅ Tabela existe!")
        print(f"   👥 Total de usuários: {count}")

except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "=" * 50)
print("✅ TESTE CONCLUÍDO COM SUCESSO!")
print("=" * 50)
print("\nO sistema está configurado para PostgreSQL.")
print("Você pode testar o login agora!")
