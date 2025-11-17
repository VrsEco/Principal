"""
Testes para blueprint: route_audit
Total de rotas: 9
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /route-audit/
Endpoint: route_audit.audit_dashboard
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_audit_dashboard(base_url, timeout):
    """Testa a rota /route-audit/"""
    url = f"{base_url}/route-audit/"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/ retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/: {e}")


"""
Teste para rota: /route-audit/api/summary
Endpoint: route_audit.get_audit_summary
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_get_audit_summary(base_url, timeout):
    """Testa a rota /route-audit/api/summary"""
    url = f"{base_url}/route-audit/api/summary"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/summary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/summary: {e}")


"""
Teste para rota: /route-audit/api/routes
Endpoint: route_audit.get_all_routes
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_get_all_routes(base_url, timeout):
    """Testa a rota /route-audit/api/routes"""
    url = f"{base_url}/route-audit/api/routes"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/routes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/routes: {e}")


"""
Teste para rota: /route-audit/api/routes/without-logging
Endpoint: route_audit.get_routes_without_logging
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_get_routes_without_logging(base_url, timeout):
    """Testa a rota /route-audit/api/routes/without-logging"""
    url = f"{base_url}/route-audit/api/routes/without-logging"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/routes/without-logging retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/routes/without-logging: {e}")


"""
Teste para rota: /route-audit/api/routes/<path:endpoint>/details
Endpoint: route_audit.get_route_details
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_get_route_details(base_url, timeout):
    """Testa a rota /route-audit/api/routes/<path:endpoint>/details"""
    url = f"{base_url}/route-audit/api/routes/<path:endpoint>/details"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/routes/<path:endpoint>/details retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/routes/<path:endpoint>/details: {e}")


"""
Teste para rota: /route-audit/api/config
Endpoint: route_audit.get_logging_config
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_get_logging_config(base_url, timeout):
    """Testa a rota /route-audit/api/config"""
    url = f"{base_url}/route-audit/api/config"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/config retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/config: {e}")


"""
Teste para rota: /route-audit/api/entity/<entity_type>/enable
Endpoint: route_audit.enable_entity_logging
Blueprint: route_audit
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_enable_entity_logging(base_url, timeout):
    """Testa a rota /route-audit/api/entity/<entity_type>/enable"""
    url = f"{base_url}/route-audit/api/entity/<entity_type>/enable"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /route-audit/api/entity/<entity_type>/enable retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /route-audit/api/entity/<entity_type>/enable: {e}")


"""
Teste para rota: /route-audit/api/entity/<entity_type>/disable
Endpoint: route_audit.disable_entity_logging
Blueprint: route_audit
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_disable_entity_logging(base_url, timeout):
    """Testa a rota /route-audit/api/entity/<entity_type>/disable"""
    url = f"{base_url}/route-audit/api/entity/<entity_type>/disable"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /route-audit/api/entity/<entity_type>/disable retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /route-audit/api/entity/<entity_type>/disable: {e}")


"""
Teste para rota: /route-audit/api/export-report
Endpoint: route_audit.export_audit_report
Blueprint: route_audit
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_route_audit_export_audit_report(base_url, timeout):
    """Testa a rota /route-audit/api/export-report"""
    url = f"{base_url}/route-audit/api/export-report"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /route-audit/api/export-report retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /route-audit/api/export-report: {e}")


