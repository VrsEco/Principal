from __future__ import annotations

import json
import os
import sys
import asyncio
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
APP_DIR = ROOT_DIR / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app32.tests.e2e.config.environments import load_environment_settings


def _is_local_base_url(base_url: str) -> bool:
    hostname = urlparse(base_url).hostname or ""
    return hostname in {"127.0.0.1", "localhost", "::1"}


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
    if settings.environment_name == "DEV_FULL" and _is_local_base_url(base_url):
        from src.core.mcp_http_server import _healthz

        mcp_response = asyncio.run(_healthz(None))  # type: ignore[arg-type]
        payload = json.loads(mcp_response.body.decode("utf-8"))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(payload).encode("utf-8")  # noqa: SLF001
        response.headers["Content-Type"] = "application/json"
        route = "/healthz"
    else:
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
