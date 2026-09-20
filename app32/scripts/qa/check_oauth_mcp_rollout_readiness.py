"""Read-only OAuth MCP rollout preflight. Never prints secrets or tokens."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from services.oauth_mcp_rollout_readiness_service import (
    evaluate_oauth_mcp_rollout_readiness,
    probe_oauth_mcp_public_endpoints,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pilot", "cohort"), default="pilot")
    parser.add_argument("--live", action="store_true", help="Probe public OIDC/JWKS/resource metadata without a token.")
    args = parser.parse_args()
    result = evaluate_oauth_mcp_rollout_readiness(os.environ, mode=args.mode)
    payload = result.to_safe_dict()
    exit_code = 0 if result.ready else 2
    if args.live and result.ready:
        probe = probe_oauth_mcp_public_endpoints(os.environ)
        payload["live_probe"] = probe.to_safe_dict()
        if not probe.ready:
            exit_code = 3
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
