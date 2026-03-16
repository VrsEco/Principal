from __future__ import annotations

import argparse
import hashlib
import posixpath
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR, BASE_DIR

DEFAULT_FILES = [
    'api/routes/agents.py',
    'api/routes/meetings.py',
    'api/routes/users.py',
    'api/resources/meeting.py',
    'src/intelligence/rag.py',
    'config.py',
    'templates/partials/sidebar_standard.html',
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Push cirúrgico de arquivos seguros para o Configr.')
    parser.add_argument('--apply', action='store_true', help='Aplica de fato; sem isso, roda em dry-run.')
    parser.add_argument('--source-root', default=str(REPO_ROOT), help='Diretório raiz de onde os arquivos serão lidos.')
    parser.add_argument('--files', nargs='*', default=DEFAULT_FILES)
    args = parser.parse_args()

    app_root = Path(args.source_root).resolve()
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    remote_backup_root = posixpath.join(BASE_DIR, 'predeploy_snapshots', f'surgical_{stamp}', 'files')

    print(f'[INFO] Modo: {"APPLY" if args.apply else "DRY-RUN"}')
    print(f'[INFO] Backup remoto alvo: {remote_backup_root}')

    ssh = connect_ssh()
    sftp = ssh.open_sftp()
    try:
        for rel in args.files:
            local_path = app_root / rel.replace('/', '\\')
            if not local_path.exists():
                raise FileNotFoundError(f'Arquivo local não encontrado: {local_path}')

            remote_path = posixpath.join(APP_DIR, rel)
            remote_dir = posixpath.dirname(remote_path)
            remote_tmp = remote_path + '.codex_tmp'
            remote_backup = posixpath.join(remote_backup_root, rel)
            remote_backup_dir = posixpath.dirname(remote_backup)

            content = local_path.read_bytes()
            local_hash = sha256_bytes(content)
            print(f'FILE {rel}')
            print(f'  local sha256: {local_hash}')

            mkdir_cmd = f"mkdir -p '{remote_dir}' '{remote_backup_dir}'"
            ssh.exec_command(mkdir_cmd)[1].channel.recv_exit_status()

            if args.apply:
                try:
                    sftp.get(remote_path, str(local_path.parent / (local_path.name + '.remote_backup')))
                except Exception:
                    pass

                ssh.exec_command(f"if [ -f '{remote_path}' ]; then cp '{remote_path}' '{remote_backup}'; fi")[1].channel.recv_exit_status()
                with sftp.open(remote_tmp, 'wb') as fh:
                    fh.write(content)
                ssh.exec_command(f"mv '{remote_tmp}' '{remote_path}'")[1].channel.recv_exit_status()
                print('  status: aplicado com backup remoto')
            else:
                print(f'  remote: {remote_path}')
                print('  status: somente planejado')

        print('[OK] Processo concluído.')
        return 0
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == '__main__':
    raise SystemExit(main())
