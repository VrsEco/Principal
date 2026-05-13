import os
import sys
from datetime import datetime

import paramiko
from scp import SCPClient

# --- CONFIGURAÇÕES ---
HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app"
PASS = "*Paraiso1978"

# Pastas remotas no Configr
REMOTE_BACKUP_DIR = "/home/app/backups"
REMOTE_CODE_DIR = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32"
REMOTE_UPLOADS_DIR = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/uploads"

# Pasta local sincronizada (OneDrive)
LOCAL_BACKUP_DIR = r"C:\Users\mff20\OneDrive\Versus\Versus Participações\Versus ERP\Backup_app"

# Configuração de retenção
KEEP_LAST_N_BACKUPS = 3


def configure_stdout():
    """Evita quebra de encoding no console padrão do Windows."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

def create_local_structure():
    """Cria a estrutura de pastas local"""
    folders = [
        LOCAL_BACKUP_DIR,
        os.path.join(LOCAL_BACKUP_DIR, "database"),
        os.path.join(LOCAL_BACKUP_DIR, "code"),
        os.path.join(LOCAL_BACKUP_DIR, "uploads")
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    return folders

def cleanup_old_backups(directory, pattern, keep_last=KEEP_LAST_N_BACKUPS):
    """Remove backups antigos, mantendo apenas os N mais recentes"""
    try:
        # Lista todos os arquivos que correspondem ao padrão
        files = [f for f in os.listdir(directory) if pattern in f]
        
        if len(files) <= keep_last:
            return 0  # Não há nada para limpar
        
        # Ordena por data de modificação (mais recente primeiro)
        files_with_time = [(f, os.path.getmtime(os.path.join(directory, f))) for f in files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        # Remove os arquivos mais antigos
        removed = 0
        for file, _ in files_with_time[keep_last:]:
            file_path = os.path.join(directory, file)
            os.remove(file_path)
            removed += 1
            print(f"    [Removido] {file} (backup antigo)")
        
        return removed
    except Exception as e:
        print(f"    ⚠️  Erro ao limpar backups antigos: {e}")
        return 0

def download_database_backups(ssh, scp):
    """Baixa backups do banco de dados"""
    print("\n[1/3] SINCRONIZANDO BACKUPS DO BANCO DE DADOS...")
    local_db_dir = os.path.join(LOCAL_BACKUP_DIR, "database")
    
    try:
        sftp = ssh.open_sftp()
        remote_files = sftp.listdir(REMOTE_BACKUP_DIR)
        backup_files = [f for f in remote_files if f.endswith('.gz') or f.endswith('.sql')]
        
        if not backup_files:
            print("  ⚠️  Nenhum backup de banco encontrado no servidor.")
            return
        
        print(f"  Encontrados {len(backup_files)} arquivos de backup.")
        downloaded = 0
        
        for file in backup_files:
            local_file_path = os.path.join(local_db_dir, file)
            
            if os.path.exists(local_file_path):
                continue
            
            print(f"    [Baixando] {file}...")
            remote_file_path = f"{REMOTE_BACKUP_DIR}/{file}"
            scp.get(remote_file_path, local_file_path)
            downloaded += 1
        
        if downloaded > 0:
            print(f"  ✅ {downloaded} novos backups baixados.")
        else:
            print(f"  ✅ Todos os backups já estão sincronizados.")
        
        # Limpa backups antigos
        removed = cleanup_old_backups(local_db_dir, "backup_")
        if removed > 0:
            print(f"  🗑️  {removed} backups antigos removidos (mantendo últimos {KEEP_LAST_N_BACKUPS})")
        
        sftp.close()
        
    except Exception as e:
        print(f"  ❌ Erro ao baixar backups do banco: {e}")

def create_code_snapshot(ssh, scp):
    """Cria um snapshot compactado do código atual"""
    print("\n[2/3] CRIANDO SNAPSHOT DO CÓDIGO DA APLICAÇÃO...")
    local_code_dir = os.path.join(LOCAL_BACKUP_DIR, "code")
    
    try:
        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"code_snapshot_{timestamp}.tar.gz"
        remote_snapshot = f"/home/app/{snapshot_name}"
        local_snapshot = os.path.join(local_code_dir, snapshot_name)
        
        # Verifica se já existe snapshot de hoje
        today = datetime.now().strftime("%Y%m%d")
        existing_snapshots = [f for f in os.listdir(local_code_dir) if f.startswith(f"code_snapshot_{today}")]
        
        if existing_snapshots:
            print(f"  ✅ Snapshot de hoje já existe: {existing_snapshots[0]}")
            return
        
        print(f"  Compactando código no servidor...")
        # Compacta o código no servidor (excluindo venv, .git, uploads)
        cmd = f"cd {REMOTE_CODE_DIR} && tar -czf {remote_snapshot} --exclude='venv' --exclude='.venv' --exclude='.git' --exclude='uploads' --exclude='__pycache__' --exclude='*.pyc' --exclude='data' . 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()  # Aguarda conclusão
        
        print(f"  Baixando snapshot ({snapshot_name})...")
        scp.get(remote_snapshot, local_snapshot)
        
        # Remove arquivo temporário do servidor
        ssh.exec_command(f"rm -f {remote_snapshot}")
        
        # Verifica tamanho do arquivo baixado
        size_mb = os.path.getsize(local_snapshot) / (1024 * 1024)
        print(f"  ✅ Snapshot criado com sucesso ({size_mb:.2f} MB)")
        
        # Limpa snapshots antigos
        removed = cleanup_old_backups(local_code_dir, "code_snapshot_")
        if removed > 0:
            print(f"  🗑️  {removed} snapshots antigos removidos (mantendo últimos {KEEP_LAST_N_BACKUPS})")
        
    except Exception as e:
        print(f"  ❌ Erro ao criar snapshot do código: {e}")

def sync_uploads(ssh, scp):
    """Sincroniza arquivos de upload (imagens, PDFs, etc)"""
    print("\n[3/3] SINCRONIZANDO ARQUIVOS DE UPLOAD...")
    local_uploads_dir = os.path.join(LOCAL_BACKUP_DIR, "uploads")
    
    try:
        sftp = ssh.open_sftp()
        
        # Verifica se a pasta de uploads existe
        try:
            sftp.stat(REMOTE_UPLOADS_DIR)
        except IOError:
            print(f"  ⚠️  Pasta de uploads não encontrada no servidor.")
            return
        
        print(f"  Sincronizando arquivos...")
        
        # Função recursiva para baixar diretórios
        def download_recursive(remote_dir, local_dir):
            os.makedirs(local_dir, exist_ok=True)
            items = sftp.listdir_attr(remote_dir)
            downloaded = 0
            
            for item in items:
                remote_path = f"{remote_dir}/{item.filename}"
                local_path = os.path.join(local_dir, item.filename)
                
                # Se for diretório, recursão
                if item.st_mode & 0o040000:  # É diretório
                    downloaded += download_recursive(remote_path, local_path)
                else:
                    # Se arquivo já existe e tem mesmo tamanho, pula
                    if os.path.exists(local_path) and os.path.getsize(local_path) == item.st_size:
                        continue
                    
                    # Baixa arquivo
                    sftp.get(remote_path, local_path)
                    downloaded += 1
            
            return downloaded
        
        total_downloaded = download_recursive(REMOTE_UPLOADS_DIR, local_uploads_dir)
        
        if total_downloaded > 0:
            print(f"  ✅ {total_downloaded} novos arquivos sincronizados.")
        else:
            print(f"  ✅ Todos os uploads já estão sincronizados.")
        
        sftp.close()
        
    except Exception as e:
        print(f"  ❌ Erro ao sincronizar uploads: {e}")

def main():
    configure_stdout()
    print("=" * 60)
    print("  BACKUP COMPLETO: CONFIGR → LOCAL (OneDrive)")
    print("=" * 60)
    
    # Cria estrutura de pastas
    create_local_structure()
    
    try:
        # Conexão SSH
        print("\n🔌 Conectando ao servidor Configr...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        print("  ✅ Conectado com sucesso!")
        
        # Cria cliente SCP
        with SCPClient(ssh.get_transport()) as scp:
            # 1. Backups do banco
            download_database_backups(ssh, scp)
            
            # 2. Snapshot do código
            create_code_snapshot(ssh, scp)
            
            # 3. Arquivos de upload
            sync_uploads(ssh, scp)
        
        ssh.close()
        
        print("\n" + "=" * 60)
        print("  ✅ SINCRONIZAÇÃO COMPLETA FINALIZADA!")
        print("=" * 60)
        print(f"\n📁 Localização dos backups:")
        print(f"   {LOCAL_BACKUP_DIR}")
        print(f"\n☁️  O OneDrive sincronizará automaticamente para a nuvem.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        print("\nVerifique:")
        print("  - Conexão com a internet")
        print("  - Credenciais do servidor")
        print("  - Disponibilidade do servidor Configr")

if __name__ == "__main__":
    main()
