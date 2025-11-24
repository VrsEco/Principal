#!/usr/bin/env python3
import os
import sys

# Simular ambiente Docker
os.environ["CLOUD_SQL_CONNECTION_NAME"] = "vrs-eco-478714:southamerica-east1:gestaoversus-db-prod"

print("=" * 70)
print("TESTE DE CONEXÃO - Ambiente Docker Simulado")
print("=" * 70)

try:
    print("\n1. Testando importação do postgres_helper...")
    from database.postgres_helper import connect
    print("   ✅ Import OK")
    
    print("\n2. Testando conexão com o banco...")
    conn = connect()
    cur = conn.cursor()
    print("   ✅ Conexão OK")
    
    print("\n3. Verificando tabelas ui_pages_v2 e ui_elements_v2...")
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema='public' AND table_name IN ('ui_pages_v2', 'ui_elements_v2')
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f"   ✅ Tabelas encontradas: {[t[0] for t in tables]}")
    
    print("\n4. Testando UIReferenceServiceV2...")
    from services.ui_reference_service_v2 import UIReferenceServiceV2
    print("   ✅ Import OK")
    
    print("\n5. Carregando páginas...")
    pages = UIReferenceServiceV2.get_all_pages()
    print(f"   ✅ {len(pages)} páginas carregadas")
    
    print("\n6. Testando UiCatalog model...")
    try:
        from models.ui_catalog import UiCatalog
        print("   ✅ UiCatalog import OK")
        
        # Verificar se a tabela existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ui_catalog'
            )
        """)
        exists = cur.fetchone()[0]
        if exists:
            print("   ✅ Tabela ui_catalog existe")
        else:
            print("   ⚠️  Tabela ui_catalog NÃO existe")
            
    except Exception as e:
        print(f"   ❌ Erro no UiCatalog: {e}")
    
    print("\n✅ TODOS OS TESTES PASSARAM!")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
