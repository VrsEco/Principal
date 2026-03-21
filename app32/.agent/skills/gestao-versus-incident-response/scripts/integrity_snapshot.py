from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Snapshot local de integridade para incidentes.')
    parser.add_argument('--files', nargs='*', default=['app.py', 'api/resources/process.py', 'api/routes/my_work.py', 'templates/modules/my_work/my_work_v2.html', 'static/js/my-work.js', 'models/__init__.py'])
    parser.add_argument('--git-status', action='store_true')
    args = parser.parse_args()

    payload = {'repo_root': str(REPO_ROOT), 'files': []}

    for rel in args.files:
        path = REPO_ROOT / rel.replace('/', '\\')
        item = {'path': rel, 'exists': path.exists()}
        if path.exists() and path.is_file():
            item['sha256'] = sha256_file(path)
            item['size'] = path.stat().st_size
        payload['files'].append(item)

    if args.git_status:
        try:
            result = subprocess.run(
                ['git', '-C', str(REPO_ROOT), '-c', 'safe.directory=C:/GestaoVersus', 'status', '--short'],
                capture_output=True,
                text=True,
                check=False,
            )
            payload['git_status'] = result.stdout.strip().splitlines()
            payload['git_status_code'] = result.returncode
        except Exception as exc:
            payload['git_status_error'] = repr(exc)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
