
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, ProjectTask, Project

app = create_app()
with app.app_context():
    # Encontrar o projeto 31
    p = Project.query.filter_by(id=31).first()
    if not p:
        p = Project.query.filter(Project.code.ilike('AA.J.31%')).first()
    
    if not p:
        print("ERROR: Project AA.J.31 not found.")
        sys.exit(1)

    print(f"Adding restructuring tasks to Project {p.id} ({p.code})")

    tasks_to_add = [
        {
            "what": "[REESTRUTURAÇÃO] Criação da estrutura de Árvore de Indicadores (Hierarquia/Níveis)",
            "how": "Implementação do model IncentiveIndicatorTree e vinculação recursiva para navegação estilo Plano de Contas.",
            "priority": "high",
            "stage": "todo"
        },
        {
            "what": "[REESTRUTURAÇÃO] Padronização de Codificação Estilo Plano de Contas (AA.I.X.X)",
            "how": "Lógica automática para geração e validação de códigos únicos baseados na posição da árvore e identificador da empresa.",
            "priority": "high",
            "stage": "todo"
        },
        {
            "what": "[REESTRUTURAÇÃO] Refatoração do Hub de Ingestão de Dados (API, Webhook, MCP e Harvesters)",
            "how": "Centralização da coleta em camada agnóstica de fonte, permitindo entrada manual e automatizada padronizada.",
            "priority": "high",
            "stage": "todo"
        },
        {
            "what": "[REESTRUTURAÇÃO] Novo Dashboard de Performance Premium",
            "how": "Interface visual com drill-down na árvore, indicadores de calor e visualização executiva consolidada.",
            "priority": "high",
            "stage": "todo"
        }
    ]

    for task_data in tasks_to_add:
        # Evitar duplicidade básica pelo nome
        exists = ProjectTask.query.filter_by(project_id=p.id, what=task_data["what"]).first()
        if not exists:
            new_task = ProjectTask(
                project_id=p.id,
                what=task_data["what"],
                how=task_data["how"],
                priority=task_data["priority"],
                stage=task_data["stage"],
                status='planned'
            )
            db.session.add(new_task)
            print(f"Added task: {task_data['what']}")
        else:
            print(f"Task already exists: {task_data['what']}")

    db.session.commit()
    print("SUCCESS: Project AA.J.31 tasks added to database.")
