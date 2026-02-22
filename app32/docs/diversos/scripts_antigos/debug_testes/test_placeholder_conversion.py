#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect


def test():
    """Testar conversao de placeholders"""

    company_id = 13

    try:
        conn = connect()
        cursor = conn.cursor()

        print("=== TESTE 1: Placeholder ? simples ===")
        cursor.execute(
            """
            SELECT *
            FROM indicators
            WHERE company_id = ?
        """,
            (company_id,),
        )

        rows = cursor.fetchall()
        print(f"Resultados: {len(rows)}")

        if rows:
            for row in rows:
                row_dict = dict(row)
                print(f"  ID {row_dict['id']}: {row_dict['name']}")

        print("\n=== TESTE 2: Query complexa com JOIN ===")
        cursor.execute(
            """
            SELECT 
                i.*,
                g.code as group_code,
                g.name as group_name
            FROM indicators i
            LEFT JOIN indicator_groups g ON i.group_id = g.id
            WHERE i.company_id = ?
            ORDER BY i.code
        """,
            (company_id,),
        )

        rows2 = cursor.fetchall()
        print(f"Resultados: {len(rows2)}")

        if rows2:
            for row in rows2:
                row_dict = dict(row)
                print(
                    f"  ID {row_dict['id']}: {row_dict['name']} - Grupo: {row_dict.get('group_name', 'Sem grupo')}"
                )

        cursor.close()
        conn.close()

        print("\n=== SUCESSO ===")

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test()
