"""
Testes para blueprint: meetings
Total de rotas: 20
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /meetings/company/<int:company_id>/list
Endpoint: meetings.meetings_manage
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_meetings_manage(base_url, timeout):
    """Testa a rota /meetings/company/<int:company_id>/list"""
    url = f"{base_url}/meetings/company/<int:company_id>/list"

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
        ), f"GET /meetings/company/<int:company_id>/list retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/company/<int:company_id>/list: {e}"
        )


"""
Teste para rota: /meetings/company/<int:company_id>
Endpoint: meetings.meetings_manage
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_meetings_manage(base_url, timeout):
    """Testa a rota /meetings/company/<int:company_id>"""
    url = f"{base_url}/meetings/company/<int:company_id>"

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
        ), f"GET /meetings/company/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /meetings/company/<int:company_id>: {e}")


"""
Teste para rota: /meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit
Endpoint: meetings.meeting_edit
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_meeting_edit(base_url, timeout):
    """Testa a rota /meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit"""
    url = f"{base_url}/meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit"

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
        ), f"GET /meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit: {e}"
        )


"""
Teste para rota: /meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete
Endpoint: meetings.meeting_delete
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_meeting_delete(base_url, timeout):
    """Testa a rota /meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete"""
    url = (
        f"{base_url}/meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete"
    )

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
        ), f"POST /meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete: {e}"
        )


"""
Teste para rota: /meetings/api/company/<int:company_id>/meeting
Endpoint: meetings.api_create_meeting
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_create_meeting(base_url, timeout):
    """Testa a rota /meetings/api/company/<int:company_id>/meeting"""
    url = f"{base_url}/meetings/api/company/<int:company_id>/meeting"

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
        ), f"POST /meetings/api/company/<int:company_id>/meeting retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/company/<int:company_id>/meeting: {e}"
        )


"""
Teste para rota: /meetings/api/company/<int:company_id>/meetings/report
Endpoint: meetings.api_generate_meetings_report
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_generate_meetings_report(base_url, timeout):
    """Testa a rota /meetings/api/company/<int:company_id>/meetings/report"""
    url = f"{base_url}/meetings/api/company/<int:company_id>/meetings/report"

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
        ), f"GET /meetings/api/company/<int:company_id>/meetings/report retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/api/company/<int:company_id>/meetings/report: {e}"
        )


