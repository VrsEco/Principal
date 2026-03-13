
import os
import sys

# Adicionar o diretório raiz ao path para importar os models
sys.path.append(os.getcwd())

from models import db, Project, ProjectTask
from app import create_app

def refactor_incentive_tasks():
    app = create_app()
    with app.app_context():
        # 1. Buscar o projeto ID 31 (já confirmado anteriormente)
        project = Project.query.get(31)
        
        if not project:
            print("Projeto ID 31 não encontrado.")
            return
            
        print(f"Refatorando tarefas no projeto: {project.name}")

        # 2. Remover as tarefas genéricas anteriores (Plano de Incentivos - Parte ...)
        deleted = ProjectTask.query.filter(
            ProjectTask.project_id == project.id,
            ProjectTask.what.ilike("Plano de Incentivos - Parte %")
        ).delete(synchronize_session=False)
        print(f"Removidas {deleted} tarefas antigas.")

        # 3. Definir as novas tarefas baseadas na Auditoria de Arquitetura e Modelo por Camadas
        new_tasks = [
            {
                "what": "Plano de Incentivos - Onda 1A: Catálogo, Governança e Camada de Fatos (Anti-Corrupção)",
                "how": "Criar models p/ Catálogo de Indicadores, Regras por versão (Pisos/Tetos/Caps), Matriz de Governabilidade (Direta/Indireta) e a camada de Facts normalizados p/ isolar o motor de módulos legados.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Onda 1B: Motor de Cálculo por Fatores e Ritual de Fechamento (Snapshot)",
                "how": "Implementar pipeline de cálculo sequencial (Fatores 0.0 a 1.2), workflow de fechamento com snapshot imutável, suporte a overrides justificados e explicabilidade do bônus p/ o colaborador.",
                "priority": "high"
            },
            {
                "what": "Plano de Incentivos - Onda 2: Adaptadores de Integração (Ocorrências, Processos e Projetos)",
                "how": "Desenvolver adaptadores que transformam execuções de processos, entregas de projetos e ocorrências em 'Fatos' consumíveis pelo motor, suportando o modelo de maturidade multi-camadas.",
                "priority": "medium"
            },
            {
                "what": "Plano de Incentivos - Onda 3: Auditoria de Alinhamento e Detecção de Nós Órfãos",
                "how": "Criar ferramentas de auditoria sob demanda p/ identificar desalinhamento estratégico entre cargos e processos, e fluxo de contestação/aprovação gerencial.",
                "priority": "medium"
            },
            {
                "what": "Plano de Incentivos - Onda 4: Interface Visual de Teia (Spider Web) e Analytics",
                "how": "Implementar visualização de grafo (Cytoscape/D3) p/ navegação na teia de incentivos e heatmaps de governabilidade operacional integrados ao Mapa de Processos.",
                "priority": "low"
            }
        ]

        # 4. Inserir as novas tarefas
        for task_info in new_tasks:
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

        db.session.commit()
        print("Refatoração finalizada com sucesso conforme a nova estratégia arquitetural.")

if __name__ == "__main__":
    refactor_incentive_tasks()
