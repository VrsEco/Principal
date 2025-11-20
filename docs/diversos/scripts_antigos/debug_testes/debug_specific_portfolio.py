#!/usr/bin/env python3
"""
Debug específico do portfólio ID 10
"""

import sqlite3


def debug_specific_portfolio():
    """Debug específico do portfólio ID 10."""

    print("Debug específico do portfólio ID 10...")

    try:
        conn = sqlite3.connect("instance/pevapp22.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        portfolio_id = 10

        # Verificar informações do portfólio
        print(f"1. Informações do portfólio ID {portfolio_id}:")
        cursor.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
        portfolio = cursor.fetchone()
        if portfolio:
            print(f"   Nome: {portfolio['name']}")
            print(f"   Código: {portfolio['code']}")
            print(f"   Company ID: {portfolio['company_id']}")
        else:
            print("   Portfólio não encontrado!")
            return

        print()

        # Verificar TODOS os projetos com plan_id = 10
        print(f"2. TODOS os projetos com plan_id = {portfolio_id}:")
        cursor.execute(
            "SELECT * FROM company_projects WHERE plan_id = ?", (portfolio_id,)
        )
        projects = cursor.fetchall()
        print(f"   Total encontrados: {len(projects)}")

        for proj in projects:
            print(
                f"   - ID: {proj['id']}, Code: {proj['code']}, Title: {proj['title']}"
            )
            print(f"     Plan ID: {proj['plan_id']}, Plan Type: {proj['plan_type']}")

        print()

        # Testar a consulta exata que está sendo usada na validação
        print(f"3. Testando consulta de validação:")
        cursor.execute(
            "SELECT COUNT(*) FROM company_projects WHERE plan_id = ? AND (plan_type = 'GRV' OR plan_type IS NULL)",
            (portfolio_id,),
        )
        count_with_filter = cursor.fetchone()[0]
        print(f"   Count com filtro GRV/NULL: {count_with_filter}")

        cursor.execute(
            "SELECT COUNT(*) FROM company_projects WHERE plan_id = ?", (portfolio_id,)
        )
        count_total = cursor.fetchone()[0]
        print(f"   Count total: {count_total}")

        print()

        # Verificar se há projetos com plan_type específico
        print(f"4. Projetos por plan_type:")
        cursor.execute(
            "SELECT plan_type, COUNT(*) FROM company_projects WHERE plan_id = ? GROUP BY plan_type",
            (portfolio_id,),
        )
        by_type = cursor.fetchall()
        for bt in by_type:
            print(f"   - Plan Type: {bt[0]}, Count: {bt[1]}")

        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_specific_portfolio()
