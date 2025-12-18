
import os
import sys
import logging
from datetime import datetime

# Adicionar o diretório atual ao path para importar as configurações do app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from config_database import get_db
    from app_pev import app
except ImportError as e:
    print(f"Erro ao importar módulos do sistema: {e}")
    sys.exit(1)

# Configuração de logging básica para o script
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_diagnostic():
    print(f"\n{'='*60}")
    print(f" RELATÓRIO DE DIAGNÓSTICO DE IMAGENS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")

    db = get_db()
    
    # 1. Verificar Configuração de Pastas
    upload_root = app.config.get("UPLOAD_FOLDER", "uploads")
    print(f"[*] Diretório raiz de uploads: {upload_root}")
    print(f"[*] Existe no disco? {'SIM' if os.path.exists(upload_root) else 'NÃO'}")
    
    paths_to_check = {
        "Fluxos de Processo": "process_flows",
        "Imagens de POP": "process_activities",
        "Uploads de POP (novos)": "uploads/pop"
    }

    print("\n[1] Verificação Física de Diretórios:")
    for label, subpath in paths_to_check.items():
        full_path = os.path.join(upload_root, subpath)
        exists = os.path.exists(full_path)
        count = len(os.listdir(full_path)) if exists else 0
        print(f"  - {label} ({subpath}): {'[OK]' if exists else '[AUSENTE]'} - Arquivos: {count}")

    # 2. Verificação de Integridade no Banco - Fluxos
    print("\n[2] Verificação de Referências no Banco (Fluxos):")
    try:
        processes = db.list_processes(None) # Passar None para listar de todas as empresas ou ajustar se necessário
        # Se list_processes exigir company_id e não aceitar None, pegamos todas as empresas primeiro
        companies = db.get_companies()
        
        total_references = 0
        broken_links = 0
        
        for comp in companies:
            c_id = comp['id']
            procs = db.list_processes(c_id)
            for p in procs:
                flow = p.get('flow_document')
                if flow:
                    total_references += 1
                    full_disk_path = os.path.join(upload_root, flow)
                    if not os.path.exists(full_disk_path):
                        broken_links += 1
                        print(f"  [!] LINK QUEBRADO (Processo {p['code']}): {flow}")
        
        print(f"  >> Total de referências encontradas: {total_references}")
        print(f"  >> Total de links quebrados: {broken_links}")
        
    except Exception as e:
        print(f"  [!] Erro ao verificar fluxos: {e}")

    # 3. Verificação de Integridade no Banco - POP (Activities)
    print("\n[3] Verificação de Referências no Banco (Imagens POP):")
    try:
        # Precisamos de uma query manual ou método que liste entradas de atividades
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, image_path, activity_id FROM process_activity_entries WHERE image_path IS NOT NULL")
        entries = cursor.fetchall()
        
        total_pop_refs = len(entries)
        broken_pop_links = 0
        
        for entry in entries:
            # entry é um Row ou dict dependendo do cursor, ajustando para acesso genérico
            e_id = entry[0]
            img_path = entry[1]
            
            # O sistema pode salvar caminhos relativos de formas variadas
            # Normalizando: se começar com 'uploads/', remover para usar join com upload_root
            search_path = img_path
            if img_path.startswith('uploads/'):
                search_path = img_path.replace('uploads/', '', 1)
            
            full_disk_path = os.path.join(upload_root, search_path)
            
            if not os.path.exists(full_disk_path):
                broken_pop_links += 1
                # print(f"  [!] LINK QUEBRADO (POP Entry {e_id}): {img_path}")
        
        print(f"  >> Total de imagens de POP referenciadas: {total_pop_refs}")
        print(f"  >> Total de links quebrados em POP: {broken_pop_links}")
        
        conn.close()
    except Exception as e:
        print(f"  [!] Erro ao verificar POP: {e}")

    print(f"\n{'='*60}")
    print(" CONCLUSÃO DO DIAGNÓSTICO")
    print(f"{'='*60}")
    
    if broken_links > 0 or broken_pop_links > 0:
        print("\n[ALERTA] Foram encontrados links no banco de dados para arquivos que NÃO existem no disco.")
        print("Isso geralmente ocorre quando o container é recriado (Redeploy) sem volumes persistentes.")
    else:
        print("\n[OK] Todas as referências no banco possuem arquivos correspondentes no disco.")
    
    print("\nDica: Se estiver no Google Cloud Run, verifique se a pasta /app/uploads está montada como um volume persistente.")

if __name__ == "__main__":
    run_diagnostic()
