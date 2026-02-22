"""
Script Ultra-Simplificado para Verificar Atividades
Apenas conta quantas atividades existem
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company

def verificar_atividades(email="mff2000@gmail.com"):
    """
    Verifica atividades do usuário de forma simplificada
    """
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 VERIFICAÇÃO DE ATIVIDADES - MY WORK")
        print("="*80)
        
        # 1. Buscar usuário
        print(f"\n1️⃣  Buscando usuário: {email}")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"   ❌ Usuário não encontrado: {email}")
            return
        
        print(f"   ✅ Usuário: {user.name} (ID: {user.id})")
        
        # 2. Buscar colaboradores vinculados
        print(f"\n2️⃣  Buscando colaboradores vinculados...")
        employees = Employee.query.filter_by(user_id=user.id).all()
        
        if not employees:
            print(f"   ❌ Nenhum colaborador vinculado ao usuário")
            return
        
        print(f"   ✅ Encontrados {len(employees)} colaborador(es):")
        employee_ids = []
        for emp in employees:
            company = db.session.get(Company, emp.company_id) if emp.company_id else None
            print(f"      - {emp.name} (ID: {emp.id})")
            print(f"        Empresa: {company.name if company else 'N/A'}")
            employee_ids.append(emp.id)
        
        # 3. Contar atividades usando SQL direto
        print(f"\n3️⃣  Contando atividades...")
        
        # Atividades de projeto
        result_proj = db.session.execute(
            db.text("""
                SELECT COUNT(*) 
                FROM project_activities 
                WHERE who_executor_id IN :ids 
                   OR who_responsible_id IN :ids
            """),
            {"ids": tuple(employee_ids)}
        )
        count_proj = result_proj.scalar()
        
        # Instâncias de processo
        result_proc = db.session.execute(
            db.text("""
                SELECT COUNT(*) 
                FROM process_instances 
                WHERE executor_id IN :ids 
                   OR responsible_id IN :ids
            """),
            {"ids": tuple(employee_ids)}
        )
        count_proc = result_proc.scalar()
        
        # 4. Estatísticas
        print(f"\n" + "="*80)
        print("📊 ESTATÍSTICAS")
        print("="*80)
        print(f"Total de colaboradores: {len(employees)}")
        print(f"Atividades de projeto: {count_proj}")
        print(f"Instâncias de processo: {count_proc}")
        print(f"Total de atividades: {count_proj + count_proc}")
        
        if count_proj + count_proc == 0:
            print(f"\n⚠️  ATENÇÃO:")
            print(f"   Não foram encontradas atividades para este usuário.")
            print(f"\n💡 SUGESTÃO:")
            print(f"   1. Acesse um projeto na interface")
            print(f"   2. Crie uma atividade de teste")
            print(f"   3. Defina '{user.name}' como executor ou responsável")
            print(f"   4. Verifique se aparece no My Work")
        else:
            print(f"\n✅ CONCLUSÃO:")
            print(f"   O usuário possui atividades cadastradas.")
            print(f"   Se não aparecem no My Work, verifique:")
            print(f"   1. Filtros de empresa selecionados")
            print(f"   2. Filtros de data/status")
            print(f"   3. Logs do navegador (F12 → Console)")

if __name__ == "__main__":
    print("\n🚀 Verificação de Atividades - My Work")
    
    email = sys.argv[1] if len(sys.argv) > 1 else "mff2000@gmail.com"
    
    try:
        verificar_atividades(email)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Verificação concluída!")
