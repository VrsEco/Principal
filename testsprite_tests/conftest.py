"""
Configuração do pytest para testes do GestaoVersus
"""
import pytest
import requests

BASE_URL = "http://localhost:5003"
TIMEOUT = 30

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
        "password": "123456"
    }

@pytest.fixture
def authenticated_session(base_url, auth_credentials):
    """Sessão autenticada para testes que precisam de login"""
    session = requests.Session()
    login_url = f"{base_url}/auth/login"
    login_payload = {
        "email": auth_credentials["username"],
        "password": auth_credentials["password"]
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = session.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)
        if response.status_code == 200:
            return session
        else:
            pytest.skip(f"Falha ao autenticar: {response.status_code}")
    except Exception as e:
        pytest.skip(f"Erro ao autenticar: {e}")

