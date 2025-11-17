"""
Testes para blueprint: logs
Total de rotas: 6
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /logs/
Endpoint: logs.list_logs
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_list_logs(base_url, timeout):
    """Testa a rota /logs/"""
    url = f"{base_url}/logs/"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/ retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/: {e}")


"""
Teste para rota: /logs/stats
Endpoint: logs.get_log_stats
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_get_log_stats(base_url, timeout):
    """Testa a rota /logs/stats"""
    url = f"{base_url}/logs/stats"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/stats retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/stats: {e}")


"""
Teste para rota: /logs/dashboard
Endpoint: logs.logs_dashboard
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_logs_dashboard(base_url, timeout):
    """Testa a rota /logs/dashboard"""
    url = f"{base_url}/logs/dashboard"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/dashboard retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/dashboard: {e}")


"""
Teste para rota: /logs/user-activity
Endpoint: logs.user_activity
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_user_activity(base_url, timeout):
    """Testa a rota /logs/user-activity"""
    url = f"{base_url}/logs/user-activity"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/user-activity retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/user-activity: {e}")


"""
Teste para rota: /logs/entity-activity/<entity_type>/<entity_id>
Endpoint: logs.entity_activity
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_entity_activity(base_url, timeout):
    """Testa a rota /logs/entity-activity/<entity_type>/<entity_id>"""
    url = f"{base_url}/logs/entity-activity/<entity_type>/<entity_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/entity-activity/<entity_type>/<entity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/entity-activity/<entity_type>/<entity_id>: {e}")


"""
Teste para rota: /logs/export
Endpoint: logs.export_logs
Blueprint: logs
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_logs_export_logs(base_url, timeout):
    """Testa a rota /logs/export"""
    url = f"{base_url}/logs/export"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /logs/export retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /logs/export: {e}")


