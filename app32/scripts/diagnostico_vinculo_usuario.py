"""
Script de Diagnóstico e Correção do Vínculo Usuário-Colaborador
Verifica e corrige o vínculo entre o usuário mff2000@gmail.com e seu colaborador
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company

def diagnosticar_vinculo():
    """
    Diagnostica o vínculo entre usuário e colaborador
    """
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
            print(f"   💡 Você precisa criar um usuário primeiro!")
            return False
        
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
                company = Company.query.get(emp.company_id) if emp.company_id else None
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
                company = Company.query.get(emp.company_id) if emp.company_id else None
                print(f"      - Employee ID: {emp.id}")
                print(f"        Nome: {emp.name}")
                print(f"        Email: {emp.email}")
                print(f"        Empresa: {company.name if company else 'N/A'} (ID: {emp.company_id})")
                print(f"        Status: {emp.status}")
                print(f"        user_id: {emp.user_id} {'✅ VINCULADO' if emp.user_id else '❌ NÃO VINCULADO'}")
        else:
            print(f"   ❌ Nenhum colaborador encontrado com email: {email}")
        
        # 4. Verificar inconsistências
        print(f"\n4️⃣  Verificando inconsistências...")
        
        problemas = []
        
        # Colaboradores com email mas sem user_id
        employees_sem_vinculo = [e for e in employees_by_email if not e.user_id]
        if employees_sem_vinculo:
            problemas.append({
                'tipo': 'sem_vinculo',
                'descricao': f'{len(employees_sem_vinculo)} colaborador(es) com email {email} mas sem user_id vinculado',
                'employees': employees_sem_vinculo
            })
        
        # Colaboradores com user_id diferente
        employees_vinculo_errado = [e for e in employees_by_email if e.user_id and e.user_id != user.id]
        if employees_vinculo_errado:
            problemas.append({
                'tipo': 'vinculo_errado',
                'descricao': f'{len(employees_vinculo_errado)} colaborador(es) com email {email} mas vinculado a outro usuário',
                'employees': employees_vinculo_errado
            })
        
        if problemas:
            print(f"   ⚠️  Encontrados {len(problemas)} problema(s):")
            for i, prob in enumerate(problemas, 1):
                print(f"      {i}. {prob['descricao']}")
        else:
            print(f"   ✅ Nenhuma inconsistência encontrada!")
        
        # 5. Resumo e recomendações
        print(f"\n" + "="*80)
        print("📊 RESUMO")
        print("="*80)
        print(f"Usuário: {user.name} ({user.email}) - ID: {user.id}")
        print(f"Colaboradores vinculados (user_id): {len(employees_by_user_id)}")
        print(f"Colaboradores com mesmo email: {len(employees_by_email)}")
        print(f"Problemas encontrados: {len(problemas)}")
        
        if problemas:
            print(f"\n💡 RECOMENDAÇÕES:")
            for prob in problemas:
                if prob['tipo'] == 'sem_vinculo':
                    print(f"\n   ⚠️  Colaboradores sem vínculo encontrados!")
                    print(f"   Execute a função corrigir_vinculo() para vincular automaticamente.")
                elif prob['tipo'] == 'vinculo_errado':
                    print(f"\n   ⚠️  Colaboradores vinculados a outro usuário!")
                    print(f"   Verifique manualmente antes de corrigir.")
        
        return {
            'user': user,
            'employees_by_user_id': employees_by_user_id,
            'employees_by_email': employees_by_email,
            'problemas': problemas
        }


def corrigir_vinculo(email="mff2000@gmail.com", auto_confirm=False):
    """
    Corrige o vínculo entre usuário e colaboradores
    """
    with app.app_context():
        print("\n" + "="*80)
        print("🔧 CORREÇÃO: Vínculo Usuário-Colaborador")
        print("="*80)
        
        # Buscar usuário
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Usuário não encontrado: {email}")
            return False
        
        # Buscar colaboradores sem vínculo
        employees_sem_vinculo = Employee.query.filter(
            db.func.lower(Employee.email) == email.lower(),
            Employee.user_id.is_(None)
        ).all()
        
        if not employees_sem_vinculo:
            print(f"✅ Todos os colaboradores com email {email} já estão vinculados!")
            return True
        
        print(f"\n📋 Colaboradores a serem vinculados:")
        for emp in employees_sem_vinculo:
            company = Company.query.get(emp.company_id) if emp.company_id else None
            print(f"   - {emp.name} (ID: {emp.id})")
            print(f"     Empresa: {company.name if company else 'N/A'}")
            print(f"     Status: {emp.status}")
        
        if not auto_confirm:
            resposta = input(f"\n❓ Deseja vincular {len(employees_sem_vinculo)} colaborador(es) ao usuário {user.name}? (s/n): ")
            if resposta.lower() != 's':
                print("❌ Operação cancelada.")
                return False
        
        # Vincular
        print(f"\n🔗 Vinculando colaboradores...")
        for emp in employees_sem_vinculo:
            emp.user_id = user.id
            print(f"   ✅ Employee #{emp.id} vinculado ao User #{user.id}")
        
        db.session.commit()
        
        print(f"\n✅ Vínculo corrigido com sucesso!")
        print(f"   {len(employees_sem_vinculo)} colaborador(es) vinculado(s) ao usuário {user.name}")
        
        return True


def menu():
    """Menu interativo"""
    print("\n" + "="*80)
    print("🔧 FERRAMENTA DE DIAGNÓSTICO E CORREÇÃO")
    print("   Vínculo Usuário-Colaborador")
    print("="*80)
    print("\n1. Diagnosticar vínculo (mff2000@gmail.com)")
    print("2. Corrigir vínculo (mff2000@gmail.com)")
    print("3. Diagnosticar outro email")
    print("4. Corrigir outro email")
    print("0. Sair")
    
    escolha = input("\n❓ Escolha uma opção: ")
    
    if escolha == '1':
        diagnosticar_vinculo()
    elif escolha == '2':
        corrigir_vinculo()
    elif escolha == '3':
        email = input("Digite o email: ")
        # Adaptar função para aceitar email customizado
        print("⚠️  Funcionalidade em desenvolvimento")
    elif escolha == '4':
        email = input("Digite o email: ")
        corrigir_vinculo(email)
    elif escolha == '0':
        print("\n👋 Até logo!")
        return False
    else:
        print("\n❌ Opção inválida!")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Sistema de Diagnóstico e Correção de Vínculos")
    
    continuar = True
    while continuar:
        continuar = menu()
    
    print("\n✅ Concluído!")
