import sys
import os
from pathlib import Path
import psycopg2
from sqlalchemy import text

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import connect as connect_helper

def migrate_v2_data():
    print("=" * 70)
    print("MIGRAÇÃO DE DADOS: ui_pages_v2 / ui_elements_v2 (Local -> Cloud)")
    print("=" * 70)

    # 1. Conectar Local
    print("\n💻 Conectando ao LOCAL...")
    try:
        conn_local = psycopg2.connect("postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus")
        cur_local = conn_local.cursor()
        
        # Ler ui_pages_v2
        cur_local.execute("""
            SELECT id, page_code, page_name, template_file, page_route, description, active, created_at, updated_at 
            FROM ui_pages_v2 ORDER BY id
        """)
        pages = cur_local.fetchall()
        print(f"   ✅ Lidos {len(pages)} registros de ui_pages_v2.")

        # Ler ui_elements_v2
        cur_local.execute("""
            SELECT id, page_id, element_code, element_name, element_type, html_id, html_class, description, active, created_at, updated_at 
            FROM ui_elements_v2 ORDER BY id
        """)
        elements = cur_local.fetchall()
        print(f"   ✅ Lidos {len(elements)} registros de ui_elements_v2.")
        
    except Exception as e:
        print(f"❌ Erro lendo do Local: {e}")
        return

    if not pages:
        print("⚠️  Nenhum dado para migrar.")
        return

    # 2. Conectar Cloud e Inserir
    print("\n☁️  Conectando ao CLOUD...")
    os.environ["CLOUD_SQL_CONNECTION_NAME"] = "vrs-eco-478714:southamerica-east1:gestaoversus-db-prod"
    
    try:
        conn_wrapper = connect_helper()
        
        with conn_wrapper.engine.connect() as conn:
            trans = conn.begin()
            try:
                print("   🧹 Limpando tabelas v2 no Cloud...")
                conn.execute(text("TRUNCATE TABLE ui_elements_v2, ui_pages_v2 RESTART IDENTITY CASCADE"))
                
                # Inserir Pages em batch menor
                print(f"   🚀 Inserindo {len(pages)} páginas...")
                batch_size = 50
                for i in range(0, len(pages), batch_size):
                    batch = pages[i:i+batch_size]
                    pages_data = [
                        {
                            "id": p[0], "page_code": p[1], "page_name": p[2], 
                            "template_file": p[3], "page_route": p[4], "description": p[5], 
                            "active": p[6], "created_at": p[7], "updated_at": p[8]
                        }
                        for p in batch
                    ]
                    
                    conn.execute(
                        text("""
                            INSERT INTO ui_pages_v2 
                            (id, page_code, page_name, template_file, page_route, description, active, created_at, updated_at)
                            VALUES (:id, :page_code, :page_name, :template_file, :page_route, :description, :active, :created_at, :updated_at)
                        """),
                        pages_data
                    )
                    print(f"      Batch {i//batch_size + 1}/{(len(pages)-1)//batch_size + 1}")
                
                # Inserir Elements em batch menor
                print(f"   🚀 Inserindo {len(elements)} elementos...")
                batch_size = 100
                for i in range(0, len(elements), batch_size):
                    batch = elements[i:i+batch_size]
                    elements_data = [
                        {
                            "id": e[0], "page_id": e[1], "element_code": e[2], 
                            "element_name": e[3], "element_type": e[4], "html_id": e[5], 
                            "html_class": e[6], "description": e[7], "active": e[8], 
                            "created_at": e[9], "updated_at": e[10]
                        }
                        for e in batch
                    ]
                    
                    conn.execute(
                        text("""
                            INSERT INTO ui_elements_v2 
                            (id, page_id, element_code, element_name, element_type, html_id, html_class, description, active, created_at, updated_at)
                            VALUES (:id, :page_id, :element_code, :element_name, :element_type, :html_id, :html_class, :description, :active, :created_at, :updated_at)
                        """),
                        elements_data
                    )
                    print(f"      Batch {i//batch_size + 1}/{(len(elements)-1)//batch_size + 1}")
                
                # Atualizar sequências
                print("   🔧 Atualizando sequências...")
                conn.execute(text("SELECT setval('ui_pages_v2_id_seq', (SELECT MAX(id) FROM ui_pages_v2))"))
                conn.execute(text("SELECT setval('ui_elements_v2_id_seq', (SELECT MAX(id) FROM ui_elements_v2))"))
                
                trans.commit()
                print("\n✅ Migração concluída com sucesso!")
                
            except Exception as e:
                trans.rollback()
                raise e
        
    except Exception as e:
        print(f"❌ Erro gravando no Cloud: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_v2_data()
