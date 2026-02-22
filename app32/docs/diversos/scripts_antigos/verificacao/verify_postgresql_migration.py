#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação da Migração PostgreSQL
Verifica se a migração foi bem-sucedida e compara dados entre SQLite e PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configurações
SQLITE_DB = "instance/pevapp22.db"
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", 5432)),
    "database": "bd_app_versus",
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "password"),
}


def connect_sqlite():
    """Conectar ao banco SQLite"""
    try:
        if not os.path.exists(SQLITE_DB):
            print(f"❌ Arquivo SQLite não encontrado: {SQLITE_DB}")
            return None

        conn = sqlite3.connect(SQLITE_DB)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar SQLite: {e}")
        return None


def connect_postgresql():
    """Conectar ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar PostgreSQL: {e}")
        return None


def get_table_count(conn, table_name, db_type):
    """Obter contagem de registros em uma tabela"""
    try:
        cursor = conn.cursor()
        if db_type == "sqlite":
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        else:  # postgresql
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

        count = cursor.fetchone()[0]
        cursor.close()
        return count
    except Exception as e:
        print(f"  ⚠️  Erro ao contar registros em '{table_name}': {e}")
        return 0


def get_table_structure(conn, table_name, db_type):
    """Obter estrutura de uma tabela"""
    try:
        cursor = conn.cursor()

        if db_type == "sqlite":
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
        else:  # postgresql
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """,
                (table_name,),
            )
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]

        cursor.close()
        return column_names
    except Exception as e:
        print(f"  ⚠️  Erro ao obter estrutura da tabela '{table_name}': {e}")
        return []


def compare_table_data(sqlite_conn, postgres_conn, table_name):
    """Comparar dados entre SQLite e PostgreSQL para uma tabela"""
    try:
        # Obter contagens
        sqlite_count = get_table_count(sqlite_conn, table_name, "sqlite")
        postgres_count = get_table_count(postgres_conn, table_name, "postgresql")

        # Obter estruturas
        sqlite_columns = get_table_structure(sqlite_conn, table_name, "sqlite")
        postgres_columns = get_table_structure(postgres_conn, table_name, "postgresql")

        # Comparar
        status = "✅"
        issues = []

        if sqlite_count != postgres_count:
            status = "⚠️"
            issues.append(
                f"Contagem diferente: SQLite={sqlite_count}, PostgreSQL={postgres_count}"
            )

        if len(sqlite_columns) != len(postgres_columns):
            status = "⚠️"
            issues.append(
                f"Número de colunas diferente: SQLite={len(sqlite_columns)}, PostgreSQL={len(postgres_columns)}"
            )

        # Verificar se todas as colunas SQLite existem no PostgreSQL
        missing_columns = set(sqlite_columns) - set(postgres_columns)
        if missing_columns:
            status = "❌"
            issues.append(f"Colunas ausentes no PostgreSQL: {missing_columns}")

        print(f"  {status} {table_name}: {sqlite_count} registros")
        for issue in issues:
            print(f"    ⚠️  {issue}")

        return {
            "table": table_name,
            "status": status,
            "sqlite_count": sqlite_count,
            "postgres_count": postgres_count,
            "issues": issues,
        }

    except Exception as e:
        print(f"  ❌ Erro ao comparar tabela '{table_name}': {e}")
        return {"table": table_name, "status": "❌", "error": str(e)}


def test_connection():
    """Testar conectividade com PostgreSQL"""
    print("🔍 Testando conectividade...")

    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        # Testar versão do PostgreSQL
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL conectado: {version.split(',')[0]}")

        # Testar se o banco existe e tem tabelas
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cursor.fetchall()]

        if tables:
            print(f"✅ {len(tables)} tabelas encontradas no banco")
        else:
            print("⚠️  Nenhuma tabela encontrada no banco")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro ao conectar PostgreSQL: {e}")
        return False


