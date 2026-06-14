import os
import sys
import re
from datetime import datetime
from pathlib import PurePosixPath

import paramiko
from scp import SCPClient

# --- CONFIGURAÇÕES ---
# Fonte oficial do backup de produção: servidor Configr.
# Credenciais NÃO devem ser versionadas. Use variáveis de ambiente:
#   GV_CONFIGR_HOST, GV_CONFIGR_PORT, GV_CONFIGR_USER,
#   GV_CONFIGR_PASSWORD ou GV_CONFIGR_KEY_PATH,
#   GV_BACKUP_LOCAL_DIR (opcional).
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_ONEDRIVE_BACKUP_DIR = r"C:\Users\mff20\OneDrive\Versus\Versus Participações\Versus ERP\Backup_app"
DEFAULT_WORKSPACE_BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")

HOST = os.getenv("GV_CONFIGR_HOST", "ip-69-164-205-75.cloudezapp.io")
PORT = int(os.getenv("GV_CONFIGR_PORT", "22122"))
USER = os.getenv("GV_CONFIGR_USER", "app")
PASSWORD = os.getenv("GV_CONFIGR_PASSWORD")
KEY_PATH = os.getenv("GV_CONFIGR_KEY_PATH")

# Pastas remotas no Configr
REMOTE_BACKUP_DIR = os.getenv("GV_CONFIGR_REMOTE_BACKUP_DIR", "/home/app/backups")
REMOTE_CODE_DIR = os.getenv(
    "GV_CONFIGR_REMOTE_CODE_DIR",
    "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32",
)
REMOTE_UPLOADS_DIR = os.getenv(
    "GV_CONFIGR_REMOTE_UPLOADS_DIR",
    "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/uploads",
)

# Pasta local sincronizada. Preferência:
# 1) GV_BACKUP_LOCAL_DIR explícito; 2) OneDrive existente; 3) workspace/backups.
def resolve_default_local_backup_dir():
    if os.getenv("GV_BACKUP_LOCAL_DIR"):
        return os.getenv("GV_BACKUP_LOCAL_DIR")
    if os.path.isdir(os.path.dirname(DEFAULT_ONEDRIVE_BACKUP_DIR)):
        return DEFAULT_ONEDRIVE_BACKUP_DIR
    return DEFAULT_WORKSPACE_BACKUP_DIR

LOCAL_BACKUP_DIR = resolve_default_local_backup_dir()

# Configuração de retenção
KEEP_LAST_N_BACKUPS = int(os.getenv("GV_BACKUP_KEEP_LAST", "3"))


def is_truthy_env(name):
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "sim", "on"}

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

def backup_sort_key(filename, directory):
    """Ordena backups por timestamp embutido no nome; fallback para mtime."""
    match = re.search(r"(20\d{6})[_-](\d{6})", filename)
    if match:
        return match.group(1) + match.group(2)
    return str(int(os.path.getmtime(os.path.join(directory, filename))))


def cleanup_old_backups(directory, pattern, keep_last=KEEP_LAST_N_BACKUPS, protected_files=None):
    """Remove backups antigos, mantendo os mais recentes por timestamp do nome."""
    protected_files = set(protected_files or [])
    try:
        files = [f for f in os.listdir(directory) if pattern in f]
        removable = [f for f in files if f not in protected_files]

        if len(files) <= keep_last:
            return 0

        files_with_key = [(f, backup_sort_key(f, directory)) for f in removable]
        files_with_key.sort(key=lambda x: x[1], reverse=True)

        keep_budget = max(keep_last - len(protected_files), 0)
        removed = 0
        for file, _ in files_with_key[keep_budget:]:
            file_path = os.path.join(directory, file)
            os.remove(file_path)
            removed += 1
            print(f"    [Removido] {file} (backup antigo)")

        return removed
    except Exception as e:
        print(f"    ⚠️  Erro ao limpar backups antigos: {e}")
        return 0

