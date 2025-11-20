#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database.postgres_helper import connect


def check_drivers():
    """Verificar tabela drivers"""

    print("=== SQLITE ===")
    try:
        sqlite_conn = sqlite3.connect("instance/pevapp22.db")
        sqlite_cursor = sqlite_conn.cursor()

        # Verificar se existe
        sqlite_cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='drivers'
        """
        )

        if sqlite_cursor.fetchone():
            print("Tabela 'drivers' existe no SQLite")

            # Estrutura
            sqlite_cursor.execute("PRAGMA table_info(drivers)")
            columns = sqlite_cursor.fetchall()
            print(f"\nColunas ({len(columns)}):")
            for col in columns:
                print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")

            # Dados
            sqlite_cursor.execute("SELECT COUNT(*) FROM drivers")
            count = sqlite_cursor.fetchone()[0]
            print(f"\nRegistros: {count}")

            if count > 0:
                sqlite_cursor.execute("SELECT * FROM drivers LIMIT 3")
                rows = sqlite_cursor.fetchall()
                print("\nPrimeiros registros:")
                for row in rows:
                    print(f"  {row}")
        else:
            print("Tabela 'drivers' NAO existe no SQLite")

        sqlite_conn.close()

    except Exception as e:
        print(f"Erro SQLite: {e}")

    print("\n=== POSTGRESQL ===")
    try:
        pg_conn = connect()
        pg_cursor = pg_conn.cursor()

        # Verificar se existe
        pg_cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'drivers'
        """
        )

        if pg_cursor.fetchone():
            print("Tabela 'drivers' existe no PostgreSQL")

            # Dados
            pg_cursor.execute("SELECT COUNT(*) FROM drivers")
            count = pg_cursor.fetchone()[0]
            print(f"Registros: {count}")
        else:
            print("Tabela 'drivers' NAO existe no PostgreSQL")

        pg_cursor.close()
        pg_conn.close()

    except Exception as e:
        print(f"Erro PostgreSQL: {e}")


if __name__ == "__main__":
    check_drivers()
