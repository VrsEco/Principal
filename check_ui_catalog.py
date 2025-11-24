#!/usr/bin/env python3
import os
os.environ["CLOUD_SQL_CONNECTION_NAME"] = "vrs-eco-478714:southamerica-east1:gestaoversus-db-prod"

from database.postgres_helper import connect

conn = connect()
cur = conn.cursor()

print("Verificando tabela ui_catalog...")
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'ui_catalog'
    )
""")
exists = cur.fetchone()[0]

if exists:
    print("✅ Tabela ui_catalog existe")
    cur.execute("SELECT COUNT(*) FROM ui_catalog")
    count = cur.fetchone()[0]
    print(f"   Registros: {count}")
else:
    print("❌ Tabela ui_catalog NÃO existe no Cloud")
    print("\nEssa tabela precisa ser criada!")
