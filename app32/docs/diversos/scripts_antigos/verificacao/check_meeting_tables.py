#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect


def check_meeting_tables():
    """Verificar tabelas meeting no PostgreSQL"""
    try:
        conn = connect()
        cursor = conn.cursor()

        # Verificar tabelas meeting
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%meeting%' 
            ORDER BY table_name
        """
        )

        tables = cursor.fetchall()
        print("Tabelas meeting encontradas no PostgreSQL:")
        if tables:
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("  Nenhuma tabela meeting encontrada")

        # Verificar todas as tabelas
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """
        )

        all_tables = cursor.fetchall()
        print(f"\nTotal de tabelas: {len(all_tables)}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    check_meeting_tables()
