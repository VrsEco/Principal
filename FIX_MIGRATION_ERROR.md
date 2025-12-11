# ============================================================================
# ERRO: Tabela project_activities não existe!
# ============================================================================
# 
# A migration falhou porque a tabela project_activities ainda não foi criada.
# Precisamos executar PRIMEIRO a migration 20251128_normalize_my_work.sql
#
# ============================================================================

# PASSO 1: Verificar se a tabela existe
# ============================================================================
docker exec -it app31_app_prod flask shell

from database.postgres_helper import connect as pg_connect
conn = pg_connect()
cursor = conn.cursor()

# Verificar se project_activities existe
cursor.execute("""
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'project_activities'
    )
""")
exists = cursor.fetchone()[0]
print(f"Tabela project_activities existe? {exists}")
conn.close()
exit()

# ============================================================================
# PASSO 2: Se NÃO existe, executar migration base primeiro
# ============================================================================
docker exec -it app31_app_prod flask shell

from database.postgres_helper import connect as pg_connect
conn = pg_connect()
cursor = conn.cursor()

# Ler e executar migration base
with open('migrations/20251128_normalize_my_work.sql', 'r', encoding='utf-8') as f:
    base_sql = f.read()

cursor.execute(base_sql)
conn.commit()
print("✅ Migration base executada!")
conn.close()
exit()

# ============================================================================
# PASSO 3: Agora executar a migration de collaborators
# ============================================================================
# (Usar os comandos do arquivo EXECUTAR_MIGRATION_FLASK.md)