def verify_critical_data(postgres_conn):
    """Verificar se dados críticos foram migrados"""
    print("\n🔍 Verificando dados críticos...")

    critical_checks = [
        {
            "name": "Usuários",
            "table": "users",
            "min_count": 1,
            "description": "Deve ter pelo menos 1 usuário",
        },
        {
            "name": "Empresas",
            "table": "companies",
            "min_count": 1,
            "description": "Deve ter pelo menos 1 empresa",
        },
    ]

    all_ok = True

    for check in critical_checks:
        try:
            cursor = postgres_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {check['table']}")
            count = cursor.fetchone()[0]
            cursor.close()

            if count >= check["min_count"]:
                print(
                    f"  ✅ {check['name']}: {count} registros ({check['description']})"
                )
            else:
                print(
                    f"  ❌ {check['name']}: apenas {count} registros ({check['description']})"
                )
                all_ok = False

        except Exception as e:
            print(f"  ❌ {check['name']}: erro ao verificar - {e}")
            all_ok = False

    return all_ok


def generate_report(comparison_results):
    """Gerar relatório final"""
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO DE VERIFICAÇÃO DA MIGRAÇÃO")
    print("=" * 60)

    total_tables = len(comparison_results)
    successful_tables = sum(1 for r in comparison_results if r["status"] == "✅")
    warning_tables = sum(1 for r in comparison_results if r["status"] == "⚠️")
    error_tables = sum(1 for r in comparison_results if r["status"] == "❌")

    print(f"📋 Total de tabelas verificadas: {total_tables}")
    print(f"✅ Tabelas OK: {successful_tables}")
    print(f"⚠️  Tabelas com avisos: {warning_tables}")
    print(f"❌ Tabelas com erros: {error_tables}")

    if error_tables > 0:
        print("\n❌ TABELAS COM ERROS:")
        for result in comparison_results:
            if result["status"] == "❌":
                print(
                    f"  - {result['table']}: {result.get('error', 'Erro desconhecido')}"
                )

    if warning_tables > 0:
        print("\n⚠️  TABELAS COM AVISOS:")
        for result in comparison_results:
            if result["status"] == "⚠️":
                print(f"  - {result['table']}: {', '.join(result.get('issues', []))}")

    # Status geral
    if error_tables == 0 and warning_tables == 0:
        print("\n🎉 MIGRAÇÃO VERIFICADA COM SUCESSO!")
        return True
    elif error_tables == 0:
        print("\n✅ MIGRAÇÃO CONCLUÍDA COM AVISOS MENORES")
        return True
    else:
        print("\n❌ MIGRAÇÃO COM PROBLEMAS - VERIFICAÇÃO NECESSÁRIA")
        return False


def main():
    """Função principal de verificação"""
    print("🔍 Verificando migração SQLite → PostgreSQL")
    print(f"📊 Banco: {POSTGRES_CONFIG['database']}")
    print("-" * 60)

    # 1. Testar conectividade
    if not test_connection():
        print("❌ Falha na conectividade - verificação abortada")
        return False

    # 2. Conectar aos bancos
    print("\n🔗 Conectando aos bancos de dados...")
    sqlite_conn = connect_sqlite()
    postgres_conn = connect_postgresql()

    if not sqlite_conn or not postgres_conn:
        print("❌ Falha na conexão com os bancos")
        return False

    # 3. Obter lista de tabelas do SQLite
    print("\n📋 Identificando tabelas para verificação...")
    try:
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        sqlite_cursor.close()
        print(f"📊 {len(tables)} tabelas encontradas no SQLite")
    except Exception as e:
        print(f"❌ Erro ao obter tabelas SQLite: {e}")
        sqlite_conn.close()
        postgres_conn.close()
        return False

    # 4. Comparar cada tabela
    print("\n🔍 Comparando dados entre bancos...")
    comparison_results = []

    for table_name in tables:
        result = compare_table_data(sqlite_conn, postgres_conn, table_name)
        comparison_results.append(result)

    # 5. Verificar dados críticos
    critical_ok = verify_critical_data(postgres_conn)

    # 6. Fechar conexões
    sqlite_conn.close()
    postgres_conn.close()

    # 7. Gerar relatório
    migration_ok = generate_report(comparison_results)

    return migration_ok and critical_ok


if __name__ == "__main__":
    # Verificar se PostgreSQL está configurado
    if not os.environ.get("POSTGRES_PASSWORD"):
        print("❌ Configure a variável POSTGRES_PASSWORD antes de executar")
        print("   Exemplo: export POSTGRES_PASSWORD=sua_senha")
        sys.exit(1)

    success = main()
    sys.exit(0 if success else 1)
