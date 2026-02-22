"""
Script Simples de Diagnóstico - Execução Direta
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company

with app.app_context():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO: Vínculo Usuário-Colaborador")
    print("="*80)
    
    email = "mff2000@gmail.com"
    
    # 1. Buscar usuário
    print(f"\n1️⃣  Buscando usuário com email: {email}")
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"   ❌ Usuário não encontrado com email: {email}")
        print(f"   💡 Listando todos os usuários:")
        users = User.query.all()
        for u in users:
            print(f"      - {u.name} ({u.email}) - ID: {u.id}")
    else:
        print(f"   ✅ Usuário encontrado:")
        print(f"      ID: {user.id}")
        print(f"      Nome: {user.name}")
        print(f"      Email: {user.email}")
        print(f"      Role: {user.role}")
        
        # 2. Buscar colaboradores vinculados por user_id
        print(f"\n2️⃣  Buscando colaboradores vinculados por user_id = {user.id}")
        employees_by_user_id = Employee.query.filter_by(user_id=user.id).all()
        
        if employees_by_user_id:
            print(f"   ✅ Encontrados {len(employees_by_user_id)} colaborador(es) vinculado(s):")
            for emp in employees_by_user_id:
                company = db.session.get(Company, emp.company_id) if emp.company_id else None
                print(f"      - Employee ID: {emp.id}")
                print(f"        Nome: {emp.name}")
                print(f"        Email: {emp.email}")
                print(f"        Empresa: {company.name if company else 'N/A'} (ID: {emp.company_id})")
                print(f"        Status: {emp.status}")
        else:
            print(f"   ⚠️  Nenhum colaborador vinculado por user_id")
        
        # 3. Buscar colaboradores por email (fallback)
        print(f"\n3️⃣  Buscando colaboradores por email: {email}")
        employees_by_email = Employee.query.filter(
            db.func.lower(Employee.email) == email.lower()
        ).all()
        
        if employees_by_email:
            print(f"   ✅ Encontrados {len(employees_by_email)} colaborador(es) com este email:")
            for emp in employees_by_email:
                company = db.session.get(Company, emp.company_id) if emp.company_id else None
                print(f"      - Employee ID: {emp.id}")
                print(f"        Nome: {emp.name}")
                print(f"        Email: {emp.email}")
                print(f"        Empresa: {company.name if company else 'N/A'} (ID: {emp.company_id})")
                print(f"        Status: {emp.status}")
                print(f"        user_id: {emp.user_id} {'✅ VINCULADO' if emp.user_id else '❌ NÃO VINCULADO'}")
        else:
            print(f"   ❌ Nenhum colaborador encontrado com email: {email}")
            print(f"\n   💡 Listando colaboradores com emails similares:")
            all_employees = Employee.query.filter(Employee.email.ilike(f"%{email.split('@')[0]}%")).all()
            for emp in all_employees:
                print(f"      - {emp.name} ({emp.email}) - ID: {emp.id}, user_id: {emp.user_id}")
        
        # 4. Resumo
        print(f"\n" + "="*80)
        print("📊 RESUMO")
        print("="*80)
        print(f"Usuário: {user.name} ({user.email}) - ID: {user.id}")
        print(f"Colaboradores vinculados (user_id): {len(employees_by_user_id)}")
        print(f"Colaboradores com mesmo email: {len(employees_by_email)}")
        
        # Verificar se precisa correção
        employees_sem_vinculo = [e for e in employees_by_email if not e.user_id]
        if employees_sem_vinculo:
            print(f"\n⚠️  AÇÃO NECESSÁRIA:")
            print(f"   {len(employees_sem_vinculo)} colaborador(es) com email {email} mas sem user_id vinculado")
            print(f"\n   Para corrigir, execute:")
            print(f"   python corrigir_vinculo_usuario.py")

print("\n✅ Diagnóstico concluído!")