def create_remote_database_backup(ssh):
    """Cria um dump novo do banco de produção no Configr antes de baixar."""
    print("\n[0/3] GERANDO BACKUP NOVO DO BANCO DE PRODUÇÃO NO CONFIGR...")
    remote_python = """
import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

project = Path(os.environ.get("GV_REMOTE_CODE_DIR", "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32"))
env_file = project / ".env"
if not env_file.exists():
    raise SystemExit("REMOTE_ENV_MISSING")

env = {}
for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env[key.strip()] = value.strip().strip('\"').strip("'")

url = env.get("DATABASE_URL")
if url:
    parsed = urlparse(url)
    db_host = parsed.hostname or "localhost"
    db_port = str(parsed.port or 5432)
    db_user = unquote(parsed.username or env.get("POSTGRES_USER") or "postgres")
    db_pass = unquote(parsed.password or env.get("POSTGRES_PASSWORD") or "")
    db_name = parsed.path.lstrip("/")
else:
    db_host = env.get("POSTGRES_HOST", "localhost")
    db_port = env.get("POSTGRES_PORT", "5432")
    db_user = env.get("POSTGRES_USER", "postgres")
    db_pass = env.get("POSTGRES_PASSWORD", "")
    db_name = env.get("POSTGRES_DB")

if not db_name:
    raise SystemExit("REMOTE_DB_NAME_MISSING")

backup_dir = Path(os.environ.get("GV_REMOTE_BACKUP_DIR", "/home/app/backups"))
backup_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
sql_path = backup_dir / f"backup_postgresql_prod_{timestamp}.sql"
gz_path = Path(str(sql_path) + ".gz")
pg_env = os.environ.copy()
pg_env["PGPASSWORD"] = db_pass
cmd = ["pg_dump", "-h", db_host, "-p", db_port, "-U", db_user, "--no-owner", "--no-privileges", "-d", db_name, "-f", str(sql_path)]
result = subprocess.run(cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if result.returncode != 0:
    raise SystemExit("PG_DUMP_FAILED:" + result.stderr[-500:])
with open(sql_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
    shutil.copyfileobj(f_in, f_out)
sql_path.unlink()
print(str(gz_path))
"""
    command = (
        f"GV_REMOTE_CODE_DIR={REMOTE_CODE_DIR!r} "
        f"GV_REMOTE_BACKUP_DIR={REMOTE_BACKUP_DIR!r} "
        "python3 - <<'PY'\n" + remote_python + "\nPY"
    )
    stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", "replace").strip()
    error = stderr.read().decode("utf-8", "replace").strip()
    if exit_code != 0:
        raise RuntimeError(f"Falha ao gerar backup remoto: {error[-800:] or output[-800:]}")
    remote_file = output.splitlines()[-1].strip()
    print(f"  ✅ Backup remoto criado: {PurePosixPath(remote_file).name}")
    return remote_file


def download_database_backups(ssh, scp, required_remote_file=None):
    """Baixa backups do banco de dados"""
    print("\n[1/3] SINCRONIZANDO BACKUPS DO BANCO DE DADOS...")
    local_db_dir = os.path.join(LOCAL_BACKUP_DIR, "database")
    
    try:
        sftp = ssh.open_sftp()
        remote_files = sftp.listdir(REMOTE_BACKUP_DIR)
        backup_files = [f for f in remote_files if f.endswith('.gz') or f.endswith('.sql')]
        if required_remote_file:
            required_name = PurePosixPath(required_remote_file).name
            if required_name in backup_files:
                backup_files = [required_name] + [f for f in backup_files if f != required_name]
        
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
        protected = [PurePosixPath(required_remote_file).name] if required_remote_file else []
        removed = cleanup_old_backups(local_db_dir, "backup_", protected_files=protected)
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
    print("  BACKUP COMPLETO: CONFIGR → LOCAL")
    print("=" * 60)
    
    # Cria estrutura de pastas
    create_local_structure()
    
    try:
        # Conexão SSH
        print("\n🔌 Conectando ao servidor Configr...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": HOST,
            "port": PORT,
            "username": USER,
            "timeout": 30,
        }
        if KEY_PATH:
            connect_kwargs["key_filename"] = KEY_PATH
        elif PASSWORD:
            connect_kwargs["password"] = PASSWORD
        else:
            raise RuntimeError(
                "Credencial Configr ausente. Defina GV_CONFIGR_PASSWORD ou GV_CONFIGR_KEY_PATH."
            )

        ssh.connect(**connect_kwargs)
        print("  ✅ Conectado com sucesso!")
        
        # Cria cliente SCP
        with SCPClient(ssh.get_transport()) as scp:
            # 0. Gera backup novo no servidor de produção
            remote_database_backup = create_remote_database_backup(ssh)

            # 1. Backups do banco
            download_database_backups(ssh, scp, required_remote_file=remote_database_backup)
            
            # 2. Snapshot do código
            if is_truthy_env("GV_BACKUP_SKIP_CODE"):
                print("\n[2/3] Snapshot do código pulado por GV_BACKUP_SKIP_CODE=1")
            else:
                create_code_snapshot(ssh, scp)
            
            # 3. Arquivos de upload
            if is_truthy_env("GV_BACKUP_SKIP_UPLOADS"):
                print("\n[3/3] Uploads pulados por GV_BACKUP_SKIP_UPLOADS=1")
            else:
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
        return 1

if __name__ == "__main__":
    sys.exit(main())
