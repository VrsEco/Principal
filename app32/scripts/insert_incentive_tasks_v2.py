
import os
import sys
sys.path.append(os.getcwd())
try:
    from models import db, Project, ProjectTask, Employee
    from app import create_app
except ImportError as e:
    print(f"Erro de import: {e}")
    sys.exit(1)

def insert_tasks():
    app = create_app()
    with app.app_context():
        # Usar o ID 31 conforme identificado no list_all
        project = Project.query.get(31)
        
        if not project:
            print("Projeto ID 31 não encontrado.")
            return
            
        print(f"Inserindo no projeto: {project.name} (Code: {project.code})")

        tasks_to_add = [
            {
                "what": "Plano de Incentivos - Parte 01: Definição de Models e Estrutura de Dados",
                "how": "Modelagem de tabelas para Regras de Incentivo e Snapshots periódicos conforme acordado no Nível 2.5.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Parte 02: Motor de Cálculo e Normalização",
                "how": "Implementação do IncentiveService para processamento de sinais polimórficos de indicadores.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Parte 03: Interface de Teia de Alinhamento (Strategic Canvas)",
                "how": "Visualização de grafo (Cytoscape/D3) integrada ao Mapa de Processos para gestão de 'Nós Órfãos'.",
                "priority": "medium"
            },
            {
                "what": "Plano de Incentivos - Parte 04: Auditoria Sob Demanda e Relatórios",
                "how": "Interface para disparo de auditoria de alinhamento estratégico pelo Squad Work.",
                "priority": "medium"
            }
        ]

        for task_info in tasks_to_add:
            # Check existance by 'what' in this project
            existing = ProjectTask.query.filter_by(project_id=project.id, what=task_info["what"]).first()
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
                print(f"Adicionada: {task_info['what']}")
            else:
                print(f"Já existe: {task_info['what']}")
        
        db.session.commit()
        print("Tudo pronto.")

if __name__ == "__main__":
    insert_tasks()
