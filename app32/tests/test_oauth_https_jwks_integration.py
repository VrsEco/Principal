"""Real loopback HTTPS/JWKS smoke without external network or persisted keys."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
from threading import Thread

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.intelligence.security.oauth_token_verifier import (
    OAuthAccessTokenVerifier,
    OAuthTokenVerificationError,
    OAuthTokenVerifierSettings,
)


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _start_https_jwks(tmp_path):
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tls_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(tls_key, hashes.SHA256())
    )
    cert_path = tmp_path / "loopback-ca.pem"
    key_path = tmp_path / "loopback-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        tls_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    numbers = signing_key.public_key().public_numbers()
    jwks = {
        "keys": [{
            "kty": "RSA", "kid": "audit-live-jwks", "use": "sig", "alg": "RS256",
            "n": _b64url_uint(numbers.n), "e": _b64url_uint(numbers.e),
        }]
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/jwks":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(jwks).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, signing_key, cert_path


def test_verifier_fetches_real_jwks_over_verified_loopback_https(tmp_path):
    server, thread, signing_key, cert_path = _start_https_jwks(tmp_path)
    try:
        issuer = f"https://localhost:{server.server_port}"
        settings = OAuthTokenVerifierSettings(
            issuer=issuer,
            audience="app32-mcp",
            jwks_url=f"{issuer}/jwks",
            ca_bundle_path=str(cert_path),
            allowed_client_ids=("codex-jwks-smoke",),
            required_scopes=("mcp:access",),
        )
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "iss": issuer,
                "sub": "service:https-jwks-smoke",
                "aud": "app32-mcp",
                "azp": "codex-jwks-smoke",
                "scope": "mcp:access mcp:user",
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            signing_key,
            algorithm="RS256",
            headers={"kid": "audit-live-jwks"},
        )

        verified = OAuthAccessTokenVerifier(settings).verify(token)
        assert verified.subject == "service:https-jwks-smoke"
        assert verified.client_id == "codex-jwks-smoke"
        assert verified.scopes == ("mcp:access", "mcp:user")

        wrong_audience = jwt.encode(
            {
                "iss": issuer, "sub": "service:https-jwks-smoke", "aud": "other",
                "scope": "mcp:access", "exp": now + timedelta(minutes=5),
            },
            signing_key,
            algorithm="RS256",
            headers={"kid": "audit-live-jwks"},
        )
        try:
            OAuthAccessTokenVerifier(settings).verify(wrong_audience)
        except OAuthTokenVerificationError:
            pass
        else:  # pragma: no cover - fail-closed contract
            raise AssertionError("wrong audience was accepted")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

