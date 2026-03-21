from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.deploy.configr_remote_helper import APP_DIR, connect_ssh


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Compara arquivos locais x produção para investigação de incidentes.')
    parser.add_argument('--files', nargs='+', required=True, help='Lista de paths relativos ao repo/app32')
    args = parser.parse_args()

    ssh = connect_ssh()
    sftp = ssh.open_sftp()
    try:
        for rel in args.files:
            local_path = REPO_ROOT / rel.replace('/', '\\')
            remote_path = f"{APP_DIR}/{rel}"

            print(f'FILE {rel}')
            if not local_path.exists():
                print('  local_exists: False')
                print('  remote_path:', remote_path)
                print('---')
                continue

            local_bytes = local_path.read_bytes()
            local_hash = sha256_bytes(local_bytes)
            print('  local_exists: True')
            print('  local_sha256:', local_hash)
            print('  remote_path:', remote_path)

            try:
                with sftp.open(remote_path, 'rb') as fh:
                    remote_bytes = fh.read()
                remote_hash = sha256_bytes(remote_bytes)
                print('  remote_exists: True')
                print('  remote_sha256:', remote_hash)
                print('  hashes_match:', local_hash == remote_hash)
            except Exception as exc:
                print('  remote_exists: False')
                print('  remote_error:', repr(exc))
            print('---')
        return 0
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == '__main__':
    raise SystemExit(main())
