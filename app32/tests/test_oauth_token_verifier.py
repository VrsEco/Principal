from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import ssl
from threading import Event
from types import SimpleNamespace

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from jwt.exceptions import PyJWKClientError

from src.intelligence.security.oauth_token_verifier import (
    OAuthAccessTokenVerifier,
    OAuthTokenVerificationError,
    OAuthTokenVerifierSettings,
)
import src.intelligence.security.oauth_token_verifier as oauth_token_verifier


ISSUER = "https://auth.gestaoversus.com.br/realms/versus"
AUDIENCE = "https://mcp.gestaoversus.com.br"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"


class _StaticSigningKeyResolver:
    def __init__(self, public_key):
        self.public_key = public_key
        self.calls = 0

    def get_signing_key_from_jwt(self, token: str):
        self.calls += 1
        return SimpleNamespace(key=self.public_key)


class _UnavailableSigningKeyResolver:
    def __init__(self):
        self.calls = 0

    def get_signing_key_from_jwt(self, token: str):
        self.calls += 1
        raise PyJWKClientError("kid desconhecido")


class _BlockingUnavailableSigningKeyResolver(_UnavailableSigningKeyResolver):
    def __init__(self):
        super().__init__()
        self.started = Event()
        self.release = Event()

    def get_signing_key_from_jwt(self, token: str):
        self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=2)
        raise PyJWKClientError("kid desconhecido")


class _RotatingSigningKeyResolver:
    def __init__(self, public_keys):
        self.public_keys = public_keys
        self.calls = 0

    def get_signing_key_from_jwt(self, token: str):
        self.calls += 1
        kid = jwt.get_unverified_header(token)["kid"]
        return SimpleNamespace(key=self.public_keys[kid])


@pytest.fixture
def signing_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, _StaticSigningKeyResolver(private_key.public_key())


def _settings(**overrides) -> OAuthTokenVerifierSettings:
    values = {"issuer": ISSUER, "audience": AUDIENCE, "jwks_url": JWKS_URL}
    values.update(overrides)
    return OAuthTokenVerifierSettings(**values)


def _access_token(private_key, *, kid: str = "key-2026-09", **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "sub": "service:erp-bomix",
        "aud": [AUDIENCE, "account"],
        "azp": "erp-bomix",
        "scope": "mcp:access routine:read",
        "typ": "Bearer",
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def test_verifier_accepts_only_valid_configured_access_token(signing_material):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)

    verified = verifier.verify(_access_token(private_key))

    assert verified.issuer == ISSUER
    assert verified.subject == "service:erp-bomix"
    assert verified.audience == (AUDIENCE, "account")
    assert verified.client_id == "erp-bomix"
    assert verified.scopes == ("mcp:access", "routine:read")
    assert resolver.calls == 1


def test_verifier_does_not_assume_bearer_type_without_explicit_resource_profile(signing_material):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)

    verified = verifier.verify(_access_token(private_key, typ="at+jwt"))

    assert verified.subject == "service:erp-bomix"


def test_verifier_preserves_subject_exactly_for_persisted_identity_lookup(signing_material):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)

    verified = verifier.verify(_access_token(private_key, sub=" service:erp-bomix "))

    assert verified.subject == " service:erp-bomix "


def test_verifier_enforces_explicit_client_allowlist_when_resource_profile_requires_it(signing_material):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(
        _settings(allowed_client_ids=("erp-bomix",)),
        signing_key_resolver=resolver,
    )

    assert verifier.verify(_access_token(private_key)).client_id == "erp-bomix"
    with pytest.raises(OAuthTokenVerificationError, match="client_id.*não autorizado"):
        verifier.verify(_access_token(private_key, azp="unknown-client"))