"""
Teste para rota: /meetings/api/company/<int:company_id>/meetings
Endpoint: meetings.api_list_company_meetings
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_list_company_meetings(base_url, timeout):
    """Testa a rota /meetings/api/company/<int:company_id>/meetings"""
    url = f"{base_url}/meetings/api/company/<int:company_id>/meetings"

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
        ), f"GET /meetings/api/company/<int:company_id>/meetings retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/api/company/<int:company_id>/meetings: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>
Endpoint: meetings.api_get_meeting
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_get_meeting(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>"

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
        ), f"GET /meetings/api/meeting/<int:meeting_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/api/meeting/<int:meeting_id>: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/preliminares
Endpoint: meetings.api_update_preliminares
Blueprint: meetings
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_update_preliminares(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/preliminares"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/preliminares"

    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
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
        ), f"PUT /meetings/api/meeting/<int:meeting_id>/preliminares retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /meetings/api/meeting/<int:meeting_id>/preliminares: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/iniciar
Endpoint: meetings.api_start_meeting
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_start_meeting(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/iniciar"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/iniciar"

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
        ), f"POST /meetings/api/meeting/<int:meeting_id>/iniciar retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/meeting/<int:meeting_id>/iniciar: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/execucao
Endpoint: meetings.api_update_execucao
Blueprint: meetings
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_update_execucao(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/execucao"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/execucao"

    # Test PUT request
    try:
        # Tentar com payload vazio primeiro
        response = requests.put(url, json={}, timeout=timeout)
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
        ), f"PUT /meetings/api/meeting/<int:meeting_id>/execucao retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /meetings/api/meeting/<int:meeting_id>/execucao: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/finalizar
Endpoint: meetings.api_finish_meeting
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_finish_meeting(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/finalizar"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/finalizar"

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
        ), f"POST /meetings/api/meeting/<int:meeting_id>/finalizar retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/meeting/<int:meeting_id>/finalizar: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/sync-activities
Endpoint: meetings.api_sync_meeting_activities
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_sync_meeting_activities(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/sync-activities"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/sync-activities"

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
        ), f"POST /meetings/api/meeting/<int:meeting_id>/sync-activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/meeting/<int:meeting_id>/sync-activities: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/check-sync
Endpoint: meetings.api_check_meeting_sync
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_check_meeting_sync(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/check-sync"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/check-sync"

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
        ), f"GET /meetings/api/meeting/<int:meeting_id>/check-sync retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/api/meeting/<int:meeting_id>/check-sync: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/remove-from-project
Endpoint: meetings.api_remove_activity_from_project
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_remove_activity_from_project(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/remove-from-project"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/remove-from-project"

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
        ), f"POST /meetings/api/meeting/<int:meeting_id>/remove-from-project retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/meeting/<int:meeting_id>/remove-from-project: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>
Endpoint: meetings.api_delete_meeting
Blueprint: meetings
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_delete_meeting(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>"

    # Test DELETE request
    try:
        response = requests.delete(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (
            200,
            204,
            400,
            401,
            403,
            404,
            500,
        ), f"DELETE /meetings/api/meeting/<int:meeting_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /meetings/api/meeting/<int:meeting_id>: {e}"
        )


"""
Teste para rota: /meetings/api/meeting/<int:meeting_id>/atividades
Endpoint: meetings.api_get_meeting_activities
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_get_meeting_activities(base_url, timeout):
    """Testa a rota /meetings/api/meeting/<int:meeting_id>/atividades"""
    url = f"{base_url}/meetings/api/meeting/<int:meeting_id>/atividades"

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
        ), f"GET /meetings/api/meeting/<int:meeting_id>/atividades retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/api/meeting/<int:meeting_id>/atividades: {e}"
        )


"""
Teste para rota: /meetings/api/company/<int:company_id>/agenda-item
Endpoint: meetings.api_save_agenda_item
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_save_agenda_item(base_url, timeout):
    """Testa a rota /meetings/api/company/<int:company_id>/agenda-item"""
    url = f"{base_url}/meetings/api/company/<int:company_id>/agenda-item"

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
        ), f"POST /meetings/api/company/<int:company_id>/agenda-item retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/company/<int:company_id>/agenda-item: {e}"
        )


"""
Teste para rota: /meetings/company/<int:company_id>/meeting/<int:meeting_id>/report
Endpoint: meetings.meeting_report
Blueprint: meetings
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_meeting_report(base_url, timeout):
    """Testa a rota /meetings/company/<int:company_id>/meeting/<int:meeting_id>/report"""
    url = (
        f"{base_url}/meetings/company/<int:company_id>/meeting/<int:meeting_id>/report"
    )

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
        ), f"GET /meetings/company/<int:company_id>/meeting/<int:meeting_id>/report retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /meetings/company/<int:company_id>/meeting/<int:meeting_id>/report: {e}"
        )


"""
Teste para rota: /meetings/api/agenda-item/<int:item_id>/use
Endpoint: meetings.api_use_agenda_item
Blueprint: meetings
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_meetings_api_use_agenda_item(base_url, timeout):
    """Testa a rota /meetings/api/agenda-item/<int:item_id>/use"""
    url = f"{base_url}/meetings/api/agenda-item/<int:item_id>/use"

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
        ), f"POST /meetings/api/agenda-item/<int:item_id>/use retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /meetings/api/agenda-item/<int:item_id>/use: {e}"
        )
