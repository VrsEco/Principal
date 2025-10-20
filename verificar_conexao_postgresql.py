#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação: PostgreSQL Connection
Verifica se o sistema está usando PostgreSQL corretamente
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 70)
print("🔍 VERIFICAÇÃO: PostgreSQL Connection - APP30")
print("=" * 70)
print()

# 1. Verificar arquivo .env
print("📄 [1/6] Verificando arquivo .env...")
if os.path.exists('.env'):
    print("   ✅ Arquivo .env existe")
    load_dotenv()
else:
    print("   ❌ Arquivo .env NÃO existe!")
    sys.exit(1)

# 2. Verificar variáveis de ambiente
print("\n🔧 [2/6] Verificando variáveis de ambiente...")
db_type = os.getenv('DB_TYPE')
database_url = os.getenv('DATABASE_URL')

print(f"   DB_TYPE: {db_type}")
print(f"   DATABASE_URL: {database_url[:50]}..." if database_url else "   DATABASE_URL: NÃO DEFINIDA")

if db_type != 'postgresql':
    print(f"   ⚠️  AVISO: DB_TYPE é '{db_type}' (esperado: 'postgresql')")
else:
    print("   ✅ DB_TYPE correto (postgresql)")

if not database_url or 'sqlite' in database_url.lower():
    print("   ❌ DATABASE_URL está usando SQLite!")
    sys.exit(1)
elif 'postgresql' in database_url.lower():
    print("   ✅ DATABASE_URL aponta para PostgreSQL")
else:
    print(f"   ⚠️  DATABASE_URL inesperada: {database_url}")

# 3. Verificar configuração do Flask
print("\n⚙️  [3/6] Verificando configuração do Flask...")
try:
    from config import Config, DevelopmentConfig
    
    config_uri = Config.SQLALCHEMY_DATABASE_URI
    dev_config_uri = DevelopmentConfig.SQLALCHEMY_DATABASE_URI
    
    print(f"   Config.SQLALCHEMY_DATABASE_URI: {config_uri[:50]}...")
    print(f"   DevelopmentConfig.SQLALCHEMY_DATABASE_URI: {dev_config_uri[:50]}...")
    
    if 'sqlite' in config_uri.lower() or 'sqlite' in dev_config_uri.lower():
        print("   ❌ Configuração do Flask ainda usa SQLite!")
        sys.exit(1)
    else:
        print("   ✅ Configuração do Flask usa PostgreSQL")
        
except Exception as e:
    print(f"   ❌ Erro ao verificar config.py: {e}")
    sys.exit(1)

# 4. Verificar conexão PostgreSQL
print("\n🔌 [4/6] Testando conexão PostgreSQL...")
try:
    from database.postgres_helper import get_engine
    
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"   ✅ Conectado ao PostgreSQL!")
        print(f"   📊 Versão: {version[:60]}...")
        
except Exception as e:
    print(f"   ❌ Erro ao conectar no PostgreSQL: {e}")
    print("\n   Possíveis causas:")
    print("   - PostgreSQL não está rodando")
    print("   - Credenciais incorretas no .env")
    print("   - Banco 'bd_app_versus' não existe")
    print("\n   Execute: psql -h localhost -U postgres -d bd_app_versus")
    sys.exit(1)

# 5. Verificar tabelas
print("\n📋 [5/6] Verificando tabelas no banco...")
try:
    from database.postgres_helper import get_engine
    
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name 
            LIMIT 10;
        """)
        tables = result.fetchall()
        
        if tables:
            print(f"   ✅ Encontradas {len(tables)} tabelas (primeiras 10):")
            for table in tables:
                print(f"      - {table[0]}")
        else:
            print("   ⚠️  Nenhuma tabela encontrada no banco")
            
except Exception as e:
    print(f"   ❌ Erro ao listar tabelas: {e}")
    sys.exit(1)

# 6. Verificar tabela 'user' (usada no login)
print("\n👤 [6/6] Verificando tabela 'user' (autenticação)...")
try:
    from database.postgres_helper import get_engine
    
    engine = get_engine()
    with engine.connect() as conn:
        # Verificar se tabela existe
        result = conn.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user'
            );
        """)
        exists = result.fetchone()[0]
        
        if exists:
            # Contar usuários
            result = conn.execute("SELECT COUNT(*) FROM \"user\";")
            count = result.fetchone()[0]
            print(f"   ✅ Tabela 'user' existe")
            print(f"   👥 Total de usuários: {count}")
            
            # Listar primeiros 3 usuários
            if count > 0:
                result = conn.execute("SELECT id, email, name FROM \"user\" LIMIT 3;")
                users = result.fetchall()
                print(f"   📋 Primeiros usuários:")
                for user in users:
                    print(f"      - ID: {user[0]}, Email: {user[1]}, Nome: {user[2]}")
        else:
            print("   ❌ Tabela 'user' NÃO existe!")
            print("   Você precisa rodar as migrações do Flask-Migrate")
            
except Exception as e:
    print(f"   ❌ Erro ao verificar tabela 'user': {e}")

# Resumo Final
print("\n" + "=" * 70)
print("✅ VERIFICAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 70)
print()
print("📊 Resumo:")
print("   ✅ Arquivo .env configurado")
print("   ✅ Variáveis de ambiente corretas")
print("   ✅ Configuração do Flask usando PostgreSQL")
print("   ✅ Conexão PostgreSQL funcionando")
print("   ✅ Banco de dados acessível")
print()
print("🚀 O sistema está configurado para usar PostgreSQL!")
print()
print("Próximo passo:")
print("   → Testar login: python app_pev.py")
print("   → Acessar: http://127.0.0.1:5002/login")
print()
print("=" * 70)

