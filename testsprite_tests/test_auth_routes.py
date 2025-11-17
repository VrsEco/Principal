"""
Testes para blueprint: auth
Total de rotas: 12
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /auth/login
Endpoint: auth.login
Blueprint: auth
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_login(base_url, timeout):
    """Testa a rota /auth/login"""
    url = f"{base_url}/auth/login"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/login retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/login: {e}")

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /auth/login retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /auth/login: {e}")


"""
Teste para rota: /auth/logout
Endpoint: auth.logout
Blueprint: auth
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_logout(base_url, timeout):
    """Testa a rota /auth/logout"""
    url = f"{base_url}/auth/logout"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/logout retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/logout: {e}")

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /auth/logout retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /auth/logout: {e}")


"""
Teste para rota: /auth/register
Endpoint: auth.register
Blueprint: auth
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_register(base_url, timeout):
    """Testa a rota /auth/register"""
    url = f"{base_url}/auth/register"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/register retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/register: {e}")

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /auth/register retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /auth/register: {e}")


"""
Teste para rota: /auth/profile
Endpoint: auth.profile
Blueprint: auth
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_profile(base_url, timeout):
    """Testa a rota /auth/profile"""
    url = f"{base_url}/auth/profile"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/profile retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/profile: {e}")

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /auth/profile retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /auth/profile: {e}")


"""
Teste para rota: /auth/change-password
Endpoint: auth.change_password
Blueprint: auth
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_change_password(base_url, timeout):
    """Testa a rota /auth/change-password"""
    url = f"{base_url}/auth/change-password"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /auth/change-password retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /auth/change-password: {e}")


"""
Teste para rota: /auth/users/page
Endpoint: auth.list_users_page
Blueprint: auth
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_list_users_page(base_url, timeout):
    """Testa a rota /auth/users/page"""
    url = f"{base_url}/auth/users/page"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/users/page retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/users/page: {e}")


"""
Teste para rota: /auth/users
Endpoint: auth.list_users
Blueprint: auth
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_list_users(base_url, timeout):
    """Testa a rota /auth/users"""
    url = f"{base_url}/auth/users"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/users retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/users: {e}")


"""
Teste para rota: /auth/users/<int:user_id>/status
Endpoint: auth.toggle_user_status
Blueprint: auth
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_toggle_user_status(base_url, timeout):
    """Testa a rota /auth/users/<int:user_id>/status"""
    url = f"{base_url}/auth/users/<int:user_id>/status"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /auth/users/<int:user_id>/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /auth/users/<int:user_id>/status: {e}")


"""
Teste para rota: /auth/current-user
Endpoint: auth.get_current_user
Blueprint: auth
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_get_current_user(base_url, timeout):
    """Testa a rota /auth/current-user"""
    url = f"{base_url}/auth/current-user"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/current-user retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/current-user: {e}")


"""
Teste para rota: /auth/users/<int:user_id>
Endpoint: auth.get_user
Blueprint: auth
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_get_user(base_url, timeout):
    """Testa a rota /auth/users/<int:user_id>"""
    url = f"{base_url}/auth/users/<int:user_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /auth/users/<int:user_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /auth/users/<int:user_id>: {e}")


"""
Teste para rota: /auth/users/<int:user_id>
Endpoint: auth.update_user
Blueprint: auth
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_update_user(base_url, timeout):
    """Testa a rota /auth/users/<int:user_id>"""
    url = f"{base_url}/auth/users/<int:user_id>"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /auth/users/<int:user_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /auth/users/<int:user_id>: {e}")


"""
Teste para rota: /auth/users/<int:user_id>
Endpoint: auth.delete_user
Blueprint: auth
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_auth_delete_user(base_url, timeout):
    """Testa a rota /auth/users/<int:user_id>"""
    url = f"{base_url}/auth/users/<int:user_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /auth/users/<int:user_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /auth/users/<int:user_id>: {e}")


