import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Project, ProjectTask

def run():
    app = create_app()
    with app.app_context():
        # code é uma @property calculada: COMPANY.J.ID
        # Por isso, buscamos todos os projetos e filtramos em Python
        all_projects = Project.query.all()
        p = None
        for proj in all_projects:
            try:
                if proj.code == 'AA.J.31':
                    p = proj
                    break
            except Exception:
                pass
        
        if not p:
            print(f"Project AA.J.31 not found among {len(all_projects)} projects.")
            print("Projetos existentes (primeiros 10):")
            for proj in all_projects[:10]:
                try:
                    print(f"  ID={proj.id} code={proj.code} name={proj.name}")
                except Exception as ex:
                    print(f"  ID={proj.id} erro={ex}")
            return

        print(f"Projeto encontrado: ID={p.id} code={p.code} name={p.name}")

        tasks_data = [
            "[Feito] Resolver bugs de TemplateSyntaxError e UndefinedError apos refatoracao",
            "[Feito] Implementar decouple dos Indicadores tornando-os entidades independentes (IncentiveIndicator -> Indicator)",
            "[Feito] Criar arvore de Indicadores independente (IndicatorTree) com formato Plano de Contas",
            "[Feito] Atualizar e refatorar views/templates de Indicadores e Incentivos",
            "[Feito] Criar script deploy_restructure_v3 para envio atomizado da versao Refatorada ao Configr",
            "[Feito] Corrigir importacoes remanescentes e restaurar a inicializacao do app em producao"
        ]

        added = 0
        for what in tasks_data:
            exists = ProjectTask.query.filter_by(project_id=p.id, what=what).first()
            if not exists:
                t = ProjectTask(
                    project_id=p.id,
                    what=what,
                    status="completed",
                    stage="completed"
                )
                db.session.add(t)
                added += 1
        db.session.commit()
        print(f"Adicionadas {added} tasks ao projeto AA.J.31 (ID {p.id})")

if __name__ == "__main__":
    run()
