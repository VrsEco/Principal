"""
Exemplos Práticos de Uso do Sistema de Usuários e Colaboradores
Execute este arquivo para testar as funcionalidades
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from services.user_employee_service import UserEmployeeService
from models.user import User
from models.company import Company
from models.employee import Employee

def exemplo_1_cadastro_completo():
    """Exemplo 1: Cadastrar novo usuário com empresa"""
    print("\n" + "="*60)
    print("EXEMPLO 1: Cadastro Completo (User + Company + Employee)")
    print("="*60)
    
    with app.app_context():
        result = UserEmployeeService.create_user_with_company(
            user_data={
                'name': 'Maria Silva',
                'email': 'maria@exemplo.com',
                'password': 'senha123',
                'role': 'client'
            },
            company_data={
                'name': 'Exemplo Tech Ltda',
                'cnpj': '12.345.678/0001-90',
                'segment': 'Tecnologia',
                'city': 'São Paulo',
                'state': 'SP'
            },
            employee_data={
                'phone': '(11) 98765-4321',
                'department': 'Diretoria'
            }
        )
        
        if result['success']:
            print("\n✅ Cadastro realizado com sucesso!")
            print(f"   User ID: {result['user']['id']}")
            print(f"   Company ID: {result['company']['id']}")
            print(f"   Employee ID: {result['employee']['id']}")
        else:
            print(f"\n❌ Erro: {result['error']}")


def exemplo_2_adicionar_empresa():
    """Exemplo 2: Adicionar usuário existente em outra empresa"""
    print("\n" + "="*60)
    print("EXEMPLO 2: Adicionar Usuário em Outra Empresa")
    print("="*60)
    
    with app.app_context():
        # Buscar um usuário existente
        user = User.query.first()
        
        if not user:
            print("⚠ Nenhum usuário encontrado. Execute o Exemplo 1 primeiro.")
            return
        
        # Buscar ou criar uma segunda empresa
        company = Company.query.filter(Company.id != user.employees[0].company_id if user.employees else 0).first()
        
        if not company:
            print("   Criando segunda empresa para teste...")
            from models import db
            company = Company(
                name="Consultoria ABC",
                cnpj="98.765.432/0001-10"
            )
            db.session.add(company)
            db.session.commit()
        
        print(f"\n   Adicionando {user.name} na empresa {company.name}...")
        
        result = UserEmployeeService.add_employee_to_company(
            user_id=user.id,
            company_id=company.id,
            employee_data={
                'department': 'Consultoria'
            }
        )
        
        if result['success']:
            print("\n✅ Usuário adicionado com sucesso!")
            print(f"   Employee ID: {result['employee']['id']}")
        else:
            print(f"\n❌ Erro: {result['error']}")


def exemplo_3_listar_empresas():
    """Exemplo 3: Listar empresas de um usuário"""
    print("\n" + "="*60)
    print("EXEMPLO 3: Listar Empresas do Usuário")
    print("="*60)
    
    with app.app_context():
        user = User.query.first()
        
        if not user:
            print("⚠ Nenhum usuário encontrado.")
            return
        
        print(f"\n   Buscando empresas de: {user.name}")
        
        companies = UserEmployeeService.get_user_companies(user.id)
        
        print(f"\n✅ Encontradas {len(companies)} empresa(s):")
        for item in companies:
            print(f"   - {item['company']['name']} (Employee ID: {item['employee_id']})")


def exemplo_4_minhas_atividades():
    """Exemplo 4: Buscar atividades agregadas"""
    print("\n" + "="*60)
    print("EXEMPLO 4: Minhas Atividades (Agregadas)")
    print("="*60)
    
    with app.app_context():
        user = User.query.first()
        
        if not user:
            print("⚠ Nenhum usuário encontrado.")
            return
        
        print(f"\n   Buscando atividades de: {user.name}")
        
        activities = UserEmployeeService.get_user_activities(user.id)
        
        print(f"\n✅ Encontradas {len(activities)} atividade(s):")
        for item in activities:
            task = item['task']
            print(f"   - {task['what']}")
            print(f"     Empresa: {item['company_id']} | Status: {task['status']}")


def exemplo_5_criar_funcionario_sem_user():
    """Exemplo 5: Criar funcionário sem acesso ao sistema"""
    print("\n" + "="*60)
    print("EXEMPLO 5: Criar Funcionário Sem Acesso ao Sistema")
    print("="*60)
    
    with app.app_context():
        company = Company.query.first()
        
        if not company:
            print("⚠ Nenhuma empresa encontrada.")
            return
        
        print(f"\n   Criando funcionário na empresa: {company.name}")
        
        result = UserEmployeeService.create_employee_without_user(
            company_id=company.id,
            employee_data={
                'name': 'Carlos Santos',
                'email': 'carlos@empresa.com',
                'phone': '(11) 91234-5678',
                'department': 'Operações'
            }
        )
        
        if result['success']:
            print("\n✅ Funcionário criado com sucesso!")
            print(f"   Employee ID: {result['employee']['id']}")
            print(f"   Nome: {result['employee']['name']}")
            print(f"   Tem acesso ao sistema: Não (user_id é NULL)")
        else:
            print(f"\n❌ Erro: {result['error']}")


def menu():
    """Menu interativo"""
    print("\n" + "="*60)
    print("EXEMPLOS DE USO - Sistema de Usuários e Colaboradores")
    print("="*60)
    print("\n1. Cadastro Completo (User + Company + Employee)")
    print("2. Adicionar Usuário em Outra Empresa")
    print("3. Listar Empresas do Usuário")
    print("4. Minhas Atividades (Agregadas)")
    print("5. Criar Funcionário Sem Acesso ao Sistema")
    print("6. Executar Todos os Exemplos")
    print("0. Sair")
    
    escolha = input("\nEscolha uma opção: ")
    
    if escolha == '1':
        exemplo_1_cadastro_completo()
    elif escolha == '2':
        exemplo_2_adicionar_empresa()
    elif escolha == '3':
        exemplo_3_listar_empresas()
    elif escolha == '4':
        exemplo_4_minhas_atividades()
    elif escolha == '5':
        exemplo_5_criar_funcionario_sem_user()
    elif escolha == '6':
        exemplo_1_cadastro_completo()
        exemplo_2_adicionar_empresa()
        exemplo_3_listar_empresas()
        exemplo_4_minhas_atividades()
        exemplo_5_criar_funcionario_sem_user()
    elif escolha == '0':
        print("\nAté logo!")
        return False
    else:
        print("\n⚠ Opção inválida!")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Sistema de Exemplos Iniciado")
    
    continuar = True
    while continuar:
        continuar = menu()
    
    print("\n✅ Exemplos concluídos!")
