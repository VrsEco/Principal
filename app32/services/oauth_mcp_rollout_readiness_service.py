"""Fail-closed readiness gate for the controlled OAuth MCP rollout."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import ssl
from typing import Mapping
from urllib.request import Request, urlopen
from urllib.parse import urlparse


def _enabled(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _csv(value: object) -> tuple[str, ...]:
    return tuple(item.strip() for item in str(value or "").split(",") if item.strip())


@dataclass(frozen=True)
class OAuthMcpRolloutReadiness:
    ready: bool
    mode: str
    checks: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "mode": self.mode,
            "checks": list(self.checks),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class OAuthMcpEndpointProbe:
    ready: bool
    checks: tuple[str, ...]
    blockers: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "checks": list(self.checks), "blockers": list(self.blockers)}


def evaluate_oauth_mcp_rollout_readiness(
    environ: Mapping[str, object], *, mode: str = "pilot"
) -> OAuthMcpRolloutReadiness:
    """Validate server-owned configuration without reading or exposing tokens."""

    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in {"pilot", "cohort"}:
        raise ValueError("mode must be pilot or cohort")

    blockers: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    def require_flag(name: str) -> None:
        if _enabled(environ.get(name)):
            checks.append(f"{name}=enabled")
        else:
            blockers.append(f"{name} must be enabled")

    require_flag("APP32_MCP_USE_PRINCIPAL_GRANTS")
    if normalized_mode == "pilot":
        require_flag("APP32_MCP_OIDC_PILOT_ROUTE_ENABLED")
        enabled_surfaces = set(_csv(environ.get("APP32_MCP_OIDC_ENABLED_SURFACES")))
        if _enabled(environ.get("APP32_MCP_HTTP_ENABLE_OAUTH")) and "user" in enabled_surfaces:
            blockers.append("pilot cannot replace the legacy user surface")
        else:
            checks.append("legacy user surface preserved")
    else:
        require_flag("APP32_MCP_HTTP_ENABLE_OAUTH")
        enabled_surfaces = set(_csv(environ.get("APP32_MCP_OIDC_ENABLED_SURFACES")))
        if not enabled_surfaces:
            blockers.append("APP32_MCP_OIDC_ENABLED_SURFACES must name an explicit cohort")
        else:
            checks.append("explicit OAuth surface cohort configured")

    for name in (
        "APP32_MCP_OIDC_ISSUER",
        "APP32_MCP_OIDC_AUDIENCE",
        "APP32_MCP_OIDC_JWKS_URL",
        "APP32_MCP_PUBLIC_BASE_URL",
    ):
        value = str(environ.get(name) or "").strip()
        if not value:
            blockers.append(f"{name} is required")
            continue
        if name != "APP32_MCP_OIDC_AUDIENCE" and urlparse(value).scheme != "https":
            blockers.append(f"{name} must use HTTPS")
            continue
        checks.append(f"{name}=configured")

    algorithms = _csv(environ.get("APP32_MCP_OIDC_ALGORITHMS") or "RS256")
    if not algorithms or any(item not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} for item in algorithms):
        blockers.append("APP32_MCP_OIDC_ALGORITHMS contains a disallowed algorithm")
    else:
        checks.append("asymmetric JWT algorithms only")

    required_scopes = set(_csv(environ.get("APP32_MCP_OIDC_REQUIRED_SCOPES") or "mcp:access"))
    if "mcp:access" not in required_scopes:
        blockers.append("APP32_MCP_OIDC_REQUIRED_SCOPES must include mcp:access")
    else:
        checks.append("baseline mcp:access scope required")

    if not _csv(environ.get("APP32_MCP_OIDC_ALLOWED_CLIENT_IDS")):
        warnings.append("client allowlist is empty; acceptable only for approved dynamic registration")
    else:
        checks.append("OAuth client allowlist configured")

    ca_bundle = str(environ.get("APP32_MCP_OIDC_CA_BUNDLE") or "").strip()
    if ca_bundle:
        if Path(ca_bundle).is_file():
            checks.append("custom CA bundle exists")
        else:
            blockers.append("APP32_MCP_OIDC_CA_BUNDLE does not exist")
    else:
        checks.append("system CA trust store selected")

    return OAuthMcpRolloutReadiness(
        ready=not blockers,
        mode=normalized_mode,
        checks=tuple(checks),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def probe_oauth_mcp_public_endpoints(
    environ: Mapping[str, object], *, timeout_seconds: int = 5, opener=urlopen
) -> OAuthMcpEndpointProbe:
    """Probe only public metadata/JWKS over verified TLS; never sends a token."""

    readiness = evaluate_oauth_mcp_rollout_readiness(environ, mode="pilot")
    if not readiness.ready:
        return OAuthMcpEndpointProbe(False, (), ("configuration readiness failed",))

    issuer = str(environ["APP32_MCP_OIDC_ISSUER"]).rstrip("/")
    jwks_url = str(environ["APP32_MCP_OIDC_JWKS_URL"])
    public_base = str(environ["APP32_MCP_PUBLIC_BASE_URL"]).rstrip("/")
    ca_bundle = str(environ.get("APP32_MCP_OIDC_CA_BUNDLE") or "").strip() or None
    context = ssl.create_default_context(cafile=ca_bundle)
    checks: list[str] = []
    blockers: list[str] = []

    def fetch_json(url: str) -> dict[str, object] | None:
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "app32-oauth-preflight/1"})
            with opener(request, context=context, timeout=timeout_seconds) as response:
                if getattr(response, "status", 200) != 200:
                    blockers.append(f"endpoint returned non-200: {url}")
                    return None
                raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                blockers.append(f"endpoint response too large: {url}")
                return None
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON root is not an object")
            return payload
        except Exception:
            blockers.append(f"endpoint unavailable or invalid: {url}")
            return None

    discovery_url = f"{issuer}/.well-known/openid-configuration"
    discovery = fetch_json(discovery_url)
    if discovery is not None:
        if discovery.get("issuer") != issuer or discovery.get("jwks_uri") != jwks_url:
            blockers.append("OIDC discovery issuer/jwks_uri differs from server configuration")
        else:
            checks.append("OIDC discovery matches configured issuer and JWKS")

    jwks = fetch_json(jwks_url)
    if jwks is not None:
        keys = jwks.get("keys")
        if not isinstance(keys, list) or not keys or not all(
            isinstance(key, dict) and key.get("kid") and key.get("kty") for key in keys
        ):
            blockers.append("JWKS has no usable keyed signing material")
        else:
            checks.append("JWKS exposes keyed signing material")

    metadata_url = f"{public_base}/.well-known/oauth-protected-resource/mcp/pilot/user"
    metadata = fetch_json(metadata_url)
    if metadata is not None:
        expected_resource = f"{public_base}/mcp/pilot/user"
        authorization_servers = metadata.get("authorization_servers")
        if metadata.get("resource") != expected_resource or not isinstance(authorization_servers, list) or issuer not in authorization_servers:
            blockers.append("protected-resource metadata differs from pilot contract")
        else:
            checks.append("protected-resource metadata matches pilot contract")

    return OAuthMcpEndpointProbe(not blockers, tuple(checks), tuple(blockers))
