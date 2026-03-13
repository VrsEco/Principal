
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def insert_prod_tasks():
    ssh = connect_ssh()
    try:
        pid = 31 # Confirmed ID for "DEV APP Gestão Versus"
        
        script_content = """
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, ProjectTask

app = create_app()
with app.app_context():
    pid = 31
    # Clean up old ones starting with 'Plano de Incentivos'
    tasks_to_del = ProjectTask.query.filter(ProjectTask.project_id == pid, ProjectTask.what.ilike('Plano de Incentivos%')).all()
    for t in tasks_to_del:
        db.session.delete(t)
    
    tasks = [
        {'what': 'Plano de Incentivos - Onda 1A: Catálogo, Governança e Camada de Fatos (Anti-Corrupção)', 'how': 'Criar models p/ Catálogo de Indicadores, Regras por versão, Matriz de Governabilidade e a camada de Facts normalizados.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 1B: Motor de Cálculo por Fatores e Ritual de Fechamento (Snapshot)', 'how': 'Implementar pipeline de cálculo sequencial, workflow de fechamento com snapshot imutável e explicabilidade.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 2: Adaptadores de Integração (Ocorrências, Processos e Projetos)', 'how': 'Desenvolver adaptadores que transformam execuções de processos, entregas de projetos e ocorrências em Fatos consumíveis.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 3: Auditoria de Alinhamento e Detecção de Nós Órfãos', 'how': 'Criar ferramentas de auditoria sob demanda p/ identificar desalinhamento estratégico e fluxo de contestação.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 4: Interface Visual de Teia (Spider Web) e Analytics', 'how': 'Implementar visualização de grafo p/ navegação na teia de incentivos e heatmaps de governabilidade operacional.', 'priority': 'low', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}
    ]
    
    for t_data in tasks:
        db.session.add(ProjectTask(**t_data))
    
    db.session.commit()
    print('SUCCESS_PROD')
"""
        # Uploading via kitty or cat
        remote_script_path = f"{APP_DIR}/tmp_insert_tasks.py"
        # We need to escape correctly or use sftp. Let's try simple cat.
        # To avoid issues with {} and quotes, I'll write it to a local file first and then maybe I should use sftp if available.
        # But I don't have sftp tool. I'll use run_command with heredoc.
        
        # Base64 encode the script to avoid shell escaping issues
        import base64
        b64_script = base64.b64encode(script_content.encode()).decode()
        
        cmd = f"echo {b64_script} | base64 -d > {remote_script_path} && cd {APP_DIR} && python3 tmp_insert_tasks.py && rm {remote_script_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        print(f"Output: {out}")
        print(f"Error: {err}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    insert_prod_tasks()
