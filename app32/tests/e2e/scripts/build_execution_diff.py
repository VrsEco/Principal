from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.environments import load_environment_settings
from app32.tests.e2e.core.execution_history import compare_manifests, latest_manifests, load_manifest


def main() -> int:
    settings = load_environment_settings()
    manifests = latest_manifests(settings.outputs_dir)
    if len(manifests) < 2:
        print(json.dumps({"status": "insufficient_history"}, ensure_ascii=False, indent=2))
        return 0
    current = load_manifest(manifests[0])
    previous = load_manifest(manifests[1])
    print(json.dumps(compare_manifests(previous, current), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