def test_verifier_requires_resource_baseline_scope_without_granting_surface_access(signing_material):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)

    with pytest.raises(OAuthTokenVerificationError, match="scopes obrigatórios"):
        verifier.verify(_access_token(private_key, scope="routine:read"))


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"aud": "https://other.example"}, "access token rejeitado"),
        ({"iss": "https://other.example/realms/versus"}, "access token rejeitado"),
        ({"exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp())}, "access token rejeitado"),
        ({"nbf": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())}, "access token rejeitado"),
        ({"typ": "ID"}, "tipo do access token"),
    ],
)
def test_verifier_denies_wrong_issuer_audience_expiry_and_non_access_token(signing_material, claims, expected):
    private_key, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(
        _settings(expected_token_type="Bearer"),
        signing_key_resolver=resolver,
    )

    with pytest.raises(OAuthTokenVerificationError, match=expected):
        verifier.verify(_access_token(private_key, **claims))


def test_verifier_rejects_unsigned_or_disallowed_algorithm_before_jwks_resolution(signing_material):
    _, resolver = signing_material
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)
    unsigned = jwt.encode(
        {"iss": ISSUER, "sub": "service:erp-bomix", "aud": AUDIENCE, "exp": 9999999999, "typ": "Bearer"},
        key="",
        algorithm="none",
        headers={"kid": "key-2026-09"},
    )

    with pytest.raises(OAuthTokenVerificationError, match="algoritmo"):
        verifier.verify(unsigned)

    assert resolver.calls == 0


def test_verifier_limits_jwks_refresh_for_repeated_unknown_kid(signing_material):
    private_key, _ = signing_material
    resolver = _UnavailableSigningKeyResolver()
    ticks = iter((100.0, 101.0, 131.0))
    verifier = OAuthAccessTokenVerifier(
        _settings(jwks_refresh_cooldown_seconds=30),
        signing_key_resolver=resolver,
    )
    verifier._monotonic_provider = lambda: next(ticks)
    token = _access_token(private_key)

    with pytest.raises(OAuthTokenVerificationError, match="indisponível"):
        verifier.verify(token)
    with pytest.raises(OAuthTokenVerificationError, match="temporariamente"):
        verifier.verify(token)
    with pytest.raises(OAuthTokenVerificationError, match="indisponível"):
        verifier.verify(token)

    assert resolver.calls == 2


def test_verifier_serializes_concurrent_unknown_kid_refreshes(signing_material):
    private_key, _ = signing_material
    resolver = _BlockingUnavailableSigningKeyResolver()
    verifier = OAuthAccessTokenVerifier(
        _settings(jwks_refresh_cooldown_seconds=30),
        signing_key_resolver=resolver,
    )
    token = _access_token(private_key)

    def verify_message() -> str:
        try:
            verifier.verify(token)
        except OAuthTokenVerificationError as exc:
            return str(exc)
        raise AssertionError("token com kid indisponível deveria ser negado")

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(verify_message)
        assert resolver.started.wait(timeout=2)
        second = executor.submit(verify_message)
        resolver.release.set()
        messages = {first.result(timeout=2), second.result(timeout=2)}

    assert resolver.calls == 1
    assert "chave de assinatura indisponível" in messages
    assert "chave de assinatura indisponível temporariamente" in messages


def test_verifier_accepts_rotated_jwks_key_after_previous_kid_was_valid(signing_material):
    first_private_key, _ = signing_material
    second_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    resolver = _RotatingSigningKeyResolver(
        {
            "key-old": first_private_key.public_key(),
            "key-new": second_private_key.public_key(),
        }
    )
    verifier = OAuthAccessTokenVerifier(_settings(), signing_key_resolver=resolver)

    old_verified = verifier.verify(_access_token(first_private_key, kid="key-old"))
    new_verified = verifier.verify(_access_token(second_private_key, kid="key-new"))

    assert old_verified.subject == new_verified.subject == "service:erp-bomix"
    assert resolver.calls == 2


def test_verifier_settings_are_https_only_and_reject_unsafe_algorithm():
    with pytest.raises(ValueError, match="HTTPS"):
        _settings(jwks_url="http://idp.invalid/jwks")
    with pytest.raises(ValueError, match="algoritmo"):
        _settings(algorithms=("HS256",))
    with pytest.raises(ValueError, match="jwks_timeout_seconds"):
        _settings(jwks_timeout_seconds=0)
    with pytest.raises(ValueError, match="jwks_refresh_cooldown_seconds"):
        _settings(jwks_refresh_cooldown_seconds=0)
    with pytest.raises(ValueError, match="expected_token_type"):
        _settings(expected_token_type=" ")
    with pytest.raises(ValueError, match="allowed_client_ids"):
        _settings(allowed_client_ids=("erp-bomix", "erp-bomix"))


