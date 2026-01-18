"""
Script temporário para verificar vinculação User-Employee
"""
from database.postgres_helper import connect as pg_connect

def check_link():
    conn = pg_connect()
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("VERIFICAÇÃO: VINCULAÇÃO USER ↔ EMPLOYEE")
    print("="*80)
    
    # 1. Verificar se coluna user_id existe
    print("\n1️⃣ Verificando estrutura da tabela...")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'employees' AND column_name = 'user_id'
    """)
    
    col = cursor.fetchone()
    if col:
        print(f"   ✅ Coluna 'user_id' existe:")
        print(f"      - Tipo: {col[1]}")
        print(f"      - Nullable: {col[2]}")
    else:
        print("   ❌ Coluna 'user_id' NÃO EXISTE")
        print("   ⚠️  Execute: python apply_user_employee_link_migration.py")
        cursor.close()
        conn.close()
        return False
    
    # 2. Verificar índices
    print("\n2️⃣ Verificando índices...")
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'employees' 
        AND indexname IN ('idx_employees_user', 'idx_employees_user_unique')
    """)
    
    indexes = [row[0] for row in cursor.fetchall()]
    if indexes:
        print(f"   ✅ Índices encontrados: {', '.join(indexes)}")
    else:
        print("   ⚠️  Índices não encontrados")
    
    # 3. Estatísticas de vinculação
    print("\n3️⃣ Estatísticas de vinculação...")
    
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM employees WHERE user_id IS NOT NULL")
    linked_employees = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    print(f"   📊 Total de colaboradores: {total_employees}")
    print(f"   🔗 Colaboradores vinculados: {linked_employees}")
    print(f"   ⛓️  Colaboradores sem vínculo: {total_employees - linked_employees}")
    print(f"   👤 Total de usuários: {total_users}")
    
    # 4. Listar vinculações existentes
    print("\n4️⃣ Vinculações existentes...")
    cursor.execute("""
        SELECT 
            e.id as emp_id,
            e.name as emp_name,
            e.email as emp_email,
            u.id as user_id,
            u.name as user_name,
            u.email as user_email,
            u.role
        FROM employees e
        JOIN users u ON u.id = e.user_id
        WHERE e.user_id IS NOT NULL
        ORDER BY e.name
        LIMIT 10
    """)
    
    links = cursor.fetchall()
    if links:
        print(f"   ✅ {len(links)} vinculações encontradas:")
        for link in links:
            print(f"      Employee #{link[0]}: {link[1]} ({link[2]})")
            print(f"      └─ User #{link[3]}: {link[4]} ({link[5]}) [{link[6]}]")
            print()
    else:
        print("   ⚠️  Nenhuma vinculação encontrada")
        print("   💡 Execute: python link_users_to_employees.py")
    
    # 5. Verificar serviço My Work
    print("\n5️⃣ Testando função get_employee_from_user...")
    try:
        from services.my_work_service import get_employee_from_user
        print("   ✅ Serviço importado com sucesso")
        
        # Testar com primeiro usuário
        cursor.execute("SELECT id, email FROM users LIMIT 1")
        user = cursor.fetchone()
        
        if user:
            employee_id = get_employee_from_user(user[0])
            if employee_id:
                print(f"   ✅ Vinculação funcionando: User #{user[0]} → Employee #{employee_id}")
            else:
                print(f"   ⚠️  User #{user[0]} ({user[1]}) não vinculado a nenhum employee")
        else:
            print("   ⚠️  Nenhum usuário no sistema para testar")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar serviço: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("RESULTADO:")
    if linked_employees > 0:
        print("✅ ESTRUTURA IMPLEMENTADA E FUNCIONANDO")
        print(f"   {linked_employees} colaboradores vinculados a usuários")
    elif col:
        print("⚠️  ESTRUTURA IMPLEMENTADA MAS SEM VINCULAÇÕES")
        print("   Execute: python link_users_to_employees.py")
    else:
        print("❌ ESTRUTURA NÃO IMPLEMENTADA")
        print("   Execute: python apply_user_employee_link_migration.py")
    print("="*80 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        check_link()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()








