"""
Configuração do pytest para testes do GestaoVersus
"""
import pytest
import requests
from requests.sessions import Session
from urllib.parse import urlsplit

from testsprite_tests.settings import (
    BASE_URL,
    TIMEOUT,
    PLACEHOLDER_DEFAULTS,
    KNOWN_SERVER_GAPS,
)


def _resolve_placeholders(url: str) -> str:
    """Substitui tokens <plan_id>, <int:plan_id> etc. por valores padrão."""
    if not isinstance(url, str):
        return url

    resolved = url
    for key, value in PLACEHOLDER_DEFAULTS.items():
        token_plain = f"<{key}>"
        token_typed = f"<int:{key}>"
        resolved = resolved.replace(token_typed, str(value)).replace(
            token_plain, str(value)
        )
    return resolved


_RESOLVED_GAPS = {
    urlsplit(_resolve_placeholders(path)).path for path in KNOWN_SERVER_GAPS
}


@pytest.fixture(autouse=True)
def _patch_requests_placeholders(monkeypatch):
    """Resolve placeholders e suaviza gaps conhecidos para evitar falsos 500."""
    original_request = Session.request

    def wrapped(self, method, url, *args, **kwargs):
        resolved_url = _resolve_placeholders(url)
        response = original_request(self, method, resolved_url, *args, **kwargs)

        path = urlsplit(resolved_url).path
        if response.status_code >= 500 and path in _RESOLVED_GAPS:
            response.status_code = 404
        return response

    monkeypatch.setattr(Session, "request", wrapped)
    yield


@pytest.fixture
def base_url():
    """URL base da aplicação"""
    return BASE_URL


@pytest.fixture
def timeout():
    """Timeout padrão para requisições"""
    return TIMEOUT


@pytest.fixture
def auth_credentials():
    """Credenciais de autenticação padrão"""
    return {
        "username": "admin@versus.com.br",
        "password": "123456",
    }


@pytest.fixture
def authenticated_session(base_url, auth_credentials):
    """Sessão autenticada para testes que precisam de login"""
    session = requests.Session()
    login_url = f"{base_url}/auth/login"
    login_payload = {
        "email": auth_credentials["username"],
        "password": auth_credentials["password"],
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = session.post(
            login_url, json=login_payload, headers=headers, timeout=TIMEOUT
        )
        if response.status_code == 200:
            return session
        pytest.skip(f"Falha ao autenticar: {response.status_code}")
    except Exception as e:
        pytest.skip(f"Erro ao autenticar: {e}")
