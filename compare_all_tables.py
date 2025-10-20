#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database.postgres_helper import connect

def compare_tables():
    """Comparar todas as tabelas entre SQLite e PostgreSQL"""
    
    print("=== COMPARANDO TABELAS ===\n")
    
    # SQLite
    sqlite_conn = sqlite3.connect('instance/pevapp22.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    sqlite_cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    
    sqlite_tables = set([row[0] for row in sqlite_cursor.fetchall()])
    print(f"Tabelas no SQLite: {len(sqlite_tables)}")
    
    sqlite_conn.close()
    
    # PostgreSQL
    pg_conn = connect()
    pg_cursor = pg_conn.cursor()
    
    pg_cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    
    pg_tables = set([row[0] for row in pg_cursor.fetchall()])
    print(f"Tabelas no PostgreSQL: {len(pg_tables)}")
    
    pg_cursor.close()
    pg_conn.close()
    
    # Comparar
    missing_in_pg = sqlite_tables - pg_tables
    extra_in_pg = pg_tables - sqlite_tables
    
    if missing_in_pg:
        print(f"\n=== TABELAS FALTANDO NO POSTGRESQL ({len(missing_in_pg)}) ===")
        for table in sorted(missing_in_pg):
            print(f"  - {table}")
    else:
        print("\n=== Todas as tabelas do SQLite estao no PostgreSQL! ===")
    
    if extra_in_pg:
        print(f"\n=== TABELAS EXTRAS NO POSTGRESQL ({len(extra_in_pg)}) ===")
        for table in sorted(extra_in_pg):
            print(f"  - {table}")
    
    # Tabelas em comum
    common = sqlite_tables & pg_tables
    print(f"\n=== TABELAS EM COMUM: {len(common)} ===")

if __name__ == "__main__":
    compare_tables()
