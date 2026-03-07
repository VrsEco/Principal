"""Script para aplicar a migration de dependências entre atividades."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from urllib.parse import quote_plus
import psycopg2

password = quote_plus('*Paraiso1978')
conn_str = f'postgresql://postgres:{password}@localhost:5432/bdversusv2'
print(f'Conectando em: postgresql://postgres:***@localhost:5432/bdversusv2')

try:
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    cur = conn.cursor()

    sql_path = os.path.join(os.path.dirname(__file__), '..', 'migrations', '20260307_create_project_task_dependencies.sql')
    sql = open(sql_path, 'r', encoding='utf-8').read()
    cur.execute(sql)
    conn.commit()
    print('✅ Tabela project_task_dependencies criada com sucesso!')

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'project_task_dependencies'")
    result = cur.fetchone()
    print(f'Verificação: tabela encontrada = {result}')
    conn.close()

except Exception as e:
    print(f'❌ Erro: {e}')
    sys.exit(1)
