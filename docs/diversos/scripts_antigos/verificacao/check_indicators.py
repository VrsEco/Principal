#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect


def check_indicators():
    """Verificar indicadores no banco"""

    try:
        conn = connect()
        cursor = conn.cursor()

        # Verificar estrutura da tabela
        print("=== ESTRUTURA DA TABELA INDICATORS ===")
        cursor.execute(
            """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'indicators' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        )
        columns = cursor.fetchall()

        print(f"Total de colunas: {len(columns)}")
        for col in columns[:10]:  # Primeiras 10
            print(f"  - {col[0]}: {col[1]}")

        # Contar indicadores
        print("\n=== INDICADORES NO BANCO ===")
        cursor.execute("SELECT COUNT(*) FROM indicators")
        total = cursor.fetchone()[0]
        print(f"Total de indicadores: {total}")

        if total > 0:
            # Listar por empresa
            cursor.execute(
                """
                SELECT company_id, COUNT(*) 
                FROM indicators 
                GROUP BY company_id 
                ORDER BY company_id
            """
            )
            by_company = cursor.fetchall()

            print("\nPor empresa:")
            for row in by_company:
                print(f"  Empresa {row[0]}: {row[1]} indicadores")

            # Mostrar alguns exemplos
            cursor.execute("SELECT id, company_id, title FROM indicators LIMIT 5")
            examples = cursor.fetchall()

            print("\nExemplos:")
            for row in examples:
                print(f"  ID {row[0]} - Empresa {row[1]}: {row[2]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_indicators()
