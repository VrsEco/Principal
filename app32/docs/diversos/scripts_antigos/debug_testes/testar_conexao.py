#!/usr/bin/env python3
"""
Script para testar a conexão do Flask com o banco
Executar DENTRO do container Docker
"""

import psycopg2
import os

# Pegar DATABASE_URL do ambiente (como o Flask faz)
database_url = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:versus@localhost:5432/bd_app_versus"
)

print("=" * 70)
print("  TESTANDO CONEXÃO DO FLASK COM POSTGRESQL")
print("=" * 70)
print()
print(f"DATABASE_URL: {database_url}")
print()

try:
    # Conectar
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Verificar banco e schema
    cursor.execute("SELECT current_database(), current_schema()")
    db, schema = cursor.fetchone()
    print(f"✅ Conectado ao banco: {db}")
    print(f"✅ Schema: {schema}")
    print()

    # Listar tabelas de alignment
    cursor.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'plan_alignment%'
        ORDER BY table_name
    """
    )

    tables = cursor.fetchall()

    if tables:
        print(f"✅ Encontradas {len(tables)} tabelas:")
        for (table_name,) in tables:
            print(f"   - {table_name}")

        print()
        print("🧪 Testando INSERT...")

        # Testar insert (será removido depois)
        cursor.execute(
            """
            INSERT INTO plan_alignment_members 
            (plan_id, name, role, motivation, commitment, risk)
            VALUES (8, 'TESTE', 'Teste', 'Teste', 'Teste', 'Teste')
            RETURNING id
        """
        )

        test_id = cursor.fetchone()[0]
        print(f"   ✅ INSERT funcionou! ID: {test_id}")

        # Remover teste
        cursor.execute("DELETE FROM plan_alignment_members WHERE id = %s", (test_id,))
        conn.commit()
        print(f"   ✅ Teste removido!")

    else:
        print("❌ NENHUMA tabela de alignment encontrada!")
        print()
        print("As tabelas NÃO EXISTEM neste banco/schema!")

    cursor.close()
    conn.close()

    print()
    print("=" * 70)
    if tables:
        print("✅ CONEXÃO OK E TABELAS EXISTEM!")
    else:
        print("❌ TABELAS NÃO EXISTEM NESTE BANCO!")
    print("=" * 70)

except Exception as e:
    print()
    print("=" * 70)
    print("❌ ERRO!")
    print("=" * 70)
    print(f"Erro: {e}")
    print()
    import traceback

    traceback.print_exc()
