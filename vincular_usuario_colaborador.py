"""
Script para vincular Usuário a Colaborador Existente
Cenário: Empresa e Colaborador já existem, precisa criar User e vincular
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.role import Role

def vincular_usuario_a_colaborador():
    """
    Vincula um novo usuário a um colaborador existente
    """
    with app.app_context():
        print("\n" + "="*60)
        print("VINCULAR USUÁRIO A COLABORADOR EXISTENTE")
        print("="*60)
        
        # Passo 1: Buscar a empresa
        print("\n1. Buscando empresa 'Empresa teste 123'...")
        company = Company.query.filter_by(name='Empresa teste 123').first()
        
        if not company:
            print("   ❌ Empresa não encontrada!")
            print("   Criando empresa...")
            company = Company(
                name='Empresa teste 123',
                legal_name='Empresa Teste 123 Ltda'
            )
            db.session.add(company)
            db.session.commit()
            print(f"   ✅ Empresa criada: ID {company.id}")
        else:
            print(f"   ✅ Empresa encontrada: ID {company.id}")
        
        # Passo 2: Buscar o colaborador
        print("\n2. Buscando colaborador da empresa...")
        employee = Employee.query.filter_by(
            company_id=company.id,
            user_id=None  # Colaborador sem usuário vinculado
        ).first()
        
        if not employee:
            print("   ❌ Colaborador sem usuário não encontrado!")
            print("   Criando colaborador de exemplo...")
            employee = Employee(
                company_id=company.id,
                name='Colaborador Teste',
                email='colaborador@teste.com',
                status='active'
            )
            db.session.add(employee)
            db.session.commit()
            print(f"   ✅ Colaborador criado: ID {employee.id}")
        else:
            print(f"   ✅ Colaborador encontrado: ID {employee.id}")
            print(f"      Nome: {employee.name}")
            print(f"      Email: {employee.email}")
        
        # Passo 3: Criar o usuário
        print("\n3. Criando usuário...")
        
        email = input("   Digite o email do usuário: ").strip()
        
        # Verificar se email já existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"   ⚠ Usuário já existe: ID {existing_user.id}")
            user = existing_user
        else:
            name = input("   Digite o nome do usuário: ").strip()
            password = input("   Digite a senha: ").strip()
            role = input("   Digite o role (admin/consultant/client) [client]: ").strip() or 'client'
            
            user = User(
                name=name,
                email=email,
                role=role
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"   ✅ Usuário criado: ID {user.id}")
        
        # Passo 4: Vincular usuário ao colaborador
        print("\n4. Vinculando usuário ao colaborador...")
        employee.user_id = user.id
        employee.name = user.name  # Atualizar nome se necessário
        employee.email = user.email  # Atualizar email se necessário
        db.session.commit()
        print(f"   ✅ Vínculo criado!")
        print(f"      Employee ID {employee.id} → User ID {user.id}")
        
        # Passo 5: Configurar permissões (Role)
        print("\n5. Configurando permissões...")
        
        # Buscar ou criar role
        role_title = input("   Digite o cargo (ex: Administrador, Gerente) [Administrador]: ").strip() or 'Administrador'
        
        role_obj = Role.query.filter_by(
            company_id=company.id,
            title=role_title
        ).first()
        
        if not role_obj:
            print(f"   Criando cargo '{role_title}'...")
            
            # Definir permissões padrão
            permissions = {
                'financial': 'admin',
                'tasks': 'edit',
                'reports': 'view',
                'users': 'admin'
            }
            
            role_obj = Role(
                company_id=company.id,
                title=role_title,
                permissions=permissions
            )
            db.session.add(role_obj)
            db.session.commit()
            print(f"   ✅ Cargo criado: ID {role_obj.id}")
        else:
            print(f"   ✅ Cargo encontrado: ID {role_obj.id}")
        
        # Vincular role ao employee
        employee.role_id = role_obj.id
        db.session.commit()
        print(f"   ✅ Cargo vinculado ao colaborador")
        
        # Resumo final
        print("\n" + "="*60)
        print("✅ VÍNCULO CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print(f"\n📊 Resumo:")
        print(f"   User ID: {user.id} ({user.email})")
        print(f"   Company ID: {company.id} ({company.name})")
        print(f"   Employee ID: {employee.id} ({employee.name})")
        print(f"   Role ID: {role_obj.id} ({role_obj.title})")
        print(f"\n   Permissões: {role_obj.permissions}")
        
        print("\n💡 Agora o usuário pode:")
        print("   1. Fazer login com o email cadastrado")
        print("   2. Acessar a empresa 'Empresa teste 123'")
        print(f"   3. Ter permissões de '{role_obj.title}'")


def editar_permissoes_usuario():
    """
    Edita as permissões de um usuário existente
    """
    with app.app_context():
        print("\n" + "="*60)
        print("EDITAR PERMISSÕES DE USUÁRIO")
        print("="*60)
        
        # Buscar usuário
        email = input("\nDigite o email do usuário: ").strip()
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ Usuário não encontrado: {email}")
            return
        
        print(f"\n✅ Usuário encontrado: {user.name} (ID {user.id})")
        
        # Buscar employees deste usuário
        employees = Employee.query.filter_by(user_id=user.id).all()
        
        if not employees:
            print("⚠ Este usuário não está vinculado a nenhuma empresa!")
            return
        
        print(f"\n📋 Empresas vinculadas:")
        for i, emp in enumerate(employees, 1):
            company = Company.query.get(emp.company_id)
            role = Role.query.get(emp.role_id) if emp.role_id else None
            print(f"   {i}. {company.name} - Cargo: {role.title if role else 'Sem cargo'}")
        
        # Selecionar empresa
        choice = int(input("\nEscolha a empresa (número): ")) - 1
        employee = employees[choice]
        company = Company.query.get(employee.company_id)
        
        print(f"\n🏢 Editando permissões em: {company.name}")
        
        # Buscar ou criar role
        if employee.role_id:
            role = Role.query.get(employee.role_id)
            print(f"\n📝 Cargo atual: {role.title}")
            print(f"   Permissões atuais: {role.permissions}")
        else:
            print("\n⚠ Colaborador sem cargo definido")
            role_title = input("Digite o nome do cargo: ").strip()
            role = Role(
                company_id=company.id,
                title=role_title,
                permissions={}
            )
            db.session.add(role)
            db.session.commit()
            employee.role_id = role.id
            db.session.commit()
        
        # Editar permissões
        print("\n🔧 Configurar permissões:")
        print("   Opções: admin, edit, view, none")
        
        permissions = {}
        
        modules = ['financial', 'tasks', 'reports', 'users', 'projects', 'meetings']
        
        for module in modules:
            current = role.permissions.get(module, 'none') if role.permissions else 'none'
            perm = input(f"   {module.capitalize()} [{current}]: ").strip() or current
            if perm != 'none':
                permissions[module] = perm
        
        # Atualizar
        role.permissions = permissions
        db.session.commit()
        
        print("\n✅ Permissões atualizadas!")
        print(f"   {permissions}")


def menu():
    """Menu interativo"""
    print("\n" + "="*60)
    print("GERENCIAMENTO DE USUÁRIOS E PERMISSÕES")
    print("="*60)
    print("\n1. Vincular novo usuário a colaborador existente")
    print("2. Editar permissões de usuário")
    print("0. Sair")
    
    choice = input("\nEscolha uma opção: ")
    
    if choice == '1':
        vincular_usuario_a_colaborador()
    elif choice == '2':
        editar_permissoes_usuario()
    elif choice == '0':
        print("\nAté logo!")
        return False
    else:
        print("\n⚠ Opção inválida!")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Sistema de Gerenciamento de Usuários")
    
    continuar = True
    while continuar:
        continuar = menu()
    
    print("\n✅ Concluído!")
