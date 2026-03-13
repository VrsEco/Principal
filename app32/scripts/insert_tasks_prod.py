
import sys
import os
from pathlib import Path

# Add app32 to path to find local scripts
sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_prod_query():
    ssh = connect_ssh()
    try:
        # Find project by name on production
        cmd = f"cd {APP_DIR} && python3 -c \"import os, sys; sys.path.append(os.getcwd()); from app import create_app; from models import db, Project; app = create_app(); with app.app_context(): p = Project.query.filter(Project.name.ilike('%AA.J.31%')).first(); print(p.id if p else 'NOT_FOUND')\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        prod_id = stdout.read().decode().strip()
        print(f"Production Project ID: {prod_id}")
        
        if prod_id != 'NOT_FOUND':
            # Run the refactor/insertion
            tasks_script = """
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, Project, ProjectTask

app = create_app()
with app.app_context():
    pid = {0}
    # Clean up old ones starting with 'Plano de Incentivos'
    ProjectTask.query.filter(ProjectTask.project_id == pid, ProjectTask.what.ilike('Plano de Incentivos%')).delete()
    
    tasks = [
        {{'what': 'Plano de Incentivos - Onda 1A: Catálogo, Governança e Camada de Fatos (Anti-Corrupção)', 'how': 'Criar models p/ Catálogo de Indicadores, Regras por versão, Matriz de Governabilidade e a camada de Facts normalizados.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}},
        {{'what': 'Plano de Incentivos - Onda 1B: Motor de Cálculo por Fatores e Ritual de Fechamento (Snapshot)', 'how': 'Implementar pipeline de cálculo sequencial, workflow de fechamento com snapshot imutável e explicabilidade.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}},
        {{'what': 'Plano de Incentivos - Onda 2: Adaptadores de Integração (Ocorrências, Processos e Projetos)', 'how': 'Desenvolver adaptadores que transformam execuções de processos, entregas de projetos e ocorrências em Fatos consumíveis.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}},
        {{'what': 'Plano de Incentivos - Onda 3: Auditoria de Alinhamento e Detecção de Nós Órfãos', 'how': 'Criar ferramentas de auditoria sob demanda p/ identificar desalinhamento estratégico e fluxo de contestação.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}},
        {{'what': 'Plano de Incentivos - Onda 4: Interface Visual de Teia (Spider Web) e Analytics', 'how': 'Implementar visualização de grafo p/ navegação na teia de incentivos e heatmaps de governabilidade operacional.', 'priority': 'low', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}}
    ]
    
    for t_data in tasks:
        db.session.add(ProjectTask(**t_data))
    
    db.session.commit()
    print('SUCCESS')
""".format(prod_id)
            
            # Escape single quotes for shell
            escaped_script = tasks_script.replace('"', '\\"').replace('`', '\\`')
            cmd_insert = f"cd {APP_DIR} && python3 -c \"{escaped_script}\""
            stdin, stdout, stderr = ssh.exec_command(cmd_insert)
            res = stdout.read().decode().strip()
            print(f"Insert Result: {res}")
            err = stderr.read().decode().strip()
            if err:
                print(f"Errors: {err}")
    finally:
        ssh.close()

if __name__ == "__main__":
    run_prod_query()
