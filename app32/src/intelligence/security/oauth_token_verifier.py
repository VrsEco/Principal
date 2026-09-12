"""Validação local e fail-closed de access tokens OIDC para o APP32.

O módulo ainda não é conectado ao transporte MCP. Ele não faz discovery por
dados do token, não provisiona identidades e não decide acesso a tenant. Sua
única responsabilidade é aceitar ou rejeitar um access JWT contra a
configuração explícita do resource server e expor claims mínimos já validados.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import ssl
from threading import Lock
from time import monotonic
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError


class OAuthTokenVerificationError(ValueError):
    """Erro seguro para resposta 401; nunca deve carregar o token bruto."""


class SigningKeyResolver(Protocol):
    """Contrato mínimo de ``PyJWKClient`` para permitir teste determinístico."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


@dataclass(frozen=True)
class OAuthTokenVerifierSettings:
    """Configuração imutável do resource server OIDC/Keycloak."""

    issuer: str
    audience: str
    jwks_url: str
    algorithms: tuple[str, ...] = ("RS256",)
    leeway_seconds: int = 30
    jwks_timeout_seconds: int = 5
    jwks_refresh_cooldown_seconds: int = 15
    jwks_unknown_kid_cache_size: int = 64
    ca_bundle_path: str | None = None
    expected_token_type: str | None = None
    # Resource servers que aceitam Dynamic Client Registration não podem
    # conhecer antecipadamente o ``azp`` público e efêmero de cada cliente
    # nativo. A allowlist segue disponível para perfis estáticos; quando vazia,
    # a confiança continua ancorada em issuer, JWKS, audience, escopos e
    # resolução persistida de principal — nunca no client_id público.
    allowed_client_ids: tuple[str, ...] = ()
    required_scopes: tuple[str, ...] = ("mcp:access",)

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value and value == value.strip() for value in (self.issuer, self.audience, self.jwks_url)):
            raise ValueError("issuer, audience e jwks_url são obrigatórios")
        if urlparse(self.issuer).scheme != "https" or urlparse(self.jwks_url).scheme != "https":
            raise ValueError("issuer e jwks_url devem usar HTTPS")
        if not self.algorithms or any(algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} for algorithm in self.algorithms):
            raise ValueError("algoritmo JWT não permitido")
        if self.leeway_seconds < 0 or self.leeway_seconds > 300:
            raise ValueError("leeway_seconds deve estar entre 0 e 300")
        if self.jwks_timeout_seconds < 1 or self.jwks_timeout_seconds > 30:
            raise ValueError("jwks_timeout_seconds deve estar entre 1 e 30")
        if self.jwks_refresh_cooldown_seconds < 1 or self.jwks_refresh_cooldown_seconds > 300:
            raise ValueError("jwks_refresh_cooldown_seconds deve estar entre 1 e 300")
        if self.jwks_unknown_kid_cache_size < 1 or self.jwks_unknown_kid_cache_size > 512:
            raise ValueError("jwks_unknown_kid_cache_size deve estar entre 1 e 512")
        if self.ca_bundle_path is not None:
            if (
                not isinstance(self.ca_bundle_path, str)
                or not self.ca_bundle_path
                or self.ca_bundle_path != self.ca_bundle_path.strip()
                or not Path(self.ca_bundle_path).is_file()
            ):
                raise ValueError("ca_bundle_path deve apontar para um arquivo existente")
        if self.expected_token_type is not None and (
            not isinstance(self.expected_token_type, str)
            or not self.expected_token_type
            or self.expected_token_type != self.expected_token_type.strip()
        ):
            raise ValueError("expected_token_type deve ser texto não vazio ou None")
        if any(
            not isinstance(client_id, str) or not client_id or client_id != client_id.strip()
            for client_id in self.allowed_client_ids
        ):
            raise ValueError("allowed_client_ids não pode conter valores vazios")
        if len(set(self.allowed_client_ids)) != len(self.allowed_client_ids):
            raise ValueError("allowed_client_ids não pode conter duplicidades")
        if not self.required_scopes or any(
            not isinstance(scope, str) or not scope or scope != scope.strip()
            for scope in self.required_scopes
        ):
            raise ValueError("required_scopes deve conter scopes não vazios")
        if len(set(self.required_scopes)) != len(self.required_scopes):
            raise ValueError("required_scopes não pode conter duplicidades")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "OAuthTokenVerifierSettings":
        """Monta perfil explícito sem consultar discovery ou token não confiável.

        O chamador decide a origem segura da configuração (secret manager,
        variáveis de ambiente injetadas ou arquivo de homologação). Ausência ou
        formato ambíguo falham antes de qualquer chamada ao JWKS.
        """

        def required(name: str) -> str:
            value = values.get(name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"configuração {name} obrigatória e inválida")
            return value

        def optional_csv(name: str) -> tuple[str, ...]:
            value = values.get(name, "")
            if value in (None, ""):
                return ()
            if not isinstance(value, str):
                raise ValueError(f"configuração {name} inválida")
            return tuple(value.split(","))

        def optional_int(name: str, default: int) -> int:
            value = values.get(name)
            if value in (None, ""):
                return default
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise ValueError(f"configuração {name} inválida")
            text_value = str(value)
            if not text_value.isdigit():
                raise ValueError(f"configuração {name} inválida")
            return int(text_value)

        expected_token_type = values.get("expected_token_type")
        if expected_token_type in (None, ""):
            expected_token_type = None
        return cls(
            issuer=required("issuer"),
            audience=required("audience"),
            jwks_url=required("jwks_url"),
            algorithms=optional_csv("algorithms") or ("RS256",),
            leeway_seconds=optional_int("leeway_seconds", 30),
            jwks_timeout_seconds=optional_int("jwks_timeout_seconds", 5),
            jwks_refresh_cooldown_seconds=optional_int("jwks_refresh_cooldown_seconds", 15),
            jwks_unknown_kid_cache_size=optional_int("jwks_unknown_kid_cache_size", 64),
            ca_bundle_path=values.get("ca_bundle_path") or None,
            expected_token_type=expected_token_type,
            allowed_client_ids=optional_csv("allowed_client_ids"),
            required_scopes=optional_csv("required_scopes") or ("mcp:access",),
        )

    @classmethod
    def from_prefixed_environ(
        cls,
        environ: Mapping[str, Any],
        *,
        prefix: str = "APP32_MCP_OIDC_",
    ) -> "OAuthTokenVerifierSettings":
        """Lê somente nomes de configuração permitidos para o resource server.

        Não habilita OAuth nem lê configuração de issuer/JWKS de headers,
        query ou claims. O transporte MCP continuará decidindo, em R05, se a
        coorte OAuth foi explicitamente habilitada.
        """

        field_names = (
            "issuer",
            "audience",
            "jwks_url",
            "algorithms",
            "leeway_seconds",
            "jwks_timeout_seconds",
            "jwks_refresh_cooldown_seconds",
            "jwks_unknown_kid_cache_size",
            "ca_bundle_path",
            "expected_token_type",
            "allowed_client_ids",
            "required_scopes",
        )
        values = {field_name: environ.get(f"{prefix}{field_name.upper()}") for field_name in field_names}
        # O contrato externo publicado desde R04 usa ``CA_BUNDLE``. Preservar
        # ``CA_BUNDLE_PATH`` apenas como alias de compatibilidade evita que um
        # profile local aparentemente válido silenciosamente perca sua CA e
        # passe a depender do trust store global.
        values["ca_bundle_path"] = (
            environ.get(f"{prefix}CA_BUNDLE")
            or environ.get(f"{prefix}CA_BUNDLE_PATH")
        )
        return cls.from_mapping(values)


