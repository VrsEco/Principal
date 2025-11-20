#!/usr/bin/env python3
"""
Debug da validação de exclusão de portfólios
"""

import sqlite3


def debug_portfolio_delete():
    """Debug da validação de exclusão."""

    print("Debug da validação de exclusão de portfólios...")

    try:
        conn = sqlite3.connect("instance/pevapp22.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Verificar portfólios da empresa 14
        print("1. Portfólios da empresa 14:")
        cursor.execute("SELECT id, name, code FROM portfolios WHERE company_id = 14")
        portfolios = cursor.fetchall()
        for p in portfolios:
            print(f"   - ID: {p['id']}, Nome: {p['name']}, Código: {p['code']}")

        print()

        # Verificar projetos associados a cada portfólio
        print("2. Projetos associados aos portfólios:")
        for portfolio in portfolios:
            portfolio_id = portfolio["id"]
            cursor.execute(
                "SELECT COUNT(*) FROM company_projects WHERE plan_id = ?",
                (portfolio_id,),
            )
            count = cursor.fetchone()[0]
            print(
                f"   - Portfólio {portfolio['name']} (ID: {portfolio_id}): {count} projetos"
            )

            if count > 0:
                # Mostrar detalhes dos projetos
                cursor.execute(
                    "SELECT id, code, title FROM company_projects WHERE plan_id = ?",
                    (portfolio_id,),
                )
                projects = cursor.fetchall()
                for proj in projects:
                    print(f"     * Projeto: {proj['code']} - {proj['title']}")

        print()

        # Verificar se há projetos com plan_type diferente
        print("3. Projetos com diferentes plan_type:")
        cursor.execute(
            "SELECT plan_id, plan_type, COUNT(*) as count FROM company_projects GROUP BY plan_id, plan_type"
        )
        plan_types = cursor.fetchall()
        for pt in plan_types:
            print(
                f"   - Plan ID: {pt['plan_id']}, Plan Type: {pt['plan_type']}, Count: {pt['count']}"
            )

        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_portfolio_delete()
