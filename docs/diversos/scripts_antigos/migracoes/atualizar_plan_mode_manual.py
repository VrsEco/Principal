#!/usr/bin/env python3
"""
Script para atualizar plan_mode de planos existentes
Use este script para corrigir planos que foram criados com plan_mode errado
"""

import sys
from config_database import get_db


def listar_planos():
    """Lista todos os planos com seus IDs e plan_mode"""
    db = get_db()

    try:
        # Para PostgreSQL e SQLite
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.id, p.name, p.plan_mode, p.created_at, c.name as company_name
            FROM plans p
            LEFT JOIN companies c ON p.company_id = c.id
            ORDER BY p.created_at DESC
            LIMIT 20
        """
        )

        rows = cursor.fetchall()

        print("\n" + "=" * 100)
        print("PLANOS CADASTRADOS:")
        print("=" * 100)
        print(
            f"{'ID':<5} {'EMPRESA':<30} {'NOME DO PLANO':<35} {'TIPO':<15} {'CRIADO EM'}"
        )
        print("-" * 100)

        for row in rows:
            plan_id = row[0]
            plan_name = row[1] or "Sem nome"
            plan_mode = row[2] or "NULL"
            created_at = str(row[3]) if row[3] else "N/A"
            company_name = row[4] or "Sem empresa"

            # Truncar strings longas
            plan_name = (plan_name[:32] + "...") if len(plan_name) > 35 else plan_name
            company_name = (
                (company_name[:27] + "...") if len(company_name) > 30 else company_name
            )
            created_at = created_at[:19] if len(created_at) > 19 else created_at

            print(
                f"{plan_id:<5} {company_name:<30} {plan_name:<35} {plan_mode:<15} {created_at}"
            )

        print("=" * 100)
        print(f"\nTotal: {len(rows)} planos\n")

        conn.close()
        return rows

    except Exception as e:
        print(f"Erro ao listar planos: {e}")
        return []


def atualizar_plan_mode(plan_id: int, novo_tipo: str):
    """Atualiza o plan_mode de um plano específico"""

    if novo_tipo not in ["evolucao", "implantacao"]:
        print(f"❌ Tipo inválido: {novo_tipo}")
        print("   Use: 'evolucao' ou 'implantacao'")
        return False

    db = get_db()

    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        # Verificar se o plano existe
        if hasattr(db, "_db_type") and db._db_type == "postgresql":
            cursor.execute("SELECT name FROM plans WHERE id = %s", (plan_id,))
        else:
            cursor.execute("SELECT name FROM plans WHERE id = ?", (plan_id,))

        row = cursor.fetchone()

        if not row:
            print(f"❌ Plano com ID {plan_id} não encontrado!")
            conn.close()
            return False

        plan_name = row[0]

        # Atualizar
        if hasattr(db, "_db_type") and db._db_type == "postgresql":
            cursor.execute(
                "UPDATE plans SET plan_mode = %s WHERE id = %s", (novo_tipo, plan_id)
            )
        else:
            cursor.execute(
                "UPDATE plans SET plan_mode = ? WHERE id = ?", (novo_tipo, plan_id)
            )

        conn.commit()
        conn.close()

        print(f"\n✅ Plano atualizado com sucesso!")
        print(f"   ID: {plan_id}")
        print(f"   Nome: {plan_name}")
        print(f"   Novo tipo: {novo_tipo}")

        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar plano: {e}")
        return False


def menu_interativo():
    """Menu interativo para atualizar planos"""

    print("\n" + "=" * 100)
    print("ATUALIZAR PLAN_MODE - MENU INTERATIVO")
    print("=" * 100)

    # Listar planos
    planos = listar_planos()

    if not planos:
        print("Nenhum plano encontrado.")
        return

    print("\nOPÇÕES:")
    print("1. Atualizar um plano específico")
    print("2. Atualizar múltiplos planos")
    print("3. Sair")

    opcao = input("\nEscolha uma opção (1-3): ").strip()

    if opcao == "1":
        # Atualizar um plano
        plan_id = input("\nDigite o ID do plano: ").strip()

        try:
            plan_id = int(plan_id)
        except ValueError:
            print("❌ ID inválido!")
            return

        print("\nTIPOS DISPONÍVEIS:")
        print("  evolucao    - Planejamento de Evolução (Clássico)")
        print("  implantacao - Planejamento de Implantação (Novo Negócio)")

        tipo = input("\nDigite o tipo (evolucao ou implantacao): ").strip().lower()

        atualizar_plan_mode(plan_id, tipo)

    elif opcao == "2":
        # Atualizar múltiplos planos
        ids = input(
            "\nDigite os IDs dos planos separados por vírgula (ex: 1,2,3): "
        ).strip()

        try:
            plan_ids = [int(x.strip()) for x in ids.split(",")]
        except ValueError:
            print("❌ IDs inválidos!")
            return

        tipo = (
            input("\nDigite o tipo para TODOS (evolucao ou implantacao): ")
            .strip()
            .lower()
        )

        for plan_id in plan_ids:
            atualizar_plan_mode(plan_id, tipo)
            print()

    else:
        print("Saindo...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Modo CLI: python atualizar_plan_mode_manual.py <plan_id> <tipo>
        if len(sys.argv) < 3:
            print("Uso: python atualizar_plan_mode_manual.py <plan_id> <tipo>")
            print("Exemplo: python atualizar_plan_mode_manual.py 5 implantacao")
            sys.exit(1)

        plan_id = int(sys.argv[1])
        tipo = sys.argv[2].lower()

        atualizar_plan_mode(plan_id, tipo)
    else:
        # Modo interativo
        menu_interativo()
