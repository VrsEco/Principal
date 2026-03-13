
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def insert_prod_tasks_v2():
    ssh = connect_ssh()
    try:
        pid = 31 # Confirmed ID for "DEV APP Gestão Versus"
        PYTHON_PATH = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        
        script_content = """
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, ProjectTask

app = create_app('production')
with app.app_context():
    pid = 31
    # Clean up old ones starting with 'Plano de Incentivos'
    tasks_to_del = ProjectTask.query.filter(ProjectTask.project_id == pid, ProjectTask.what.ilike('Plano de Incentivos%')).all()
    for t in tasks_to_del:
        db.session.delete(t)
    
    tasks = [
        {'what': 'Plano de Incentivos - Onda 1A: Catálogo, Governança e Camada de Fatos (Anti-Corrupção)', 'how': 'Criar models p/ Catálogo de Indicadores, Regras por versão, Matriz de Governança e a camada de Facts normalizados.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 1B: Motor de Cálculo por Fatores e Ritual de Fechamento (Snapshot)', 'how': 'Implementar pipeline de cálculo sequencial, workflow de fechamento com snapshot imutável e explicabilidade.', 'priority': 'high', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 2: Adaptadores de Integração (Ocorrências, Processos e Projetos)', 'how': 'Desenvolver adaptadores que transformam execuções de processos, entregas de projetos e ocorrências em Fatos consumíveis.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 3: Auditoria de Alinhamento e Detecção de Nós Órfãos', 'how': 'Criar ferramentas de auditoria sob demanda p/ identificar desalinhamento estratégico e fluxo de contestação.', 'priority': 'medium', 'stage': 'inbox', 'status': 'planned', 'project_id': pid},
        {'what': 'Plano de Incentivos - Onda 4: Interface Visual de Teia (Spider Web) e Analytics', 'how': 'Implementar visualização de grafo p/ navegação na teia de incentivos e heatmaps de governabilidade operacional.', 'priority': 'low', 'stage': 'inbox', 'status': 'planned', 'project_id': pid}
    ]
    
    for t_data in tasks:
        db.session.add(ProjectTask(**t_data))
    
    db.session.commit()
    print('SUCCESS_PROD_V2')
"""
        import base64
        b64_script = base64.b64encode(script_content.encode()).decode()
        
        remote_script_path = f"{APP_DIR}/tmp_insert_tasks_v2.py"
        cmd = f"echo {b64_script} | base64 -d > {remote_script_path} && cd {APP_DIR} && {PYTHON_PATH} tmp_insert_tasks_v2.py && rm {remote_script_path}"
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print(f"Output: {out}")
        print(f"Error: {err}")
        
        if "SUCCESS_PROD_V2" in out:
            print("\n✅ TAREFAS INSERIDAS COM SUCESSO NO PROJETO 31 EM PRODUÇÃO!")
        else:
            print("\n❌ FALHA NA INSERÇÃO EM PRODUÇÃO.")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    insert_prod_tasks_v2()