def test_verifier_settings_load_only_complete_strict_resource_server_profile():
    settings = OAuthTokenVerifierSettings.from_mapping(
        {
            "issuer": ISSUER,
            "audience": AUDIENCE,
            "jwks_url": JWKS_URL,
            "algorithms": "RS256,ES256",
            "expected_token_type": "Bearer",
            "allowed_client_ids": "erp-bomix,claude-remote",
            "required_scopes": "mcp:access",
            "jwks_refresh_cooldown_seconds": "20",
        }
    )

    assert settings.algorithms == ("RS256", "ES256")
    assert settings.expected_token_type == "Bearer"
    assert settings.allowed_client_ids == ("erp-bomix", "claude-remote")
    assert settings.required_scopes == ("mcp:access",)
    assert settings.jwks_refresh_cooldown_seconds == 20

    with pytest.raises(ValueError, match="issuer"):
        OAuthTokenVerifierSettings.from_mapping({"audience": AUDIENCE, "jwks_url": JWKS_URL})
    with pytest.raises(ValueError, match="allowed_client_ids"):
        OAuthTokenVerifierSettings.from_mapping(
            {"issuer": ISSUER, "audience": AUDIENCE, "jwks_url": JWKS_URL}
        )
    with pytest.raises(ValueError, match="allowed_client_ids"):
        OAuthTokenVerifierSettings.from_mapping(
            {"issuer": ISSUER, "audience": AUDIENCE, "jwks_url": JWKS_URL, "allowed_client_ids": "client, "}
        )


def test_verifier_uses_explicit_ca_bundle_without_disabling_tls_validation(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "local-test-ca")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    ca_bundle = tmp_path / "local-test-ca.pem"
    ca_bundle.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    captured = {}

    class _RecordingJwksClient:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(oauth_token_verifier, "PyJWKClient", _RecordingJwksClient)
    settings = _settings(ca_bundle_path=str(ca_bundle))
    OAuthAccessTokenVerifier(settings)

    assert captured["ssl_context"].verify_mode == ssl.CERT_REQUIRED


def test_verifier_rejects_missing_explicit_ca_bundle():
    with pytest.raises(ValueError, match="ca_bundle_path"):
        _settings(ca_bundle_path="C:/not-a-trust-anchor.pem")


def test_verifier_settings_reads_only_allowlisted_oidc_environment_names():
    settings = OAuthTokenVerifierSettings.from_prefixed_environ(
        {
            "APP32_MCP_OIDC_ISSUER": ISSUER,
            "APP32_MCP_OIDC_AUDIENCE": AUDIENCE,
            "APP32_MCP_OIDC_JWKS_URL": JWKS_URL,
            "APP32_MCP_OIDC_CA_BUNDLE": "",
            "APP32_MCP_OIDC_ALLOWED_CLIENT_IDS": "erp-bomix",
            "UNTRUSTED_ISSUER": "https://attacker.invalid",
        }
    )

    assert settings.issuer == ISSUER
    assert settings.allowed_client_ids == ("erp-bomix",)


def test_verifier_settings_reads_documented_ca_bundle_environment_name(tmp_path):
    ca_bundle = tmp_path / "local-ca.pem"
    ca_bundle.write_text("placeholder", encoding="utf-8")

    settings = OAuthTokenVerifierSettings.from_prefixed_environ(
        {
            "APP32_MCP_OIDC_ISSUER": ISSUER,
            "APP32_MCP_OIDC_AUDIENCE": AUDIENCE,
            "APP32_MCP_OIDC_JWKS_URL": JWKS_URL,
            "APP32_MCP_OIDC_ALLOWED_CLIENT_IDS": "erp-bomix",
            "APP32_MCP_OIDC_CA_BUNDLE": str(ca_bundle),
        }
    )

    assert settings.ca_bundle_path == str(ca_bundle)
