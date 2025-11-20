# -*- coding: utf-8 -*-
"""
Verificar se existem rotinas no banco para o processo 38
"""
import sqlite3

conn = sqlite3.connect("instance/pevapp22.db")
cursor = conn.cursor()
cursor.row_factory = sqlite3.Row

print("\n" + "=" * 70)
print("VERIFICANDO ROTINAS NO BANCO DE DADOS")
print("=" * 70 + "\n")

# Verificar estrutura da tabela routines
print("1. Estrutura da tabela routines:")
cursor.execute("PRAGMA table_info(routines)")
columns = cursor.fetchall()
for col in columns:
    print(f"   - {col['name']} ({col['type']})")

# Buscar rotinas do processo 38
print("\n2. Rotinas do processo 38:")
cursor.execute("SELECT * FROM routines WHERE process_id = 38")
routines = cursor.fetchall()

if routines:
    print(f"   Encontradas {len(routines)} rotinas:")
    for r in routines:
        print(f"\n   ID: {r['id']}")
        print(f"   Nome: {r['name']}")
        print(f"   Process ID: {r['process_id']}")
        print(f"   Agendamento: {r.get('schedule_type', 'N/A')}")
        print(f"   Prazo Dias: {r.get('deadline_days', 0)}")
        print(f"   Prazo Horas: {r.get('deadline_hours', 0)}")

        # Buscar colaboradores
        cursor.execute(
            """
            SELECT rc.*, e.name as employee_name 
            FROM routine_collaborators rc
            LEFT JOIN employees e ON rc.employee_id = e.id
            WHERE rc.routine_id = ?
        """,
            (r["id"],),
        )
        collabs = cursor.fetchall()
        print(f"   Colaboradores: {len(collabs)}")
        for c in collabs:
            print(f"     - {c['employee_name']}: {c['hours_used']}h")
else:
    print("   ❌ Nenhuma rotina encontrada para processo 38")

    # Verificar se existem rotinas em geral
    cursor.execute("SELECT COUNT(*) as total FROM routines")
    total = cursor.fetchone()["total"]
    print(f"\n   Total de rotinas no banco: {total}")

    if total > 0:
        cursor.execute("SELECT id, name, process_id FROM routines LIMIT 5")
        print("\n   Exemplo de rotinas existentes:")
        for r in cursor.fetchall():
            print(f"     ID {r['id']}: {r['name']} (processo {r['process_id']})")

conn.close()
print("\n" + "=" * 70)
