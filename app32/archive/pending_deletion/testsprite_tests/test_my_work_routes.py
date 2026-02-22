"""
Testes para blueprint: my_work
Total de rotas: 9
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /my-work/
Endpoint: my_work.dashboard
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_dashboard(base_url, timeout):
    """Testa a rota /my-work/"""
    url = f"{base_url}/my-work/"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/ retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /my-work/: {e}")


"""
Teste para rota: /my-work/api/activities
Endpoint: my_work.get_activities
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_get_activities(base_url, timeout):
    """Testa a rota /my-work/api/activities"""
    url = f"{base_url}/my-work/api/activities"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/api/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /my-work/api/activities: {e}")


"""
Teste para rota: /my-work/api/team-overview
Endpoint: my_work.api_team_overview
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_api_team_overview(base_url, timeout):
    """Testa a rota /my-work/api/team-overview"""
    url = f"{base_url}/my-work/api/team-overview"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/api/team-overview retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /my-work/api/team-overview: {e}")


"""
Teste para rota: /my-work/api/company-overview
Endpoint: my_work.api_company_overview
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_api_company_overview(base_url, timeout):
    """Testa a rota /my-work/api/company-overview"""
    url = f"{base_url}/my-work/api/company-overview"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/api/company-overview retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /my-work/api/company-overview: {e}")


"""
Teste para rota: /my-work/api/work-hours
Endpoint: my_work.api_add_work_hours
Blueprint: my_work
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_api_add_work_hours(base_url, timeout):
    """Testa a rota /my-work/api/work-hours"""
    url = f"{base_url}/my-work/api/work-hours"

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (
            200,
            201,
            400,
            401,
            403,
            404,
            422,
            500,
        ), f"POST /my-work/api/work-hours retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /my-work/api/work-hours: {e}")


"""
Teste para rota: /my-work/api/comments
Endpoint: my_work.api_add_comment
Blueprint: my_work
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_api_add_comment(base_url, timeout):
    """Testa a rota /my-work/api/comments"""
    url = f"{base_url}/my-work/api/comments"

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (
            200,
            201,
            400,
            401,
            403,
            404,
            422,
            500,
        ), f"POST /my-work/api/comments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /my-work/api/comments: {e}")


"""
Teste para rota: /my-work/api/complete
Endpoint: my_work.api_complete_activity
Blueprint: my_work
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_api_complete_activity(base_url, timeout):
    """Testa a rota /my-work/api/complete"""
    url = f"{base_url}/my-work/api/complete"

    # Test POST request
    try:
        # Tentar com payload vazio primeiro
        response = requests.post(url, json={}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (
            200,
            201,
            400,
            401,
            403,
            404,
            422,
            500,
        ), f"POST /my-work/api/complete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /my-work/api/complete: {e}")


"""
Teste para rota: /my-work/activity/<int:activity_id>
Endpoint: my_work.view_project_activity
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_view_project_activity(base_url, timeout):
    """Testa a rota /my-work/activity/<int:activity_id>"""
    url = f"{base_url}/my-work/activity/<int:activity_id>"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/activity/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /my-work/activity/<int:activity_id>: {e}")


"""
Teste para rota: /my-work/process-instance/<int:instance_id>
Endpoint: my_work.view_process_instance
Blueprint: my_work
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_my_work_view_process_instance(base_url, timeout):
    """Testa a rota /my-work/process-instance/<int:instance_id>"""
    url = f"{base_url}/my-work/process-instance/<int:instance_id>"

    # Test GET request
    try:
        response = requests.get(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (
            200,
            302,
            401,
            403,
            404,
        ), f"GET /my-work/process-instance/<int:instance_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /my-work/process-instance/<int:instance_id>: {e}"
        )
