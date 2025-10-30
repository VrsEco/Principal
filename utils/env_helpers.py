"""
Helpers to normalize environment-dependent values.

We mainly use these helpers to adjust database hosts when the application
runs outside Docker on Windows, where ``host.docker.internal`` may not be
reachable and psycopg2 fails early with UnicodeDecodeError.
"""

from __future__ import annotations

import os

_DOCKER_SPECIAL_HOST = "host.docker.internal"
_DEFAULT_LOCAL_HOST = "localhost"


def _is_truthy(value: str | None) -> bool:
    """Return True for common truthy string values."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def running_inside_docker() -> bool:
    """Best-effort detection whether the code executes inside a container."""
    if _is_truthy(os.environ.get("RUNNING_IN_DOCKER")):
        return True
    # Docker for Linux places this file in the container root.
    return os.path.exists("/.dockerenv")


def normalize_docker_host(host: str | None) -> str:
    """
    Normalize special Docker hostnames for environments outside containers.

    When the application runs directly on Windows or macOS, using
    ``host.docker.internal`` often fails (and psycopg2 may even raise
    UnicodeDecodeError before surfacing the real connection error).
    For those cases we transparently fall back to ``localhost`` unless the
    caller explicitly forces the Docker hostname.
    """
    value = (host or "").strip()
    if not value:
        return _DEFAULT_LOCAL_HOST

    if value.lower() != _DOCKER_SPECIAL_HOST:
        return value

    if running_inside_docker():
        return value

    if _is_truthy(os.environ.get("PEV_FORCE_DOCKER_HOST")):
        return value

    fallback = os.environ.get("PEV_FALLBACK_DB_HOST", _DEFAULT_LOCAL_HOST).strip()
    return fallback or _DEFAULT_LOCAL_HOST


def normalize_database_url(url: str | None) -> str | None:
    """
    Replace Docker-specific host aliases with a local fallback when needed.
    """
    if not url or _DOCKER_SPECIAL_HOST not in url:
        return url

    replacement = normalize_docker_host(_DOCKER_SPECIAL_HOST)
    if replacement == _DOCKER_SPECIAL_HOST:
        return url
    return url.replace(_DOCKER_SPECIAL_HOST, replacement)
