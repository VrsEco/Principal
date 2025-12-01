"""
Script para migrar dados existentes:
1. Criar Employee para cada User existente
2. Vincular project_tasks.who (texto) para employee_id
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.project import ProjectTask
from sqlalchemy import text

def migrate_users_to_employees():
    """Cria registros Employee para Users existentes"""
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO DE DADOS: Users → Employees")
            print("=" * 60)
            
            # 1. Buscar todos os usuários
            users = User.query.all()
            print(f"\n1. Encontrados {len(users)} usuários no sistema")
            
            if not users:
                print("   ⚠ Nenhum usuário encontrado. Pulando migração.")
                return True
            
            # 2. Buscar empresas (vamos vincular à primeira empresa por padrão)
            companies = Company.query.all()
            print(f"2. Encontradas {len(companies)} empresas no sistema")
            
            if not companies:
                print("   ⚠ Nenhuma empresa encontrada. Criando empresa padrão...")
                default_company = Company(
                    name="Versus Gestão Corporativa",
                    legal_name="Versus Gestão Corporativa Ltda"
                )
                db.session.add(default_company)
                db.session.commit()
                companies = [default_company]
                print(f"   ✓ Empresa padrão criada: {default_company.name}")
            
            default_company = companies[0]
            
            # 3. Criar Employee para cada User (se ainda não existir)
            created_count = 0
            skipped_count = 0
            
            print(f"\n3. Criando vínculos Employee para empresa: {default_company.name}")
            
            for user in users:
                # Verificar se já existe Employee para este user nesta company
                existing = Employee.query.filter_by(
                    user_id=user.id,
                    company_id=default_company.id
                ).first()
                
                if existing:
                    print(f"   - {user.name}: já possui vínculo (ID {existing.id})")
                    skipped_count += 1
                    continue
                
                # Criar novo Employee
                employee = Employee(
                    user_id=user.id,
                    company_id=default_company.id,
                    name=user.name,
                    email=user.email,
                    status='active'
                )
                db.session.add(employee)
                created_count += 1
                print(f"   + {user.name}: vínculo criado")
            
            db.session.commit()
            
            print(f"\n✅ Migração concluída:")
            print(f"   - Criados: {created_count} vínculos")
            print(f"   - Já existiam: {skipped_count} vínculos")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro na migração: {e}")
            import traceback
            traceback.print_exc()
            return False


def migrate_project_tasks_who_to_employee():
    """Vincula project_tasks.who (texto) para employee_id"""
    with app.app_context():
        try:
            print("\n" + "=" * 60)
            print("MIGRAÇÃO DE DADOS: project_tasks.who → employee_id")
            print("=" * 60)
            
            # Buscar todas as tasks sem employee_id
            tasks = ProjectTask.query.filter(
                ProjectTask.employee_id.is_(None),
                ProjectTask.who.isnot(None)
            ).all()
            
            print(f"\n1. Encontradas {len(tasks)} tarefas para migrar")
            
            if not tasks:
                print("   ✓ Nenhuma tarefa pendente de migração")
                return True
            
            # Buscar todos os employees
            employees = Employee.query.all()
            print(f"2. Encontrados {len(employees)} colaboradores no sistema")
            
            # Criar mapa de nomes para employee_id
            name_to_employee = {}
            for emp in employees:
                # Normalizar nome (lowercase, sem espaços extras)
                normalized_name = emp.name.lower().strip()
                name_to_employee[normalized_name] = emp.id
            
            # Migrar tasks
            matched_count = 0
            unmatched_count = 0
            
            print(f"\n3. Vinculando tarefas aos colaboradores...")
            
            for task in tasks:
                who_normalized = task.who.lower().strip()
                
                if who_normalized in name_to_employee:
                    task.employee_id = name_to_employee[who_normalized]
                    matched_count += 1
                    print(f"   ✓ '{task.who}' → Employee ID {task.employee_id}")
                else:
                    unmatched_count += 1
                    print(f"   ⚠ '{task.who}' → Não encontrado")
            
            db.session.commit()
            
            print(f"\n✅ Migração concluída:")
            print(f"   - Vinculadas: {matched_count} tarefas")
            print(f"   - Não encontradas: {unmatched_count} tarefas")
            
            if unmatched_count > 0:
                print(f"\n💡 Dica: Revise manualmente as {unmatched_count} tarefas não vinculadas")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro na migração: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("\n🚀 Iniciando migração de dados...\n")
    
    # Passo 1: Criar Employees
    success1 = migrate_users_to_employees()
    
    if success1:
        # Passo 2: Vincular Tasks
        success2 = migrate_project_tasks_who_to_employee()
        
        if success2:
            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO COMPLETA COM SUCESSO!")
            print("=" * 60)
        else:
            print("\n⚠ Migração parcial: Employees criados, mas Tasks não vinculadas")
    else:
        print("\n❌ Migração falhou na criação de Employees")
