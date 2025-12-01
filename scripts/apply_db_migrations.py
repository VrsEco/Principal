"""
Script para aplicar as alterações de estrutura no banco de dados
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from sqlalchemy import text

def apply_migrations():
    """Aplica as migrações de estrutura"""
    with app.app_context():
        try:
            # 1. Adicionar coluna permissions em roles
            print("1. Adicionando coluna 'permissions' em 'roles'...")
            db.session.execute(text("""
                ALTER TABLE roles 
                ADD COLUMN IF NOT EXISTS permissions JSON
            """))
            db.session.commit()
            print("   ✓ Coluna 'permissions' adicionada")
            
            # 2. Adicionar coluna employee_id em project_tasks
            print("2. Adicionando coluna 'employee_id' em 'project_tasks'...")
            db.session.execute(text("""
                ALTER TABLE project_tasks 
                ADD COLUMN IF NOT EXISTS employee_id INTEGER
            """))
            db.session.commit()
            print("   ✓ Coluna 'employee_id' adicionada")
            
            # 3. Adicionar Foreign Key
            print("3. Adicionando Foreign Key constraint...")
            db.session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'fk_project_tasks_employee'
                    ) THEN
                        ALTER TABLE project_tasks
                        ADD CONSTRAINT fk_project_tasks_employee
                        FOREIGN KEY (employee_id)
                        REFERENCES employees (id);
                    END IF;
                END $$;
            """))
            db.session.commit()
            print("   ✓ Foreign Key adicionada")
            
            print("\n✅ Migração de estrutura concluída com sucesso!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao aplicar migração: {e}")
            return False

if __name__ == "__main__":
    apply_migrations()
