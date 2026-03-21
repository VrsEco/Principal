from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description='Smoke de boot do create_app para investigação de incidentes.')
    parser.add_argument('--env', default='production', help='Ambiente passado para create_app (default: production)')
    args = parser.parse_args()

    print(f'[SMOKE] create_app env={args.env}')
    try:
        from app import create_app
        app = create_app(args.env)
        print('[OK] create_app executado com sucesso')
        print(f'[INFO] app_name={getattr(app, "name", "unknown")}')
        print(f'[INFO] blueprints={sorted(list(app.blueprints.keys()))[:20]}')
        return 0
    except Exception as exc:
        print(f'[FAIL] create_app falhou: {exc!r}')
        raise


if __name__ == '__main__':
    raise SystemExit(main())
