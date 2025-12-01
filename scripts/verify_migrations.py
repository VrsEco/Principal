"""
Script para verificar o resultado das migrações
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.employee import Employee
from models.project import ProjectTask
from sqlalchemy import text

def verify_migrations():
    """Verifica o resultado das migrações"""
    with app.app_context():
        print("=" * 60)
        print("VERIFICAÇÃO DAS MIGRAÇÕES")
        print("=" * 60)
        
        # 1. Verificar Users
        users_count = User.query.count()
        print(f"\n1. Usuários no sistema: {users_count}")
        
        # 2. Verificar Employees
        employees_count = Employee.query.count()
        employees_with_user = Employee.query.filter(Employee.user_id.isnot(None)).count()
        employees_without_user = Employee.query.filter(Employee.user_id.is_(None)).count()
        
        print(f"\n2. Colaboradores (Employees):")
        print(f"   - Total: {employees_count}")
        print(f"   - Com vínculo User: {employees_with_user}")
        print(f"   - Sem vínculo User: {employees_without_user}")
        
        # 3. Verificar ProjectTasks
        tasks_total = ProjectTask.query.count()
        tasks_with_employee = ProjectTask.query.filter(ProjectTask.employee_id.isnot(None)).count()
        tasks_without_employee = ProjectTask.query.filter(ProjectTask.employee_id.is_(None)).count()
        
        print(f"\n3. Tarefas (ProjectTasks):")
        print(f"   - Total: {tasks_total}")
        print(f"   - Com employee_id: {tasks_with_employee}")
        print(f"   - Sem employee_id: {tasks_without_employee}")
        
        # 4. Verificar estrutura de roles
        result = db.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'roles' AND column_name = 'permissions'
        """))
        has_permissions = result.fetchone() is not None
        
        print(f"\n4. Estrutura da tabela 'roles':")
        print(f"   - Campo 'permissions' existe: {'✓ Sim' if has_permissions else '✗ Não'}")
        
        # 5. Verificar estrutura de project_tasks
        result = db.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'project_tasks' AND column_name = 'employee_id'
        """))
        has_employee_id = result.fetchone() is not None
        
        print(f"\n5. Estrutura da tabela 'project_tasks':")
        print(f"   - Campo 'employee_id' existe: {'✓ Sim' if has_employee_id else '✗ Não'}")
        
        # 6. Listar alguns employees
        print(f"\n6. Amostra de Employees:")
        employees = Employee.query.limit(5).all()
        for emp in employees:
            user_info = f"User ID {emp.user_id}" if emp.user_id else "Sem User"
            print(f"   - {emp.name} ({user_info}) @ Company {emp.company_id}")
        
        print("\n" + "=" * 60)
        print("✅ VERIFICAÇÃO CONCLUÍDA")
        print("=" * 60)

if __name__ == "__main__":
    verify_migrations()
