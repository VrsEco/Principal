"""
Script para aplicar migration de vínculo User <-> Employee

Adiciona coluna user_id na tabela employees e cria índices necessários.

Uso:
    python apply_user_employee_link_migration.py

Autor: AI Assistant
Data: 2025-10-22
"""

import os
import sys
from database.postgres_helper import connect as pg_connect


def apply_migration():
    """
    Aplica migration para adicionar user_id em employees
    """
    print("=" * 80)
    print("APLICANDO MIGRATION: USER <-> EMPLOYEE LINK")
    print("=" * 80)
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Verificar se coluna já existe
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'employees' AND column_name = 'user_id'
        """)
        
        if cursor.fetchone():
            print("\n⚠️  Coluna 'user_id' já existe na tabela 'employees'")
            print("   Migration já foi aplicada anteriormente.")
            
            # Verificar índices
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'employees' AND indexname IN ('idx_employees_user', 'idx_employees_user_unique')
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            if 'idx_employees_user' in indexes:
                print("   ✅ Índice 'idx_employees_user' já existe")
            if 'idx_employees_user_unique' in indexes:
                print("   ✅ Índice 'idx_employees_user_unique' já existe")
            
            cursor.close()
            conn.close()
            return True
        
        print("\n📝 Aplicando migration...")
        
        # 1. Adicionar coluna user_id
        print("\n1️⃣  Adicionando coluna user_id...")
        cursor.execute("""
            ALTER TABLE employees 
            ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
        """)
        print("   ✅ Coluna user_id adicionada")
        
        # 2. Criar índice para performance
        print("\n2️⃣  Criando índice idx_employees_user...")
        cursor.execute("""
            CREATE INDEX idx_employees_user ON employees(user_id)
        """)
        print("   ✅ Índice criado")
        
        # 3. Criar índice unique
        print("\n3️⃣  Criando índice único idx_employees_user_unique...")
        cursor.execute("""
            CREATE UNIQUE INDEX idx_employees_user_unique 
            ON employees(user_id) 
            WHERE user_id IS NOT NULL
        """)
        print("   ✅ Índice único criado")
        
        # 4. Adicionar comentário (opcional, não crítico)
        try:
            cursor.execute("""
                COMMENT ON COLUMN employees.user_id IS 
                'FK para users - Permite que colaborador tenha acesso ao sistema'
            """)
            print("\n4️⃣  Comentário adicionado à coluna")
        except Exception as e:
            print(f"\n⚠️  Não foi possível adicionar comentário: {e}")
        
        # Commit
        conn.commit()
        print("\n" + "=" * 80)
        print("✅ MIGRATION APLICADA COM SUCESSO!")
        print("=" * 80)
        
        # Verificar estrutura
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'user_id'
        """)
        
        col_info = cursor.fetchone()
        if col_info:
            print(f"\n📊 Estrutura da coluna:")
            print(f"   Nome: {col_info[0]}")
            print(f"   Tipo: {col_info[1]}")
            print(f"   Nullable: {col_info[2]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao aplicar migration: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        cursor.close()
        conn.close()
        return False


def verify_migration():
    """
    Verifica se a migration foi aplicada corretamente
    """
    print("\n" + "=" * 80)
    print("VERIFICANDO MIGRATION")
    print("=" * 80)
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Verificar coluna
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'user_id'
        """)
        
        col = cursor.fetchone()
        if col:
            print(f"\n✅ Coluna 'user_id' existe:")
            print(f"   - Tipo: {col[1]}")
            print(f"   - Nullable: {col[2]}")
        else:
            print("\n❌ Coluna 'user_id' NÃO existe")
            cursor.close()
            conn.close()
            return False
        
        # Verificar índices
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'employees' 
            AND indexname IN ('idx_employees_user', 'idx_employees_user_unique')
            ORDER BY indexname
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            print(f"\n✅ Índices criados ({len(indexes)}):")
            for idx in indexes:
                print(f"   - {idx[0]}")
        else:
            print("\n⚠️  Índices não encontrados")
        
        # Verificar FK constraint
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'employees' 
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%user_id%'
        """)
        
        fk = cursor.fetchone()
        if fk:
            print(f"\n✅ Foreign Key criada: {fk[0]}")
        else:
            print("\n⚠️  Foreign Key não encontrada (pode ter nome diferente)")
        
        # Contar employees
        cursor.execute("SELECT COUNT(*) FROM employees")
        total_employees = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM employees WHERE user_id IS NOT NULL")
        linked_employees = cursor.fetchone()[0]
        
        print(f"\n📊 Estatísticas:")
        print(f"   Total de colaboradores: {total_employees}")
        print(f"   Colaboradores vinculados a users: {linked_employees}")
        print(f"   Colaboradores sem vínculo: {total_employees - linked_employees}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao verificar migration: {e}")
        cursor.close()
        conn.close()
        return False


if __name__ == '__main__':
    try:
        print("\n🚀 Iniciando aplicação da migration...\n")
        
        # Aplicar migration
        success = apply_migration()
        
        if not success:
            print("\n❌ Falha ao aplicar migration")
            sys.exit(1)
        
        # Verificar
        verify_migration()
        
        # Próximos passos
        print("\n" + "=" * 80)
        print("📋 PRÓXIMOS PASSOS")
        print("=" * 80)
        print("\n1️⃣  Execute o script de vinculação:")
        print("   python link_users_to_employees.py")
        print("\n2️⃣  Teste o My Work Dashboard:")
        print("   http://127.0.0.1:5003/my-work/")
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

