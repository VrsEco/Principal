"""
Script para vincular Users existentes aos Employees correspondentes
Executa matching por email e popula o campo user_id

Uso:
    python link_users_to_employees.py

Autor: AI Assistant
Data: 2025-10-22
"""

import sys
from database.postgres_helper import connect as pg_connect
from models.user import User
from models import db


def link_users_to_employees():
    """
    Vincula users existentes aos employees por email
    """
    print("=" * 80)
    print("VINCULANDO USERS A EMPLOYEES")
    print("=" * 80)

    # Buscar todos os users
    users = User.query.all()
    print(f"\n✅ Encontrados {len(users)} usuários no sistema\n")

    if len(users) == 0:
        print(
            "⚠️  Nenhum usuário encontrado. Execute primeiro o script de criação de usuários."
        )
        return

    conn = pg_connect()
    cursor = conn.cursor()

    linked_count = 0
    not_found_count = 0
    already_linked_count = 0

    for user in users:
        print(f"🔍 Processando: {user.name} ({user.email})")

        try:
            # Verificar se employee existe com este email
            cursor.execute(
                """
                SELECT id, name, user_id
                FROM employees
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """,
                (user.email,),
            )

            row = cursor.fetchone()

            if not row:
                print(f"   ⚠️  Colaborador não encontrado para email: {user.email}")
                not_found_count += 1
                continue

            employee_id = row[0]
            employee_name = row[1]
            current_user_id = row[2]

            # Verificar se já está vinculado
            if current_user_id is not None:
                if current_user_id == user.id:
                    print(
                        f"   ✅ Já vinculado: Employee #{employee_id} -> User #{user.id}"
                    )
                    already_linked_count += 1
                else:
                    print(
                        f"   ⚠️  Employee #{employee_id} já vinculado a outro user (#{current_user_id})"
                    )
                continue

            # Vincular
            cursor.execute(
                """
                UPDATE employees
                SET user_id = %s
                WHERE id = %s
            """,
                (user.id, employee_id),
            )

            conn.commit()
            linked_count += 1
            print(
                f"   ✅ VINCULADO: Employee #{employee_id} ({employee_name}) -> User #{user.id} ({user.name})"
            )

        except Exception as e:
            print(f"   ❌ ERRO ao processar {user.email}: {e}")
            conn.rollback()
            continue

    cursor.close()
    conn.close()

    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DA VINCULAÇÃO")
    print("=" * 80)
    print(f"✅ Vinculados com sucesso: {linked_count}")
    print(f"ℹ️  Já estavam vinculados: {already_linked_count}")
    print(f"⚠️  Colaboradores não encontrados: {not_found_count}")
    print(f"📊 Total de usuários processados: {len(users)}")
    print("=" * 80)

    if linked_count > 0:
        print("\n🎉 Vinculação concluída com sucesso!")
        print("   Agora os usuários podem acessar o My Work Dashboard.")
    elif already_linked_count > 0:
        print("\n✅ Todos os usuários já estavam vinculados.")
    else:
        print("\n⚠️  Nenhuma vinculação foi realizada.")
        print(
            "   Certifique-se de que existem employees com emails correspondentes aos users."
        )


def verify_links():
    """
    Verifica a situação atual dos vínculos
    """
    print("\n" + "=" * 80)
    print("VERIFICANDO VÍNCULOS")
    print("=" * 80)

    conn = pg_connect()
    cursor = conn.cursor()

    # Employees com user_id
    cursor.execute(
        """
        SELECT 
            e.id,
            e.name,
            e.email,
            e.user_id,
            u.name as user_name,
            u.email as user_email
        FROM employees e
        LEFT JOIN users u ON u.id = e.user_id
        WHERE e.user_id IS NOT NULL
        ORDER BY e.name
    """
    )

    linked = cursor.fetchall()

    if linked:
        print(f"\n✅ {len(linked)} colaboradores com acesso ao sistema:")
        print("-" * 80)
        for row in linked:
            print(f"   Employee #{row[0]}: {row[1]} ({row[2]})")
            print(f"   └─ User #{row[3]}: {row[4]} ({row[5]})")
            print()
    else:
        print("\n⚠️  Nenhum colaborador vinculado a usuários.")

    # Employees sem user_id
    cursor.execute(
        """
        SELECT id, name, email
        FROM employees
        WHERE user_id IS NULL
        ORDER BY name
        LIMIT 10
    """
    )

    not_linked = cursor.fetchall()

    if not_linked:
        print(f"\n📋 Colaboradores sem acesso ao sistema (amostra de 10):")
        print("-" * 80)
        for row in not_linked:
            print(f"   Employee #{row[0]}: {row[1]} ({row[2] or 'sem email'})")

    cursor.close()
    conn.close()
    print("=" * 80)


if __name__ == "__main__":
    try:
        # Verificar situação atual
        verify_links()

        # Confirmar execução
        print("\n⚠️  Este script vai vincular users aos employees por email.")
        resposta = input("Deseja continuar? (s/N): ").strip().lower()

        if resposta != "s":
            print("\n❌ Operação cancelada pelo usuário.")
            sys.exit(0)

        # Executar vinculação
        link_users_to_employees()

        # Verificar resultado
        verify_links()

    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
