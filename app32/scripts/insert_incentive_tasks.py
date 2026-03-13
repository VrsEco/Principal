
import os
import sys

# Adicionar o diretório raiz ao path para importar os models
sys.path.append(os.getcwd())

from models import db, Project, ProjectTask
from app import create_app

def find_and_insert_tasks():
    app = create_app()
    with app.app_context():
        # 1. Buscar o projeto
        project_name = "AA.J.31 DEV APP Gestão Versus"
        project = Project.query.filter(Project.name.ilike(f"%{project_name}%")).first()
        
        if not project:
            print(f"Projeto '{project_name}' não encontrado.")
            # Buscar qualquer projeto que comece com AA.J.31
            project = Project.query.filter(Project.name.ilike("AA.J.31%")).first()
            if not project:
                print("Nenhum projeto AA.J.31 encontrado.")
                return
            else:
                print(f"Usando projeto encontrado: {project.name} (ID: {project.id})")
        else:
            print(f"Projeto encontrado: {project.name} (ID: {project.id})")

        # 2. Definir as tarefas
        tasks_to_add = [
            {
                "what": "Plano de Incentivos - Parte 01: Definição de Models e Estrutura de Dados",
                "how": "Criar novos models para Regras de Incentivo (Base, Multiplicadores, Redutores) e Snapshots de Premiação periódica.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Parte 02: Motor de Cálculo e Normalização",
                "how": "Implementar a Layer 3 (IncentiveService) para processamento de sinais de indicadores e cálculo de valores por colaborador.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Parte 03: Interface de Teia de Alinhamento (Strategic Canvas)",
                "how": "Desenvolver visualização de grafo integrada ao Mapa de Processos para auditar conexões entre Processos, Indicadores e Incentivos.",
                "priority": "medium"
            },
            {
                "what": "Plano de Incentivos - Parte 04: Auditoria Sob Demanda e Relatórios de Transparência",
                "how": "Criar ferramenta de auditoria manual via Agentes de Work para detectar processos órfãos e dashboards de acompanhamento.",
                "priority": "medium"
            }
        ]

        # 3. Inserir tarefas
        for task_info in tasks_to_add:
            # Verificar se já existe
            existing = ProjectTask.query.filter_by(
                project_id=project.id, 
                what=task_info["what"]
            ).first()
            
            if not existing:
                new_task = ProjectTask(
                    project_id=project.id,
                    what=task_info["what"],
                    how=task_info["how"],
                    priority=task_info["priority"],
                    stage="inbox",
                    status="planned"
                )
                db.session.add(new_task)
                print(f"Tarefa adicionada: {task_info['what']}")
            else:
                print(f"Tarefa já existe: {task_info['what']}")

        db.session.commit()
        print("Finalizado com sucesso.")

if __name__ == "__main__":
    find_and_insert_tasks()
