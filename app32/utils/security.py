import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app, jsonify, request


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_csv(name: str) -> list[str]:
    raw_value = os.environ.get(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_or_create_dev_secret() -> str:
    return os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)


def _limiter_store():
    store = current_app.extensions.setdefault(
        "simple_rate_limiter",
        defaultdict(deque),
    )
    return store


def get_request_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def consume_rate_limit(bucket: str, key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    store = _limiter_store()
    cache_key = f"{bucket}:{key}"
    entries = store[cache_key]
    while entries and entries[0] <= now - window_seconds:
        entries.popleft()
    if len(entries) >= limit:
        return False
    entries.append(now)
    return True


def rate_limit_exceeded_response(message: str = "Muitas tentativas. Tente novamente em instantes."):
    return jsonify({"success": False, "message": message}), 429


def is_safe_method() -> bool:
    return request.method.upper() not in UNSAFE_METHODS


def same_origin_verified() -> bool:
    if current_app.config.get("TESTING"):
        return True

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    host_url = request.host_url.rstrip("/")

    if origin:
        return origin.rstrip("/") == host_url
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return referer_origin == host_url
    return True


def webhook_secret_verified(*, expected_secret: str | None, header_names: list[str] | None = None, query_names: list[str] | None = None) -> bool:
    if not expected_secret:
        return True

    candidates: list[str] = []
    for header_name in header_names or []:
        header_value = request.headers.get(header_name)
        if header_value:
            candidates.append(header_value.strip())
    for query_name in query_names or []:
        query_value = request.args.get(query_name)
        if query_value:
            candidates.append(query_value.strip())

    return any(hmac.compare_digest(candidate, expected_secret) for candidate in candidates)


def normalize_relative_upload_path(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    value = str(relative_path).strip().replace("\\", "/")
    while value.startswith("/"):
        value = value[1:]
    if value.startswith("uploads/"):
        value = value[8:]
    normalized = Path(value).as_posix()
    if normalized in {"", "."} or normalized.startswith("../") or "/../" in normalized:
        return None
    return normalized
