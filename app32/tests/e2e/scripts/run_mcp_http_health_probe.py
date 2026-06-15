from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.environments import load_environment_settings


@dataclass(frozen=True)
class MCPHTTPHealthProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def main() -> int:
    settings = load_environment_settings()
    base_url = (settings.base_url or os.environ.get("EXTERNAL_URL") or "https://app.gestaoversus.com.br").rstrip("/")
    route = "/mcp/healthz"
    response = requests.get(f"{base_url}{route}", timeout=settings.request_timeout_seconds)
    content_type = str(response.headers.get("Content-Type") or "")
    payload: dict[str, Any] | None = None
    try:
        payload = response.json()
    except Exception:
        payload = None
    success = response.ok and isinstance(payload, dict) and bool(payload)
    result = MCPHTTPHealthProbeResult(
        check_name="mcp.http_healthz",
        route=route,
        success=success,
        status_code=response.status_code,
        details={
            "content_type": content_type,
            "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "environment": settings.environment_name,
        },
    )
    print(json.dumps([asdict(result)], ensure_ascii=False, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
