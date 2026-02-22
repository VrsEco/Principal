
import sys
import os
from datetime import datetime, timedelta

# Padronizacao de caminho para raiz app32
sys.path.append(os.getcwd())

from app import create_app
from models import (
    db, Company, User, Employee, Portfolio, Plan, PlanParticipant, PlanSectionStatus, PlanDriver, OKRGlobal, KeyResult, Project, ProjectTask,
    ProcessArea, MacroProcess, Process, ProcessRoutine, ProcessStep
)
from sqlalchemy import text

app = create_app()

def reset_titan_corp():
    with app.app_context():
        print("--- REFAZENDO CADASTRO COMPLETO: TITAN CORP (ID 36) ---")
        
        # 1. IDENTIFICAR EMPRESA
        original_titan = Company.query.filter_by(name="Titan Corp").first()
        company_id = original_titan.id if original_titan else 36
        
        # 2. LIMPEZA DOS DADOS (DELETE CASCADE MANUAL)
        print("-> Limpando dados antigos...")

        # Add all potential tables that might reference employees or data
        tables_to_clean = [
            # My Work / Activities
            ("project_activity_collaborators", "activity_id IN (SELECT id FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))"),
            ("project_activities", "project_id IN (SELECT id FROM projects WHERE company_id = :cid)"),
            
            ("activity_comments", "company_id = :cid"), 
            ("activity_work_logs", "company_id = :cid"), 
            
            # Meetings
            ("meeting_participants", "meeting_id IN (SELECT id FROM meetings WHERE company_id = :cid)"),
            ("meetings", "company_id = :cid"),
            
            # Teams
            ("team_members", "team_id IN (SELECT id FROM teams WHERE company_id = :cid)"),
            ("teams", "company_id = :cid"),
            
            # Occurrences
            ("occurrences", "company_id = :cid"),
            
            # Notes
            ("notes", "user_id IN (SELECT id FROM users WHERE email LIKE '%@titancorp.com')"),
            
            # Projects & Portfolios
            ("project_tasks", "project_id IN (SELECT id FROM projects WHERE company_id = :cid)"),
            ("projects", "company_id = :cid"),
            ("portfolios", "company_id = :cid"),
            
            # Strategic Planning
            ("key_results", "okr_global_id IN (SELECT id FROM okrs_global WHERE company_id = :cid)"),
            ("okrs_global", "company_id = :cid"),
            ("plan_drivers", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_section_status", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_participants", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plan_implantation_data", "plan_id IN (SELECT id FROM plans WHERE company_id = :cid)"),
            ("plans", "company_id = :cid"),
            
            # Processes
            ("process_instances", "company_id = :cid"),
            ("process_steps", "routine_id IN (SELECT id FROM routines WHERE company_id = :cid)"),
            ("routines", "company_id = :cid"),
            ("processes", "company_id = :cid"),
            ("macro_processes", "company_id = :cid"),
            ("process_areas", "company_id = :cid"),
            
            # Employees (Last)
            ("employees", "company_id = :cid"),
        ]

        try:
            for table, condition in tables_to_clean:
                # print(f"   Deleting from {table}...") # Reduce spam
                try:
                    db.session.execute(text(f"DELETE FROM {table} WHERE {condition}"), {'cid': company_id})
                except Exception as inner_e:
                    txt = str(inner_e)
                    if "does not exist" in txt or "undefined table" in txt:
                        pass
                    else:
                        print(f"     Error deleting {table}: {inner_e}")
            
            # Commit cleanup
            db.session.commit()
            print("-> Limpeza concluida.")
        except Exception as e:
            print(f"ERRO CRITICO NA LIMPEZA: {e}")
            db.session.rollback()
            return

        # 3. RECRIAR EMPRESA (Se nao existir)
        titan = Company.query.get(company_id)
        if not titan:
            print("-> Criando Empresa Titan Corp...")
            titan = Company(name="Titan Corp", client_code="TITAN001", size="Grande", is_active=True)
            db.session.add(titan)
            db.session.commit()
        
        # 4. REPOPULAR DADOS
        try:
            # User (Admin is Global User, attached to Employee later if needed)
            # Check if user exists
            user_admin = User.query.filter_by(email="admin@titancorp.com").first()
            if not user_admin:
                user_admin = User(name="Admin Titan", email="admin@titancorp.com", role="admin")
                user_admin.set_password("titan123")
                db.session.add(user_admin)
                db.session.commit()
            
            # Employees (Use department instead of role)
            print("-> Seed Employees")
            # Clean email list first to avoid unique constraint if not deleted
            # (Wait, User table has unique email. Employee table doesn't necessarily enforce unique email globally, but usually valid)
            # Employee table constraints?
            
            emp1 = Employee(company_id=titan.id, name="Arthur Dent", email="arthur@titancorp.com", department="Engineering", notes="CTO")
            emp2 = Employee(company_id=titan.id, name="Ford Prefect", email="ford@titancorp.com", department="Product", notes="Product Manager")
            emp3 = Employee(company_id=titan.id, name="Trillian Astra", email="trillian@titancorp.com", department="Data Science", notes="Data Scientist")
            
            # Link Admin User to Arthur Dent?
            # If User Admin exists, we can link.
            # emp1.user_id = user_admin.id 
            
            db.session.add_all([emp1, emp2, emp3])
            db.session.commit()
            
            # Portfolio
            print("-> Seed Portfolio")
            portfolio = Portfolio(company_id=titan.id, code="PORT-IA", name="Inovacao e IA", responsible_id=emp1.id)
            db.session.add(portfolio)
            db.session.commit()
            
            # Plan
            print("-> Seed Plan")
            plan = Plan(company_id=titan.id, title="Plano de Dominio 2026", mode="growth", status="in_progress")
            db.session.add(plan)
            db.session.commit()
            
            # Plan Participants
            db.session.add(PlanParticipant(plan_id=plan.id, user_id=user_admin.id, role="owner"))
            
            # Drivers
            db.session.add(PlanDriver(plan_id=plan.id, type="driver", description="Liderar a transicao AI-First"))
            
            # OKR Global
            okr = OKRGlobal(company_id=titan.id, plan_id=plan.id, objective="Dominacao Global", type="aceleracao")
            db.session.add(okr)
            db.session.commit()
            
            db.session.add(KeyResult(okr_global_id=okr.id, label="Faturamento", metric="R$", target="50M"))
            
            # Plan Sections
            sections = ["growth_participants", "growth_drivers", "growth_alignment", "growth_okr_global", "growth_projects"]
            for s in sections:
                db.session.add(PlanSectionStatus(plan_id=plan.id, section_key=s, status="completed"))
            
            # Project
            print("-> Seed Project")
            proj = Project(
                company_id=titan.id, 
                portfolio_id=portfolio.id,
                name="Infraestrutura de RAG Corporativo",
                owner="Arthur Dent",
                status="in_progress",
                deadline=datetime.now().date() + timedelta(days=90),
                budget="R$ 150.000,00"
            )
            db.session.add(proj)
            db.session.commit()
            
            # Project Tasks
            task1 = ProjectTask(project_id=proj.id, employee_id=emp1.id, what="Arquitetura Vetorial", status="completed", priority="high")
            task2 = ProjectTask(project_id=proj.id, employee_id=emp3.id, what="Criptografia", status="in_progress", priority="urgent")
            db.session.add_all([task1, task2])
            
            # Processes
            print("-> Seed Processes")
            area = ProcessArea(company_id=titan.id, name="Operacoes de IA", code="IA-OPS")
            db.session.add(area)
            db.session.commit()
            
            macro = MacroProcess(company_id=titan.id, area_id=area.id, name="Ciclo de Dados", code="DATA-CYCLE")
            db.session.add(macro)
            db.session.commit()
            
            proc = Process(company_id=titan.id, macro_id=macro.id, name="Curadoria de Datasets", code="DATA-01")
            db.session.add(proc)
            db.session.commit()
            
            routine = ProcessRoutine(company_id=titan.id, process_id=proc.id, name="Higienizacao Diaria", code="R-01")
            db.session.add(routine)
            db.session.commit()
            
            step1 = ProcessStep(routine_id=routine.id, name="Verificar Duplicatas", order_index=1)
            step2 = ProcessStep(routine_id=routine.id, name="Validar Schema JSON", order_index=2)
            db.session.add_all([step1, step2])
            db.session.commit()
            
            print("\n--- CADASTRO REFEITO COM SUCESSO! ---")
            
        except Exception as e:
            print(f"ERRO NA INSERCAO: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    reset_titan_corp()
