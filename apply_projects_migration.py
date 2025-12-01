"""
Script para aplicar migration manualmente - adicionar colunas à tabela projects
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.postgres_helper import connect

def apply_migration():
    """Adiciona colunas faltantes à tabela projects"""
    conn = connect()
    cursor = conn.cursor()
    
    try:
        print("🔧 Aplicando migration: adicionar colunas à tabela projects\n")
        
        # Verificar colunas existentes
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'projects'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Colunas existentes: {', '.join(existing_columns)}\n")
        
        columns_to_add = {
            'title': "VARCHAR(255) NOT NULL DEFAULT ''",
            'description': "TEXT",
            'status': "VARCHAR(50) DEFAULT 'planned'",
            'priority': "VARCHAR(50)",
            'owner': "VARCHAR(255)",
            'start_date': "DATE",
            'end_date': "DATE",
            'created_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            'updated_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        }
        
        added_count = 0
        for col_name, col_def in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE projects ADD COLUMN {col_name} {col_def}"
                    print(f"  ➕ Adicionando coluna: {col_name}")
                    cursor.execute(sql)
                    
                    # Remove default temporário da coluna title
                    if col_name == 'title':
                        cursor.execute("ALTER TABLE projects ALTER COLUMN title DROP DEFAULT")
                    
                    added_count += 1
                except Exception as e:
                    print(f"  ⚠️  Erro ao adicionar {col_name}: {e}")
            else:
                print(f"  ✓ Coluna {col_name} já existe")
        
        conn.commit()
        
        print(f"\n✅ Migration concluída! {added_count} colunas adicionadas.")
        
        # Verificar resultado final
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'projects'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 Estrutura final da tabela projects:")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"  {row[0]:30} {row[1]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro ao aplicar migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()
    
    return True

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
