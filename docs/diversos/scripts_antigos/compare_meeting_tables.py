#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database.postgres_helper import connect


def compare_meeting_tables():
    """Comparar tabelas meeting entre SQLite e PostgreSQL"""

    # SQLite
    print("=== TABELAS MEETING NO SQLITE ===")
    try:
        sqlite_conn = sqlite3.connect("instance/pevapp22.db")
        sqlite_cursor = sqlite_conn.cursor()

        sqlite_cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%meeting%' 
            ORDER BY name
        """
        )

        sqlite_tables = sqlite_cursor.fetchall()
        for table in sqlite_tables:
            print(f"  - {table[0]}")

        sqlite_conn.close()
    except Exception as e:
        print(f"Erro SQLite: {e}")

    # PostgreSQL
    print("\n=== TABELAS MEETING NO POSTGRESQL ===")
    try:
        pg_conn = connect()
        pg_cursor = pg_conn.cursor()

        pg_cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%meeting%' 
            ORDER BY table_name
        """
        )

        pg_tables = pg_cursor.fetchall()
        for table in pg_tables:
            print(f"  - {table[0]}")

        pg_cursor.close()
        pg_conn.close()
    except Exception as e:
        print(f"Erro PostgreSQL: {e}")

    # Identificar faltantes
    print("\n=== TABELAS FALTANTES ===")
    sqlite_names = [t[0] for t in sqlite_tables]
    pg_names = [t[0] for t in pg_tables]

    missing = set(sqlite_names) - set(pg_names)
    if missing:
        print("Tabelas que existem no SQLite mas não no PostgreSQL:")
        for table in missing:
            print(f"  - {table}")
    else:
        print("Todas as tabelas meeting foram migradas!")


if __name__ == "__main__":
    compare_meeting_tables()