@dataclass(frozen=True)
class VerifiedOAuthAccessToken:
    """Claims já assinados e validados, sem reter o JWT original."""

    issuer: str
    subject: str
    audience: tuple[str, ...]
    client_id: str | None
    scopes: tuple[str, ...]
    expires_at: int


def _claim_as_text(value: Any, *, claim: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise OAuthTokenVerificationError(f"claim {claim} inválida")
    # ``iss``/``sub`` são identificadores, não labels: sua normalização pode
    # fundir dois valores distintos antes do vínculo exato no APP32.
    return value


def _claim_as_scopes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(scope for scope in value.split() if scope)
    if isinstance(value, (list, tuple)) and all(isinstance(scope, str) and scope.strip() for scope in value):
        return tuple(scope.strip() for scope in value)
    raise OAuthTokenVerificationError("claim scope inválida")


def _claim_as_audience(value: Any) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, (list, tuple)) and value and all(isinstance(item, str) and item.strip() for item in value):
        return tuple(item.strip() for item in value)
    raise OAuthTokenVerificationError("claim aud inválida")


class OAuthAccessTokenVerifier:
    """Verifica assinatura, issuer, audience e temporalidade com JWKS conhecido."""

    def __init__(
        self,
        settings: OAuthTokenVerifierSettings,
        *,
        signing_key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        self.settings = settings
        ssl_context = (
            ssl.create_default_context(cafile=settings.ca_bundle_path)
            if settings.ca_bundle_path is not None
            else None
        )
        self._signing_key_resolver = signing_key_resolver or PyJWKClient(
            settings.jwks_url,
            cache_jwk_set=True,
            lifespan=300,
            timeout=settings.jwks_timeout_seconds,
            ssl_context=ssl_context,
        )
        # PyJWKClient já mantém as chaves válidas em cache. Este gate adiciona
        # serialização e backoff limitado para falhas/kids desconhecidos, que
        # de outro modo podem provocar rajada de refresh contra o IdP.
        self._jwks_lock = Lock()
        self._unknown_kid_until: OrderedDict[str, float] = OrderedDict()
        self._monotonic_provider: Callable[[], float] = monotonic

    def _resolve_signing_key(self, token: str, kid: str) -> Any:
        now = self._monotonic_provider()
        with self._jwks_lock:
            retry_after = self._unknown_kid_until.get(kid)
            if retry_after is not None and retry_after > now:
                raise OAuthTokenVerificationError("chave de assinatura indisponível temporariamente")
            if retry_after is not None:
                self._unknown_kid_until.pop(kid, None)
            try:
                signing_key = self._signing_key_resolver.get_signing_key_from_jwt(token)
            except Exception as exc:
                self._unknown_kid_until[kid] = now + self.settings.jwks_refresh_cooldown_seconds
                self._unknown_kid_until.move_to_end(kid)
                while len(self._unknown_kid_until) > self.settings.jwks_unknown_kid_cache_size:
                    self._unknown_kid_until.popitem(last=False)
                raise OAuthTokenVerificationError("chave de assinatura indisponível") from exc
            self._unknown_kid_until.pop(kid, None)
            return signing_key

    def verify(self, token: str) -> VerifiedOAuthAccessToken:
        """Aceita apenas access JWT assinado pelo issuer configurado.

        A URL de JWKS vem exclusivamente da configuração do servidor. Nenhuma
        claim não verificada (como ``jku``) participa da seleção de chave.
        """

        if not isinstance(token, str) or not token.strip():
            raise OAuthTokenVerificationError("access token ausente ou inválido")
        normalized_token = token.strip()
        try:
            header = jwt.get_unverified_header(normalized_token)
        except InvalidTokenError as exc:
            raise OAuthTokenVerificationError("header do access token inválido") from exc

        algorithm = header.get("alg")
        if algorithm not in self.settings.algorithms:
            raise OAuthTokenVerificationError("algoritmo do access token não permitido")
        if not isinstance(header.get("kid"), str) or not header["kid"].strip():
            raise OAuthTokenVerificationError("access token sem kid")
        kid = header["kid"]

        try:
            signing_key = self._resolve_signing_key(normalized_token, kid)
            claims = jwt.decode(
                normalized_token,
                signing_key.key,
                algorithms=list(self.settings.algorithms),
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                leeway=self.settings.leeway_seconds,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except OAuthTokenVerificationError:
            raise
        except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
            raise OAuthTokenVerificationError("access token rejeitado") from exc

        # O perfil do realm define se ``typ`` é aplicável (Keycloak pode usar
        # valores distintos de Bearer). Nunca tratá-lo como universal: quando
        # contratado, a expectativa vem da configuração do resource server.
        if (
            self.settings.expected_token_type is not None
            and claims.get("typ") != self.settings.expected_token_type
        ):
            raise OAuthTokenVerificationError("tipo do access token não corresponde ao perfil configurado")
        expires_at = claims.get("exp")
        if isinstance(expires_at, bool) or not isinstance(expires_at, int):
            raise OAuthTokenVerificationError("claim exp inválida")
        client_id_claim = claims["azp"] if "azp" in claims else claims.get("client_id")
        client_id = _claim_as_text(client_id_claim, claim="azp")
        if self.settings.allowed_client_ids and client_id not in self.settings.allowed_client_ids:
            raise OAuthTokenVerificationError("client_id do access token não autorizado para este resource server")
        scopes = _claim_as_scopes(claims.get("scope"))
        if not set(self.settings.required_scopes).issubset(scopes):
            raise OAuthTokenVerificationError("access token sem scopes obrigatórios do resource server")
        return VerifiedOAuthAccessToken(
            issuer=_claim_as_text(claims.get("iss"), claim="iss", required=True),
            subject=_claim_as_text(claims.get("sub"), claim="sub", required=True),
            audience=_claim_as_audience(claims.get("aud")),
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
        )
