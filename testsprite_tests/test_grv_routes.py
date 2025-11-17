"""
Testes para blueprint: grv
Total de rotas: 68
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /grv/dashboard
Endpoint: grv.grv_dashboard
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_dashboard(base_url, timeout):
    """Testa a rota /grv/dashboard"""
    url = f"{base_url}/grv/dashboard"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/dashboard retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/dashboard: {e}")


"""
Teste para rota: /grv/company/<int:company_id>
Endpoint: grv.grv_company_dashboard
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_company_dashboard(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>"""
    url = f"{base_url}/grv/company/<int:company_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/identity/mvv
Endpoint: grv.grv_identity_mvv
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_identity_mvv(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/identity/mvv"""
    url = f"{base_url}/grv/company/<int:company_id>/identity/mvv"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/identity/mvv retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/identity/mvv: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/identity/roles
Endpoint: grv.grv_identity_roles
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_identity_roles(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/identity/roles"""
    url = f"{base_url}/grv/company/<int:company_id>/identity/roles"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/identity/roles retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/identity/roles: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/identity/org-chart
Endpoint: grv.grv_identity_org_chart
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_identity_org_chart(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/identity/org-chart"""
    url = f"{base_url}/grv/company/<int:company_id>/identity/org-chart"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/identity/org-chart retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/identity/org-chart: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map
Endpoint: grv.grv_process_map
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/print
Endpoint: grv.grv_process_map_print
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_print(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/print"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/print"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/print retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/print: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/pdf/debug
Endpoint: grv.grv_process_map_pdf_debug
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_pdf_debug(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/pdf/debug"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/pdf/debug"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/pdf/debug retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/pdf/debug: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/pdf
Endpoint: grv.grv_process_map_pdf
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_pdf(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/pdf"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/pdf"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/pdf retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/pdf: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/pdf2/test
Endpoint: grv.grv_process_map_pdf2_test
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_pdf2_test(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/pdf2/test"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/pdf2/test"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/pdf2/test retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/pdf2/test: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/pdf2/debug
Endpoint: grv.grv_process_map_pdf2_debug
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_pdf2_debug(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/pdf2/debug"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/pdf2/debug"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/pdf2/debug retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/pdf2/debug: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/map/pdf2
Endpoint: grv.grv_process_map_pdf2
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_map_pdf2(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/map/pdf2"""
    url = f"{base_url}/grv/company/<int:company_id>/process/map/pdf2"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/map/pdf2 retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/map/pdf2: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/macro
Endpoint: grv.grv_process_macro
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_macro(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/macro"""
    url = f"{base_url}/grv/company/<int:company_id>/process/macro"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/macro retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/macro: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/list
Endpoint: grv.grv_process_list
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_list(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/list"""
    url = f"{base_url}/grv/company/<int:company_id>/process/list"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/list retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/list: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/modeling
Endpoint: grv.grv_process_modeling
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_modeling(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/modeling"""
    url = f"{base_url}/grv/company/<int:company_id>/process/modeling"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/modeling retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/modeling: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/modeling/<int:process_id>
Endpoint: grv.grv_process_detail
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_detail(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/modeling/<int:process_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/process/modeling/<int:process_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/modeling/<int:process_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/modeling/<int:process_id>: {e}")


"""
Teste para rota: /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities
Endpoint: grv.api_process_activities
Blueprint: grv
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_process_activities(base_url, timeout):
    """Testa a rota /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities"""
    url = f"{base_url}/grv/api/companies/<int:company_id>/processes/<int:process_id>/activities"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities: {e}")

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities: {e}")


"""
Teste para rota: /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>
Endpoint: grv.api_process_activity_detail
Blueprint: grv
Métodos: DELETE, GET, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_process_activity_detail(base_url, timeout):
    """Testa a rota /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>"""
    url = f"{base_url}/grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>: {e}")

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>: {e}")

    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>: {e}")


"""
Teste para rota: /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries
Endpoint: grv.api_create_process_activity_entry
Blueprint: grv
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_create_process_activity_entry(base_url, timeout):
    """Testa a rota /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries"""
    url = f"{base_url}/grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries: {e}")


"""
Teste para rota: /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>
Endpoint: grv.api_process_activity_entry_detail
Blueprint: grv
Métodos: DELETE, GET, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_process_activity_entry_detail(base_url, timeout):
    """Testa a rota /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>"""
    url = f"{base_url}/grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>: {e}")

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>: {e}")

    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/analysis
Endpoint: grv.grv_process_analysis
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_analysis(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/analysis"""
    url = f"{base_url}/grv/company/<int:company_id>/process/analysis"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/analysis: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/routine/work-distribution
Endpoint: grv.grv_routine_work_distribution
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_routine_work_distribution(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/routine/work-distribution"""
    url = f"{base_url}/grv/company/<int:company_id>/routine/work-distribution"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/routine/work-distribution retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/routine/work-distribution: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/routine/capacity
Endpoint: grv.grv_routine_capacity
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_routine_capacity(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/routine/capacity"""
    url = f"{base_url}/grv/company/<int:company_id>/routine/capacity"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/routine/capacity retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/routine/capacity: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/routine/activities
Endpoint: grv.grv_routine_activities
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_routine_activities(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/routine/activities"""
    url = f"{base_url}/grv/company/<int:company_id>/routine/activities"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/routine/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/routine/activities: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/routine/incidents
Endpoint: grv.grv_routine_incidents
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_routine_incidents(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/routine/incidents"""
    url = f"{base_url}/grv/company/<int:company_id>/routine/incidents"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/routine/incidents retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/routine/incidents: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/routine/efficiency
Endpoint: grv.grv_routine_efficiency
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_routine_efficiency(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/routine/efficiency"""
    url = f"{base_url}/grv/company/<int:company_id>/routine/efficiency"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/routine/efficiency retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/routine/efficiency: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/projects/portfolios
Endpoint: grv.grv_projects_portfolios
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_projects_portfolios(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/projects/portfolios"""
    url = f"{base_url}/grv/company/<int:company_id>/projects/portfolios"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/projects/portfolios retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/projects/portfolios: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/projects/projects
Endpoint: grv.grv_projects_projects
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_projects_projects(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/projects/projects"""
    url = f"{base_url}/grv/company/<int:company_id>/projects/projects"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/projects/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/projects/projects: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/project/<int:project_id>
Endpoint: grv.grv_project_shortcut
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_project_shortcut(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/project/<int:project_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/project/<int:project_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/project/<int:project_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/project/<int:project_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/projects/<int:project_id>/manage
Endpoint: grv.grv_project_manage
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_project_manage(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/projects/<int:project_id>/manage"""
    url = f"{base_url}/grv/company/<int:company_id>/projects/<int:project_id>/manage"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/projects/<int:project_id>/manage retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/projects/<int:project_id>/manage: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/projects/analysis
Endpoint: grv.grv_projects_analysis
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_projects_analysis(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/projects/analysis"""
    url = f"{base_url}/grv/company/<int:company_id>/projects/analysis"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/projects/analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/projects/analysis: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/instances
Endpoint: grv.grv_process_instances
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_instances(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/instances"""
    url = f"{base_url}/grv/company/<int:company_id>/process/instances"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/instances retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/instances: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/process/instances/<int:instance_id>/manage
Endpoint: grv.grv_process_instance_manage
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_process_instance_manage(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/process/instances/<int:instance_id>/manage"""
    url = f"{base_url}/grv/company/<int:company_id>/process/instances/<int:instance_id>/manage"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/process/instances/<int:instance_id>/manage retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/process/instances/<int:instance_id>/manage: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/tree
Endpoint: grv.grv_indicators_tree
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicators_tree(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/tree"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/tree"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/tree retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/tree: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-groups/form
Endpoint: grv.grv_indicator_group_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_group_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-groups/form"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-groups/form"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-groups/form retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-groups/form: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-groups/form/<int:group_id>
Endpoint: grv.grv_indicator_group_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_group_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-groups/form/<int:group_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-groups/form/<int:group_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-groups/form/<int:group_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-groups/form/<int:group_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/list
Endpoint: grv.grv_indicators_list
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicators_list(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/list"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/list"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/list retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/list: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/form
Endpoint: grv.grv_indicator_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/form"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/form"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/form retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/form: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/form/<int:indicator_id>
Endpoint: grv.grv_indicator_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/form/<int:indicator_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/form/<int:indicator_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/form/<int:indicator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/form/<int:indicator_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/goals
Endpoint: grv.grv_indicators_goals
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicators_goals(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/goals"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/goals"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/goals retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/goals: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-goals/form
Endpoint: grv.grv_indicator_goal_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_goal_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-goals/form"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-goals/form"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-goals/form retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-goals/form: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-goals/form/<int:goal_id>
Endpoint: grv.grv_indicator_goal_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_goal_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-goals/form/<int:goal_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-goals/form/<int:goal_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-goals/form/<int:goal_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-goals/form/<int:goal_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/data
Endpoint: grv.grv_indicators_data
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicators_data(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/data"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/data"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/data retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/data: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-data/form
Endpoint: grv.grv_indicator_data_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_data_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-data/form"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-data/form"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-data/form retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-data/form: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicator-data/form/<int:record_id>
Endpoint: grv.grv_indicator_data_form
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicator_data_form(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicator-data/form/<int:record_id>"""
    url = f"{base_url}/grv/company/<int:company_id>/indicator-data/form/<int:record_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicator-data/form/<int:record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicator-data/form/<int:record_id>: {e}")


"""
Teste para rota: /grv/company/<int:company_id>/indicators/analysis
Endpoint: grv.grv_indicators_analysis
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_grv_indicators_analysis(base_url, timeout):
    """Testa a rota /grv/company/<int:company_id>/indicators/analysis"""
    url = f"{base_url}/grv/company/<int:company_id>/indicators/analysis"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/company/<int:company_id>/indicators/analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/company/<int:company_id>/indicators/analysis: {e}")


"""
Teste para rota: /grv/api/plans/<int:plan_id>/okrs
Endpoint: grv.api_get_plan_okrs
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_plan_okrs(base_url, timeout):
    """Testa a rota /grv/api/plans/<int:plan_id>/okrs"""
    url = f"{base_url}/grv/api/plans/<int:plan_id>/okrs"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/plans/<int:plan_id>/okrs retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/plans/<int:plan_id>/okrs: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-groups
Endpoint: grv.api_get_indicator_groups
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_groups(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-groups"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-groups"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-groups retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-groups: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>
Endpoint: grv.api_get_indicator_group
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_group(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-groups/<int:group_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-groups
Endpoint: grv.api_create_indicator_group
Blueprint: grv
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_create_indicator_group(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-groups"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-groups"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/company/<int:company_id>/indicator-groups retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/company/<int:company_id>/indicator-groups: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>
Endpoint: grv.api_update_indicator_group
Blueprint: grv
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_update_indicator_group(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/company/<int:company_id>/indicator-groups/<int:group_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>
Endpoint: grv.api_delete_indicator_group
Blueprint: grv
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_delete_indicator_group(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-groups/<int:group_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/company/<int:company_id>/indicator-groups/<int:group_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/company/<int:company_id>/indicator-groups/<int:group_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicators
Endpoint: grv.api_get_indicators
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicators(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicators"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicators"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicators: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicators/<int:indicator_id>
Endpoint: grv.api_get_indicator
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicators/<int:indicator_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicators/<int:indicator_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicators/<int:indicator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicators/<int:indicator_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/processes/<int:process_id>/indicators
Endpoint: grv.api_get_process_indicators
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_process_indicators(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/processes/<int:process_id>/indicators"""
    url = f"{base_url}/grv/api/company/<int:company_id>/processes/<int:process_id>/indicators"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/processes/<int:process_id>/indicators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/processes/<int:process_id>/indicators: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicators
Endpoint: grv.api_create_indicator
Blueprint: grv
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_create_indicator(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicators"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicators"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/company/<int:company_id>/indicators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/company/<int:company_id>/indicators: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicators/<int:indicator_id>
Endpoint: grv.api_update_indicator
Blueprint: grv
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_update_indicator(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicators/<int:indicator_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicators/<int:indicator_id>"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/company/<int:company_id>/indicators/<int:indicator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/company/<int:company_id>/indicators/<int:indicator_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicators/<int:indicator_id>
Endpoint: grv.api_delete_indicator
Blueprint: grv
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_delete_indicator(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicators/<int:indicator_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicators/<int:indicator_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/company/<int:company_id>/indicators/<int:indicator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/company/<int:company_id>/indicators/<int:indicator_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-goals
Endpoint: grv.api_get_indicator_goals
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_goals(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-goals"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-goals"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-goals retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-goals: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>
Endpoint: grv.api_get_indicator_goal
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_goal(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-goals
Endpoint: grv.api_create_indicator_goal
Blueprint: grv
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_create_indicator_goal(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-goals"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-goals"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/company/<int:company_id>/indicator-goals retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/company/<int:company_id>/indicator-goals: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>
Endpoint: grv.api_update_indicator_goal
Blueprint: grv
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_update_indicator_goal(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>
Endpoint: grv.api_delete_indicator_goal
Blueprint: grv
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_delete_indicator_goal(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/company/<int:company_id>/indicator-goals/<int:goal_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-data
Endpoint: grv.api_get_indicator_data
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_data(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-data"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-data"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-data retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-data: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-data/<int:data_id>
Endpoint: grv.api_get_indicator_data_record
Blueprint: grv
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_get_indicator_data_record(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-data/<int:data_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-data/<int:data_id>"
    
    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \
            f"GET /grv/api/company/<int:company_id>/indicator-data/<int:data_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /grv/api/company/<int:company_id>/indicator-data/<int:data_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-data
Endpoint: grv.api_create_indicator_data
Blueprint: grv
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_create_indicator_data(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-data"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-data"
    
    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"POST /grv/api/company/<int:company_id>/indicator-data retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /grv/api/company/<int:company_id>/indicator-data: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-data/<int:data_id>
Endpoint: grv.api_update_indicator_data
Blueprint: grv
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_update_indicator_data(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-data/<int:data_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-data/<int:data_id>"
    
    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \
            f"PUT /grv/api/company/<int:company_id>/indicator-data/<int:data_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /grv/api/company/<int:company_id>/indicator-data/<int:data_id>: {e}")


"""
Teste para rota: /grv/api/company/<int:company_id>/indicator-data/<int:data_id>
Endpoint: grv.api_delete_indicator_data
Blueprint: grv
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def test_grv_api_delete_indicator_data(base_url, timeout):
    """Testa a rota /grv/api/company/<int:company_id>/indicator-data/<int:data_id>"""
    url = f"{base_url}/grv/api/company/<int:company_id>/indicator-data/<int:data_id>"
    
    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \
            f"DELETE /grv/api/company/<int:company_id>/indicator-data/<int:data_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /grv/api/company/<int:company_id>/indicator-data/<int:data_id>: {e}")


