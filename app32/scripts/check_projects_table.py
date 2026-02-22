"""
Script para verificar estrutura da tabela projects
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.postgres_helper import connect

def check_projects_table():
    """Verifica a estrutura da tabela projects"""
    conn = connect()
    cursor = conn.cursor()
    
    try:
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'projects'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if not exists:
            print("❌ Tabela 'projects' NÃO existe")
            return
        
        print("✅ Tabela 'projects' existe\n")
        
        # Listar todas as colunas
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'projects'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        print("Colunas existentes:")
        print("-" * 80)
        for col in columns:
            col_name, data_type, max_len, nullable, default = col
            type_str = f"{data_type}"
            if max_len:
                type_str += f"({max_len})"
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f"DEFAULT {default}" if default else ""
            print(f"  {col_name:30} {type_str:20} {nullable_str:10} {default_str}")
        
        print(f"\nTotal: {len(columns)} colunas")
        
        # Verificar colunas esperadas
        expected_columns = ['title', 'description', 'status', 'priority', 'owner', 
                          'start_date', 'end_date', 'created_at', 'updated_at']
        existing_column_names = [col[0] for col in columns]
        
        missing = [col for col in expected_columns if col not in existing_column_names]
        
        if missing:
            print(f"\n❌ Colunas faltantes: {', '.join(missing)}")
        else:
            print("\n✅ Todas as colunas esperadas existem")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_projects_table()
