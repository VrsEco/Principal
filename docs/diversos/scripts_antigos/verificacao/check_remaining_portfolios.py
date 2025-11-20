#!/usr/bin/env python3
"""
Verificar portfólios restantes
"""

import sqlite3


def check_remaining_portfolios():
    """Verifica quais portfólios ainda existem."""

    print("Verificando portfólios restantes...")

    try:
        conn = sqlite3.connect("instance/pevapp22.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Verificar todos os portfólios da empresa 14
        print("Portfólios da empresa 14:")
        cursor.execute("SELECT * FROM portfolios WHERE company_id = 14")
        portfolios = cursor.fetchall()

        if portfolios:
            for p in portfolios:
                print(f"   - ID: {p['id']}, Nome: {p['name']}, Código: {p['code']}")

                # Verificar projetos associados
                cursor.execute(
                    "SELECT COUNT(*) FROM company_projects WHERE plan_id = ?",
                    (p["id"],),
                )
                project_count = cursor.fetchone()[0]
                print(f"     Projetos associados: {project_count}")

                if project_count > 0:
                    cursor.execute(
                        "SELECT id, code, title, plan_type FROM company_projects WHERE plan_id = ?",
                        (p["id"],),
                    )
                    projects = cursor.fetchall()
                    for proj in projects:
                        print(
                            f"       * {proj['code']} - {proj['title']} (Type: {proj['plan_type']})"
                        )
                print()
        else:
            print("   Nenhum portfólio encontrado!")

        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_remaining_portfolios()
