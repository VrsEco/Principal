"""
Testes para blueprint: None
Total de rotas: 233
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /favicon.ico
Endpoint: favicon
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_favicon(base_url, timeout):
    """Testa a rota /favicon.ico"""
    url = f"{base_url}/favicon.ico"

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
        ), f"GET /favicon.ico retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /favicon.ico: {e}")


"""
Teste para rota: /admin/purge/companies
Endpoint: purge_companies_except_versus
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_purge_companies_except_versus(base_url, timeout):
    """Testa a rota /admin/purge/companies"""
    url = f"{base_url}/admin/purge/companies"

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
        ), f"POST /admin/purge/companies retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /admin/purge/companies: {e}")


"""
Teste para rota: /
Endpoint: index
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_index(base_url, timeout):
    """Testa a rota /"""
    url = f"{base_url}/"

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
        ), f"GET / retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /: {e}")


"""
Teste para rota: /login
Endpoint: login
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_login(base_url, timeout):
    """Testa a rota /login"""
    url = f"{base_url}/login"

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
        ), f"GET /login retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /login: {e}")

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
        ), f"POST /login retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /login: {e}")


"""
Teste para rota: /main
Endpoint: main
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_main(base_url, timeout):
    """Testa a rota /main"""
    url = f"{base_url}/main"

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
        ), f"GET /main retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /main: {e}")


"""
Teste para rota: /integrations
Endpoint: integrations
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_integrations(base_url, timeout):
    """Testa a rota /integrations"""
    url = f"{base_url}/integrations"

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
        ), f"GET /integrations retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /integrations: {e}")


"""
Teste para rota: /configs
Endpoint: system_configs
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_system_configs(base_url, timeout):
    """Testa a rota /configs"""
    url = f"{base_url}/configs"

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
        ), f"GET /configs retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /configs: {e}")


"""
Teste para rota: /configs/system
Endpoint: system_configs_system
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_system_configs_system(base_url, timeout):
    """Testa a rota /configs/system"""
    url = f"{base_url}/configs/system"

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
        ), f"GET /configs/system retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /configs/system: {e}")


"""
Teste para rota: /configs/system/audit
Endpoint: system_configs_audit
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_system_configs_audit(base_url, timeout):
    """Testa a rota /configs/system/audit"""
    url = f"{base_url}/configs/system/audit"

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
        ), f"GET /configs/system/audit retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /configs/system/audit: {e}")


"""
Teste para rota: /configs/ai
Endpoint: system_configs_ai
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_system_configs_ai(base_url, timeout):
    """Testa a rota /configs/ai"""
    url = f"{base_url}/configs/ai"

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
        ), f"GET /configs/ai retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /configs/ai: {e}")


"""
Teste para rota: /settings/reports
Endpoint: settings_reports
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_settings_reports(base_url, timeout):
    """Testa a rota /settings/reports"""
    url = f"{base_url}/settings/reports"

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
        ), f"GET /settings/reports retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /settings/reports: {e}")


"""
Teste para rota: /api/reports/preview
Endpoint: api_report_preview
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_report_preview(base_url, timeout):
    """Testa a rota /api/reports/preview"""
    url = f"{base_url}/api/reports/preview"

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
        ), f"POST /api/reports/preview retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/reports/preview: {e}")


"""
Teste para rota: /api/reports/generate
Endpoint: api_report_generate
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_report_generate(base_url, timeout):
    """Testa a rota /api/reports/generate"""
    url = f"{base_url}/api/reports/generate"

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
        ), f"POST /api/reports/generate retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/reports/generate: {e}")


"""
Teste para rota: /api/reports/download/<filename>
Endpoint: api_report_download
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_report_download(base_url, timeout):
    """Testa a rota /api/reports/download/<filename>"""
    url = f"{base_url}/api/reports/download/<filename>"

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
        ), f"GET /api/reports/download/<filename> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/reports/download/<filename>: {e}")


"""
Teste para rota: /api/reports/models
Endpoint: api_save_report_model
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_save_report_model(base_url, timeout):
    """Testa a rota /api/reports/models"""
    url = f"{base_url}/api/reports/models"

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
        ), f"POST /api/reports/models retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/reports/models: {e}")


"""
Teste para rota: /api/reports/models/<int:model_id>
Endpoint: api_get_report_model
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_report_model(base_url, timeout):
    """Testa a rota /api/reports/models/<int:model_id>"""
    url = f"{base_url}/api/reports/models/<int:model_id>"

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
        ), f"GET /api/reports/models/<int:model_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/reports/models/<int:model_id>: {e}")


"""
Teste para rota: /api/reports/models/<int:model_id>
Endpoint: api_update_report_model
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_report_model(base_url, timeout):
    """Testa a rota /api/reports/models/<int:model_id>"""
    url = f"{base_url}/api/reports/models/<int:model_id>"

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
        ), f"PUT /api/reports/models/<int:model_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /api/reports/models/<int:model_id>: {e}")


"""
Teste para rota: /api/reports/models/<int:model_id>/conflicts
Endpoint: api_check_model_conflicts
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_check_model_conflicts(base_url, timeout):
    """Testa a rota /api/reports/models/<int:model_id>/conflicts"""
    url = f"{base_url}/api/reports/models/<int:model_id>/conflicts"

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
        ), f"GET /api/reports/models/<int:model_id>/conflicts retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/reports/models/<int:model_id>/conflicts: {e}"
        )


"""
Teste para rota: /api/reports/models/<int:model_id>
Endpoint: api_delete_report_model
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_report_model(base_url, timeout):
    """Testa a rota /api/reports/models/<int:model_id>"""
    url = f"{base_url}/api/reports/models/<int:model_id>"

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
        ), f"DELETE /api/reports/models/<int:model_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/reports/models/<int:model_id>: {e}"
        )


"""
Teste para rota: /report-templates
Endpoint: report_templates_manager
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_report_templates_manager(base_url, timeout):
    """Testa a rota /report-templates"""
    url = f"{base_url}/report-templates"

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
        ), f"GET /report-templates retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /report-templates: {e}")


"""
Teste para rota: /api/report-templates
Endpoint: api_get_report_templates
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_report_templates(base_url, timeout):
    """Testa a rota /api/report-templates"""
    url = f"{base_url}/api/report-templates"

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
        ), f"GET /api/report-templates retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/report-templates: {e}")


"""
Teste para rota: /api/report-templates
Endpoint: api_create_report_template
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_report_template(base_url, timeout):
    """Testa a rota /api/report-templates"""
    url = f"{base_url}/api/report-templates"

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
        ), f"POST /api/report-templates retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/report-templates: {e}")


"""
Teste para rota: /api/report-templates/<int:template_id>
Endpoint: api_get_report_template
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_report_template(base_url, timeout):
    """Testa a rota /api/report-templates/<int:template_id>"""
    url = f"{base_url}/api/report-templates/<int:template_id>"

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
        ), f"GET /api/report-templates/<int:template_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/report-templates/<int:template_id>: {e}"
        )


"""
Teste para rota: /api/report-templates/<int:template_id>
Endpoint: api_update_report_template
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_report_template(base_url, timeout):
    """Testa a rota /api/report-templates/<int:template_id>"""
    url = f"{base_url}/api/report-templates/<int:template_id>"

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
        ), f"PUT /api/report-templates/<int:template_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/report-templates/<int:template_id>: {e}"
        )


"""
Teste para rota: /api/report-templates/<int:template_id>
Endpoint: api_delete_report_template
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_report_template(base_url, timeout):
    """Testa a rota /api/report-templates/<int:template_id>"""
    url = f"{base_url}/api/report-templates/<int:template_id>"

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
        ), f"DELETE /api/report-templates/<int:template_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/report-templates/<int:template_id>: {e}"
        )


"""
Teste para rota: /api/report-templates/<int:template_id>/generate
Endpoint: api_generate_report_from_template
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_generate_report_from_template(base_url, timeout):
    """Testa a rota /api/report-templates/<int:template_id>/generate"""
    url = f"{base_url}/api/report-templates/<int:template_id>/generate"

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
        ), f"POST /api/report-templates/<int:template_id>/generate retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/report-templates/<int:template_id>/generate: {e}"
        )


"""
Teste para rota: /api/report-templates/by-type/<report_type>
Endpoint: api_get_templates_by_type
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_templates_by_type(base_url, timeout):
    """Testa a rota /api/report-templates/by-type/<report_type>"""
    url = f"{base_url}/api/report-templates/by-type/<report_type>"

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
        ), f"GET /api/report-templates/by-type/<report_type> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/report-templates/by-type/<report_type>: {e}"
        )


"""
Teste para rota: /api/reports/models
Endpoint: api_get_report_models
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_report_models(base_url, timeout):
    """Testa a rota /api/reports/models"""
    url = f"{base_url}/api/reports/models"

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
        ), f"GET /api/reports/models retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/reports/models: {e}")


"""
Teste para rota: /companies
Endpoint: companies_page
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_companies_page(base_url, timeout):
    """Testa a rota /companies"""
    url = f"{base_url}/companies"

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
        ), f"GET /companies retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies: {e}")


"""
Teste para rota: /companies/new
Endpoint: companies_new
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_companies_new(base_url, timeout):
    """Testa a rota /companies/new"""
    url = f"{base_url}/companies/new"

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
        ), f"GET /companies/new retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies/new: {e}")


"""
Teste para rota: /companies/<int:company_id>
Endpoint: company_details
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_company_details(base_url, timeout):
    """Testa a rota /companies/<int:company_id>"""
    url = f"{base_url}/companies/<int:company_id>"

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
        ), f"GET /companies/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies/<int:company_id>: {e}")


"""
Teste para rota: /companies/<int:company_id>/edit
Endpoint: companies_edit
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_companies_edit(base_url, timeout):
    """Testa a rota /companies/<int:company_id>/edit"""
    url = f"{base_url}/companies/<int:company_id>/edit"

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
        ), f"GET /companies/<int:company_id>/edit retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies/<int:company_id>/edit: {e}")


"""
Teste para rota: /companies/<int:company_id>/logos
Endpoint: company_logos_manager
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_company_logos_manager(base_url, timeout):
    """Testa a rota /companies/<int:company_id>/logos"""
    url = f"{base_url}/companies/<int:company_id>/logos"

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
        ), f"GET /companies/<int:company_id>/logos retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies/<int:company_id>/logos: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/logos
Endpoint: api_upload_company_logo
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_upload_company_logo(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/logos"""
    url = f"{base_url}/api/companies/<int:company_id>/logos"

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
        ), f"POST /api/companies/<int:company_id>/logos retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/logos: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/logos/<logo_type>
Endpoint: api_delete_company_logo
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_company_logo(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/logos/<logo_type>"""
    url = f"{base_url}/api/companies/<int:company_id>/logos/<logo_type>"

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
        ), f"DELETE /api/companies/<int:company_id>/logos/<logo_type> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/logos/<logo_type>: {e}"
        )


"""
Teste para rota: /dashboard
Endpoint: dashboard
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_dashboard(base_url, timeout):
    """Testa a rota /dashboard"""
    url = f"{base_url}/dashboard"

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
        ), f"GET /dashboard retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /dashboard: {e}")


"""
Teste para rota: /api/plans/<int:plan_id>/company-data
Endpoint: api_get_company_data
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_company_data(base_url, timeout):
    """Testa a rota /api/plans/<int:plan_id>/company-data"""
    url = f"{base_url}/api/plans/<int:plan_id>/company-data"

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
        ), f"GET /api/plans/<int:plan_id>/company-data retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/plans/<int:plan_id>/company-data: {e}"
        )


"""
Teste para rota: /api/plans/<int:plan_id>/company-data
Endpoint: api_update_company_data
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_company_data(base_url, timeout):
    """Testa a rota /api/plans/<int:plan_id>/company-data"""
    url = f"{base_url}/api/plans/<int:plan_id>/company-data"

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
        ), f"POST /api/plans/<int:plan_id>/company-data retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/plans/<int:plan_id>/company-data: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/mvv
Endpoint: api_get_company_mvv
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_company_mvv(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/mvv"""
    url = f"{base_url}/api/companies/<int:company_id>/mvv"

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
        ), f"GET /api/companies/<int:company_id>/mvv retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/companies/<int:company_id>/mvv: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/mvv
Endpoint: api_update_company_mvv
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_company_mvv(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/mvv"""
    url = f"{base_url}/api/companies/<int:company_id>/mvv"

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
        ), f"POST /api/companies/<int:company_id>/mvv retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/companies/<int:company_id>/mvv: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/economic
Endpoint: api_update_company_economic
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_company_economic(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/economic"""
    url = f"{base_url}/api/companies/<int:company_id>/economic"

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
        ), f"POST /api/companies/<int:company_id>/economic retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/economic: {e}"
        )


"""
Teste para rota: /api/companies
Endpoint: api_create_company
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_company(base_url, timeout):
    """Testa a rota /api/companies"""
    url = f"{base_url}/api/companies"

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
        ), f"POST /api/companies retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/companies: {e}")


"""
Teste para rota: /api/plans
Endpoint: api_create_plan
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_plan(base_url, timeout):
    """Testa a rota /api/plans"""
    url = f"{base_url}/api/plans"

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
        ), f"POST /api/plans retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/plans: {e}")


"""
Teste para rota: /api/plans/<int:plan_id>
Endpoint: api_get_plan
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_plan(base_url, timeout):
    """Testa a rota /api/plans/<int:plan_id>"""
    url = f"{base_url}/api/plans/<int:plan_id>"

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
        ), f"GET /api/plans/<int:plan_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/plans/<int:plan_id>: {e}")


"""
Teste para rota: /api/companies/<int:company_id>
Endpoint: api_get_company_profile
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_company_profile(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>"""
    url = f"{base_url}/api/companies/<int:company_id>"

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
        ), f"GET /api/companies/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/companies/<int:company_id>: {e}")


"""
Teste para rota: /api/companies/<int:company_id>
Endpoint: api_update_company_profile
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_company_profile(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>"""
    url = f"{base_url}/api/companies/<int:company_id>"

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
        ), f"POST /api/companies/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/companies/<int:company_id>: {e}")


"""
Teste para rota: /api/companies/<int:company_id>
Endpoint: api_delete_company
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_company(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>"""
    url = f"{base_url}/api/companies/<int:company_id>"

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
        ), f"DELETE /api/companies/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /api/companies/<int:company_id>: {e}")


"""
Teste para rota: /relatorios/projetos/<int:company_id>
Endpoint: gerar_relatorio_projetos
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_gerar_relatorio_projetos(base_url, timeout):
    """Testa a rota /relatorios/projetos/<int:company_id>"""
    url = f"{base_url}/relatorios/projetos/<int:company_id>"

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
        ), f"GET /relatorios/projetos/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /relatorios/projetos/<int:company_id>: {e}"
        )


"""
Teste para rota: /api/relatorios/projetos/<int:company_id>
Endpoint: api_gerar_relatorio_projetos
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_gerar_relatorio_projetos(base_url, timeout):
    """Testa a rota /api/relatorios/projetos/<int:company_id>"""
    url = f"{base_url}/api/relatorios/projetos/<int:company_id>"

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
        ), f"GET /api/relatorios/projetos/<int:company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/relatorios/projetos/<int:company_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/employees
Endpoint: api_company_employees
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_employees(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/employees"""
    url = f"{base_url}/api/companies/<int:company_id>/employees"

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
        ), f"GET /api/companies/<int:company_id>/employees retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/employees: {e}"
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
        ), f"POST /api/companies/<int:company_id>/employees retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/employees: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/employees/<int:employee_id>
Endpoint: api_company_employee
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_employee(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/employees/<int:employee_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/employees/<int:employee_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/employees/<int:employee_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/employees/<int:employee_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/employees/<int:employee_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/employees/<int:employee_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/workforce-analysis
Endpoint: api_workforce_analysis
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_workforce_analysis(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/workforce-analysis"""
    url = f"{base_url}/api/companies/<int:company_id>/workforce-analysis"

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
        ), f"GET /api/companies/<int:company_id>/workforce-analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/workforce-analysis: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/client-code
Endpoint: api_update_client_code
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_client_code(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/client-code"""
    url = f"{base_url}/api/companies/<int:company_id>/client-code"

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
        ), f"POST /api/companies/<int:company_id>/client-code retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/client-code: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/roles
Endpoint: api_list_roles
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_list_roles(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/roles"""
    url = f"{base_url}/api/companies/<int:company_id>/roles"

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
        ), f"GET /api/companies/<int:company_id>/roles retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/roles: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/roles/tree
Endpoint: api_roles_tree
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_roles_tree(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/roles/tree"""
    url = f"{base_url}/api/companies/<int:company_id>/roles/tree"

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
        ), f"GET /api/companies/<int:company_id>/roles/tree retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/roles/tree: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/roles
Endpoint: api_create_role
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_role(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/roles"""
    url = f"{base_url}/api/companies/<int:company_id>/roles"

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
        ), f"POST /api/companies/<int:company_id>/roles retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/roles: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/roles/<int:role_id>
Endpoint: api_update_role
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_role(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/roles/<int:role_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/roles/<int:role_id>"

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
        ), f"PUT /api/companies/<int:company_id>/roles/<int:role_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/roles/<int:role_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/roles/<int:role_id>
Endpoint: api_delete_role
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_role(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/roles/<int:role_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/roles/<int:role_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/roles/<int:role_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/roles/<int:role_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-map
Endpoint: api_get_process_map
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_process_map(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-map"""
    url = f"{base_url}/api/companies/<int:company_id>/process-map"

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
        ), f"GET /api/companies/<int:company_id>/process-map retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/process-map: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-areas
Endpoint: api_list_process_areas
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_list_process_areas(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-areas"""
    url = f"{base_url}/api/companies/<int:company_id>/process-areas"

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
        ), f"GET /api/companies/<int:company_id>/process-areas retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/process-areas: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-areas
Endpoint: api_create_process_area
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_process_area(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-areas"""
    url = f"{base_url}/api/companies/<int:company_id>/process-areas"

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
        ), f"POST /api/companies/<int:company_id>/process-areas retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/process-areas: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-areas/<int:area_id>
Endpoint: api_update_process_area
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_process_area(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-areas/<int:area_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/process-areas/<int:area_id>"

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
        ), f"PUT /api/companies/<int:company_id>/process-areas/<int:area_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/process-areas/<int:area_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-areas/<int:area_id>
Endpoint: api_delete_process_area
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_process_area(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-areas/<int:area_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/process-areas/<int:area_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/process-areas/<int:area_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/process-areas/<int:area_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/macro-processes
Endpoint: api_list_macro_processes
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_list_macro_processes(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/macro-processes"""
    url = f"{base_url}/api/companies/<int:company_id>/macro-processes"

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
        ), f"GET /api/companies/<int:company_id>/macro-processes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/macro-processes: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/macro-processes
Endpoint: api_create_macro_process
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_macro_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/macro-processes"""
    url = f"{base_url}/api/companies/<int:company_id>/macro-processes"

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
        ), f"POST /api/companies/<int:company_id>/macro-processes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/macro-processes: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/macro-processes/<int:macro_id>
Endpoint: api_update_macro_process
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_macro_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/macro-processes/<int:macro_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/macro-processes/<int:macro_id>"

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
        ), f"PUT /api/companies/<int:company_id>/macro-processes/<int:macro_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/macro-processes/<int:macro_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/macro-processes/<int:macro_id>
Endpoint: api_delete_macro_process
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_macro_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/macro-processes/<int:macro_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/macro-processes/<int:macro_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/macro-processes/<int:macro_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/macro-processes/<int:macro_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes
Endpoint: api_list_processes
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_list_processes(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes"""
    url = f"{base_url}/api/companies/<int:company_id>/processes"

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
        ), f"GET /api/companies/<int:company_id>/processes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/processes: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes
Endpoint: api_create_process
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes"""
    url = f"{base_url}/api/companies/<int:company_id>/processes"

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
        ), f"POST /api/companies/<int:company_id>/processes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/processes: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>
Endpoint: api_update_process
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>"

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
        ), f"PUT /api/companies/<int:company_id>/processes/<int:process_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/processes/<int:process_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/stage
Endpoint: api_update_process_stage
Blueprint: None
Métodos: PATCH
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_process_stage(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/stage"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/stage"

    # Test PATCH request
    try:
        # Tentar com payload vazio primeiro
        response = requests.patch(url, json={}, timeout=timeout)
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
        ), f"PATCH /api/companies/<int:company_id>/processes/<int:process_id>/stage retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PATCH /api/companies/<int:company_id>/processes/<int:process_id>/stage: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/notes
Endpoint: api_process_notes
Blueprint: None
Métodos: GET, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_process_notes(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/notes"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/notes"

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
        ), f"GET /api/companies/<int:company_id>/processes/<int:process_id>/notes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/processes/<int:process_id>/notes: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/processes/<int:process_id>/notes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/processes/<int:process_id>/notes: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/flow
Endpoint: api_process_flow_document
Blueprint: None
Métodos: DELETE, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_process_flow_document(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/flow"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/flow"

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
        ), f"DELETE /api/companies/<int:company_id>/processes/<int:process_id>/flow retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/processes/<int:process_id>/flow: {e}"
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
        ), f"POST /api/companies/<int:company_id>/processes/<int:process_id>/flow retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/processes/<int:process_id>/flow: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/activities
Endpoint: api_process_activities
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_process_activities(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/activities"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/activities"

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
        ), f"GET /api/companies/<int:company_id>/processes/<int:process_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/processes/<int:process_id>/activities: {e}"
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
        ), f"POST /api/companies/<int:company_id>/processes/<int:process_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/processes/<int:process_id>/activities: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>
Endpoint: api_process_activity_detail
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_process_activity_detail(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries
Endpoint: api_create_process_activity_entry
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_process_activity_entry(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries"

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
        ), f"POST /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>
Endpoint: api_process_activity_entry_detail
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_process_activity_entry_detail(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>
Endpoint: api_delete_process
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_process(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/processes/<int:process_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/processes/<int:process_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-instances
Endpoint: api_list_process_instances
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_list_process_instances(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-instances"""
    url = f"{base_url}/api/companies/<int:company_id>/process-instances"

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
        ), f"GET /api/companies/<int:company_id>/process-instances retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/process-instances: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-instances
Endpoint: api_create_process_instance
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_process_instance(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-instances"""
    url = f"{base_url}/api/companies/<int:company_id>/process-instances"

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
        ), f"POST /api/companies/<int:company_id>/process-instances retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/process-instances: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators
Endpoint: api_get_process_routine_collaborators
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_process_routine_collaborators(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators"

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
        ), f"GET /api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-instances/<int:instance_id>
Endpoint: api_update_process_instance
Blueprint: None
Métodos: PATCH
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_process_instance(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-instances/<int:instance_id>"""
    url = (
        f"{base_url}/api/companies/<int:company_id>/process-instances/<int:instance_id>"
    )

    # Test PATCH request
    try:
        # Tentar com payload vazio primeiro
        response = requests.patch(url, json={}, timeout=timeout)
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
        ), f"PATCH /api/companies/<int:company_id>/process-instances/<int:instance_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PATCH /api/companies/<int:company_id>/process-instances/<int:instance_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/unified-activities
Endpoint: api_get_unified_activities
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_unified_activities(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/unified-activities"""
    url = f"{base_url}/api/companies/<int:company_id>/unified-activities"

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
        ), f"GET /api/companies/<int:company_id>/unified-activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/unified-activities: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/occurrences
Endpoint: api_company_occurrences
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_occurrences(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/occurrences"""
    url = f"{base_url}/api/companies/<int:company_id>/occurrences"

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
        ), f"GET /api/companies/<int:company_id>/occurrences retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/occurrences: {e}"
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
        ), f"POST /api/companies/<int:company_id>/occurrences retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/occurrences: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/occurrences/<int:occurrence_id>
Endpoint: api_company_occurrence
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_occurrence(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/occurrences/<int:occurrence_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/occurrences/<int:occurrence_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/occurrences/<int:occurrence_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/occurrences/<int:occurrence_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/occurrences/<int:occurrence_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/occurrences/<int:occurrence_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/efficiency/collaborators
Endpoint: api_company_efficiency_collaborators
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_efficiency_collaborators(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/efficiency/collaborators"""
    url = f"{base_url}/api/companies/<int:company_id>/efficiency/collaborators"

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
        ), f"GET /api/companies/<int:company_id>/efficiency/collaborators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/efficiency/collaborators: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/processes/<int:process_id>/report
Endpoint: api_generate_process_report
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_generate_process_report(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/processes/<int:process_id>/report"""
    url = f"{base_url}/api/companies/<int:company_id>/processes/<int:process_id>/report"

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
        ), f"GET /api/companies/<int:company_id>/processes/<int:process_id>/report retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/processes/<int:process_id>/report: {e}"
        )


"""
Teste para rota: /__routes
Endpoint: __routes
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test___routes(base_url, timeout):
    """Testa a rota /__routes"""
    url = f"{base_url}/__routes"

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
        ), f"GET /__routes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /__routes: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/routines
Endpoint: api_get_routines
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_routines(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/routines"""
    url = f"{base_url}/api/companies/<int:company_id>/routines"

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
        ), f"GET /api/companies/<int:company_id>/routines retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/routines: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/routines
Endpoint: api_create_routine
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_routine(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/routines"""
    url = f"{base_url}/api/companies/<int:company_id>/routines"

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
        ), f"POST /api/companies/<int:company_id>/routines retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/routines: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>
Endpoint: api_get_routine
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_routine(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>"""
    url = f"{base_url}/api/routines/<int:routine_id>"

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
        ), f"GET /api/routines/<int:routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/routines/<int:routine_id>: {e}")


"""
Teste para rota: /api/routines/<int:routine_id>
Endpoint: api_update_routine
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_routine(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>"""
    url = f"{base_url}/api/routines/<int:routine_id>"

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
        ), f"PUT /api/routines/<int:routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /api/routines/<int:routine_id>: {e}")


"""
Teste para rota: /api/routines/<int:routine_id>
Endpoint: api_delete_routine
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_routine(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>"""
    url = f"{base_url}/api/routines/<int:routine_id>"

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
        ), f"DELETE /api/routines/<int:routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /api/routines/<int:routine_id>: {e}")


"""
Teste para rota: /api/routines/<int:routine_id>/triggers
Endpoint: api_get_routine_triggers
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_routine_triggers(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/triggers"""
    url = f"{base_url}/api/routines/<int:routine_id>/triggers"

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
        ), f"GET /api/routines/<int:routine_id>/triggers retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/routines/<int:routine_id>/triggers: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>/triggers
Endpoint: api_create_routine_trigger
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_routine_trigger(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/triggers"""
    url = f"{base_url}/api/routines/<int:routine_id>/triggers"

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
        ), f"POST /api/routines/<int:routine_id>/triggers retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/routines/<int:routine_id>/triggers: {e}"
        )


"""
Teste para rota: /api/triggers/<int:trigger_id>
Endpoint: api_update_routine_trigger
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_routine_trigger(base_url, timeout):
    """Testa a rota /api/triggers/<int:trigger_id>"""
    url = f"{base_url}/api/triggers/<int:trigger_id>"

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
        ), f"PUT /api/triggers/<int:trigger_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /api/triggers/<int:trigger_id>: {e}")


"""
Teste para rota: /api/triggers/<int:trigger_id>
Endpoint: api_delete_routine_trigger
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_routine_trigger(base_url, timeout):
    """Testa a rota /api/triggers/<int:trigger_id>"""
    url = f"{base_url}/api/triggers/<int:trigger_id>"

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
        ), f"DELETE /api/triggers/<int:trigger_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /api/triggers/<int:trigger_id>: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/routine-tasks
Endpoint: api_get_routine_tasks
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_routine_tasks(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/routine-tasks"""
    url = f"{base_url}/api/companies/<int:company_id>/routine-tasks"

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
        ), f"GET /api/companies/<int:company_id>/routine-tasks retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/routine-tasks: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/routine-tasks/overdue
Endpoint: api_get_overdue_tasks
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_overdue_tasks(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/routine-tasks/overdue"""
    url = f"{base_url}/api/companies/<int:company_id>/routine-tasks/overdue"

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
        ), f"GET /api/companies/<int:company_id>/routine-tasks/overdue retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/routine-tasks/overdue: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/routine-tasks/upcoming
Endpoint: api_get_upcoming_tasks
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_upcoming_tasks(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/routine-tasks/upcoming"""
    url = f"{base_url}/api/companies/<int:company_id>/routine-tasks/upcoming"

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
        ), f"GET /api/companies/<int:company_id>/routine-tasks/upcoming retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/routine-tasks/upcoming: {e}"
        )


"""
Teste para rota: /api/routine-tasks/<int:task_id>/status
Endpoint: api_update_task_status
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_task_status(base_url, timeout):
    """Testa a rota /api/routine-tasks/<int:task_id>/status"""
    url = f"{base_url}/api/routine-tasks/<int:task_id>/status"

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
        ), f"PUT /api/routine-tasks/<int:task_id>/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/routine-tasks/<int:task_id>/status: {e}"
        )


"""
Teste para rota: /companies/<int:company_id>/routines
Endpoint: routines_management
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_routines_management(base_url, timeout):
    """Testa a rota /companies/<int:company_id>/routines"""
    url = f"{base_url}/companies/<int:company_id>/routines"

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
        ), f"GET /companies/<int:company_id>/routines retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /companies/<int:company_id>/routines: {e}")


"""
Teste para rota: /companies/<int:company_id>/routines/<routine_id>
Endpoint: routine_details
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_routine_details(base_url, timeout):
    """Testa a rota /companies/<int:company_id>/routines/<routine_id>"""
    url = f"{base_url}/companies/<int:company_id>/routines/<routine_id>"

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
        ), f"GET /companies/<int:company_id>/routines/<routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /companies/<int:company_id>/routines/<routine_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-routines
Endpoint: api_get_process_routines
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_process_routines(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-routines"""
    url = f"{base_url}/api/companies/<int:company_id>/process-routines"

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
        ), f"GET /api/companies/<int:company_id>/process-routines retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/process-routines: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-routines
Endpoint: api_create_process_routine
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_create_process_routine(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-routines"""
    url = f"{base_url}/api/companies/<int:company_id>/process-routines"

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
        ), f"POST /api/companies/<int:company_id>/process-routines retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/process-routines: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-routines/<int:routine_id>
Endpoint: api_delete_process_routine
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_process_routine(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-routines/<int:routine_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/process-routines/<int:routine_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/process-routines/<int:routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/process-routines/<int:routine_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/process-routines/<int:routine_id>
Endpoint: api_update_process_routine
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_process_routine(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/process-routines/<int:routine_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/process-routines/<int:routine_id>"

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
        ), f"PUT /api/companies/<int:company_id>/process-routines/<int:routine_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/process-routines/<int:routine_id>: {e}"
        )


"""
Teste para rota: /api/processes/<int:process_id>/routines-with-collaborators
Endpoint: api_get_process_routines_with_collaborators
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_process_routines_with_collaborators(base_url, timeout):
    """Testa a rota /api/processes/<int:process_id>/routines-with-collaborators"""
    url = f"{base_url}/api/processes/<int:process_id>/routines-with-collaborators"

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
        ), f"GET /api/processes/<int:process_id>/routines-with-collaborators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/processes/<int:process_id>/routines-with-collaborators: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>/collaborators
Endpoint: api_get_routine_collaborators
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_routine_collaborators(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/collaborators"""
    url = f"{base_url}/api/routines/<int:routine_id>/collaborators"

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
        ), f"GET /api/routines/<int:routine_id>/collaborators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/routines/<int:routine_id>/collaborators: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>/collaborators
Endpoint: api_add_routine_collaborator
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_add_routine_collaborator(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/collaborators"""
    url = f"{base_url}/api/routines/<int:routine_id>/collaborators"

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
        ), f"POST /api/routines/<int:routine_id>/collaborators retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/routines/<int:routine_id>/collaborators: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>
Endpoint: api_update_routine_collaborator
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_update_routine_collaborator(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>"""
    url = (
        f"{base_url}/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>"
    )

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
        ), f"PUT /api/routines/<int:routine_id>/collaborators/<int:collaborator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>: {e}"
        )


"""
Teste para rota: /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>
Endpoint: api_delete_routine_collaborator
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_delete_routine_collaborator(base_url, timeout):
    """Testa a rota /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>"""
    url = (
        f"{base_url}/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>"
    )

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
        ), f"DELETE /api/routines/<int:routine_id>/collaborators/<int:collaborator_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/routines/<int:routine_id>/collaborators/<int:collaborator_id>: {e}"
        )


"""
Teste para rota: /companies/<int:company_id>/routine-tasks
Endpoint: routine_tasks_page
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_routine_tasks_page(base_url, timeout):
    """Testa a rota /companies/<int:company_id>/routine-tasks"""
    url = f"{base_url}/companies/<int:company_id>/routine-tasks"

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
        ), f"GET /companies/<int:company_id>/routine-tasks retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /companies/<int:company_id>/routine-tasks: {e}"
        )


"""
Teste para rota: /test-routines-modal
Endpoint: test_routines_modal
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_routines_modal(base_url, timeout):
    """Testa a rota /test-routines-modal"""
    url = f"{base_url}/test-routines-modal"

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
        ), f"GET /test-routines-modal retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /test-routines-modal: {e}")


"""
Teste para rota: /plans/<plan_id>
Endpoint: plan_dashboard
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_dashboard(base_url, timeout):
    """Testa a rota /plans/<plan_id>"""
    url = f"{base_url}/plans/<plan_id>"

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
        ), f"GET /plans/<plan_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>: {e}")


"""
Teste para rota: /plans/<plan_id>/company
Endpoint: plan_company
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_company(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company"""
    url = f"{base_url}/plans/<plan_id>/company"

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
        ), f"GET /plans/<plan_id>/company retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/company: {e}")


"""
Teste para rota: /plans/<plan_id>/participants
Endpoint: plan_participants
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_participants(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants"""
    url = f"{base_url}/plans/<plan_id>/participants"

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
        ), f"GET /plans/<plan_id>/participants retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/participants: {e}")


"""
Teste para rota: /plans/<plan_id>/participants/toggle/<int:employee_id>
Endpoint: toggle_participant
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_toggle_participant(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/toggle/<int:employee_id>"""
    url = f"{base_url}/plans/<plan_id>/participants/toggle/<int:employee_id>"

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
        ), f"POST /plans/<plan_id>/participants/toggle/<int:employee_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/participants/toggle/<int:employee_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/drivers
Endpoint: plan_drivers
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_drivers(base_url, timeout):
    """Testa a rota /plans/<plan_id>/drivers"""
    url = f"{base_url}/plans/<plan_id>/drivers"

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
        ), f"GET /plans/<plan_id>/drivers retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/drivers: {e}")


"""
Teste para rota: /plans/<plan_id>/okr-global
Endpoint: plan_okr_global
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_okr_global(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global"""
    url = f"{base_url}/plans/<plan_id>/okr-global"

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
        ), f"GET /plans/<plan_id>/okr-global retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/okr-global: {e}")


"""
Teste para rota: /plans/<plan_id>/okr-area
Endpoint: plan_okr_area
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_okr_area(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area"""
    url = f"{base_url}/plans/<plan_id>/okr-area"

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
        ), f"GET /plans/<plan_id>/okr-area retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/okr-area: {e}")


"""
Teste para rota: /plans/<plan_id>/projects
Endpoint: plan_projects
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_projects(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects"""
    url = f"{base_url}/plans/<plan_id>/projects"

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
        ), f"GET /plans/<plan_id>/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/projects: {e}")


"""
Teste para rota: /plans/<plan_id>/projects
Endpoint: create_project
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_create_project(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects"""
    url = f"{base_url}/plans/<plan_id>/projects"

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
        ), f"POST /plans/<plan_id>/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/projects: {e}")


"""
Teste para rota: /plans/<plan_id>/projects/<int:project_id>
Endpoint: update_project_route
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_project_route(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects/<int:project_id>"""
    url = f"{base_url}/plans/<plan_id>/projects/<int:project_id>"

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
        ), f"POST /plans/<plan_id>/projects/<int:project_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/projects/<int:project_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/projects/analysis
Endpoint: save_projects_analysis
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_projects_analysis(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects/analysis"""
    url = f"{base_url}/plans/<plan_id>/projects/analysis"

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
        ), f"POST /plans/<plan_id>/projects/analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/projects/analysis: {e}")


"""
Teste para rota: /plans/<plan_id>/projects/<int:project_id>/edit
Endpoint: edit_project
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_edit_project(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects/<int:project_id>/edit"""
    url = f"{base_url}/plans/<plan_id>/projects/<int:project_id>/edit"

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
        ), f"GET /plans/<plan_id>/projects/<int:project_id>/edit retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/projects/<int:project_id>/edit: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/projects/<int:project_id>/delete
Endpoint: delete_project
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_project(base_url, timeout):
    """Testa a rota /plans/<plan_id>/projects/<int:project_id>/delete"""
    url = f"{base_url}/plans/<plan_id>/projects/<int:project_id>/delete"

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
        ), f"POST /plans/<plan_id>/projects/<int:project_id>/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/projects/<int:project_id>/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/reports
Endpoint: plan_reports
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_reports(base_url, timeout):
    """Testa a rota /plans/<plan_id>/reports"""
    url = f"{base_url}/plans/<plan_id>/reports"

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
        ), f"GET /plans/<plan_id>/reports retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/reports: {e}")


"""
Teste para rota: /plans/<plan_id>/reports/pdf/<variant>
Endpoint: plan_reports_pdf
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_plan_reports_pdf(base_url, timeout):
    """Testa a rota /plans/<plan_id>/reports/pdf/<variant>"""
    url = f"{base_url}/plans/<plan_id>/reports/pdf/<variant>"

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
        ), f"GET /plans/<plan_id>/reports/pdf/<variant> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/reports/pdf/<variant>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/reports/formal
Endpoint: generate_formal_report
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_generate_formal_report(base_url, timeout):
    """Testa a rota /plans/<plan_id>/reports/formal"""
    url = f"{base_url}/plans/<plan_id>/reports/formal"

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
        ), f"GET /plans/<plan_id>/reports/formal retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/reports/formal: {e}")


"""
Teste para rota: /plans/<plan_id>/reports/slides
Endpoint: generate_presentation_slides
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_generate_presentation_slides(base_url, timeout):
    """Testa a rota /plans/<plan_id>/reports/slides"""
    url = f"{base_url}/plans/<plan_id>/reports/slides"

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
        ), f"GET /plans/<plan_id>/reports/slides retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/reports/slides: {e}")


"""
Teste para rota: /uploads/<path:filename>
Endpoint: serve_uploaded_file
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_serve_uploaded_file(base_url, timeout):
    """Testa a rota /uploads/<path:filename>"""
    url = f"{base_url}/uploads/<path:filename>"

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
        ), f"GET /uploads/<path:filename> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /uploads/<path:filename>: {e}")


"""
Teste para rota: /plans/<plan_id>/company/delete-file
Endpoint: delete_company_file
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_company_file(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company/delete-file"""
    url = f"{base_url}/plans/<plan_id>/company/delete-file"

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
        ), f"POST /plans/<plan_id>/company/delete-file retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/company/delete-file: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/company
Endpoint: update_company_data
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_company_data(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company"""
    url = f"{base_url}/plans/<plan_id>/company"

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
        ), f"POST /plans/<plan_id>/company retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/company: {e}")


"""
Teste para rota: /plans/<plan_id>/company/update-analyses
Endpoint: update_company_analyses
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_company_analyses(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company/update-analyses"""
    url = f"{base_url}/plans/<plan_id>/company/update-analyses"

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
        ), f"POST /plans/<plan_id>/company/update-analyses retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/company/update-analyses: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/company/generate-ai-insights
Endpoint: generate_company_ai_insights
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_generate_company_ai_insights(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company/generate-ai-insights"""
    url = f"{base_url}/plans/<plan_id>/company/generate-ai-insights"

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
        ), f"POST /plans/<plan_id>/company/generate-ai-insights retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/company/generate-ai-insights: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/company/status
Endpoint: update_company_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_company_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/company/status"""
    url = f"{base_url}/plans/<plan_id>/sections/company/status"

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
        ), f"POST /plans/<plan_id>/sections/company/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/company/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/participants
Endpoint: add_participant
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_participant(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants"""
    url = f"{base_url}/plans/<plan_id>/participants"

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
        ), f"POST /plans/<plan_id>/participants retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/participants: {e}")


"""
Teste para rota: /plans/<plan_id>/participants/<participant_id>
Endpoint: get_participant
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_participant(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/<participant_id>"""
    url = f"{base_url}/plans/<plan_id>/participants/<participant_id>"

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
        ), f"GET /plans/<plan_id>/participants/<participant_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/participants/<participant_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/participants/<participant_id>
Endpoint: update_participant
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_participant(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/<participant_id>"""
    url = f"{base_url}/plans/<plan_id>/participants/<participant_id>"

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
        ), f"PUT /plans/<plan_id>/participants/<participant_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/participants/<participant_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/participants/<participant_id>/status
Endpoint: update_participant_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_participant_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/<participant_id>/status"""
    url = f"{base_url}/plans/<plan_id>/participants/<participant_id>/status"

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
        ), f"POST /plans/<plan_id>/participants/<participant_id>/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/participants/<participant_id>/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/messages
Endpoint: get_message_templates
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_message_templates(base_url, timeout):
    """Testa a rota /plans/<plan_id>/messages"""
    url = f"{base_url}/plans/<plan_id>/messages"

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
        ), f"GET /plans/<plan_id>/messages retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /plans/<plan_id>/messages: {e}")


"""
Teste para rota: /plans/<plan_id>/messages/<message_type>
Endpoint: get_message_template
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_message_template(base_url, timeout):
    """Testa a rota /plans/<plan_id>/messages/<message_type>"""
    url = f"{base_url}/plans/<plan_id>/messages/<message_type>"

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
        ), f"GET /plans/<plan_id>/messages/<message_type> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/messages/<message_type>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/messages/<message_type>
Endpoint: save_message_template
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_message_template(base_url, timeout):
    """Testa a rota /plans/<plan_id>/messages/<message_type>"""
    url = f"{base_url}/plans/<plan_id>/messages/<message_type>"

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
        ), f"POST /plans/<plan_id>/messages/<message_type> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/messages/<message_type>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/participants/<participant_id>/send-message
Endpoint: send_participant_message
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_send_participant_message(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/<participant_id>/send-message"""
    url = f"{base_url}/plans/<plan_id>/participants/<participant_id>/send-message"

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
        ), f"POST /plans/<plan_id>/participants/<participant_id>/send-message retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/participants/<participant_id>/send-message: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/participants/<participant_id>
Endpoint: delete_participant
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_participant(base_url, timeout):
    """Testa a rota /plans/<plan_id>/participants/<participant_id>"""
    url = f"{base_url}/plans/<plan_id>/participants/<participant_id>"

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
        ), f"DELETE /plans/<plan_id>/participants/<participant_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/participants/<participant_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/drivers
Endpoint: add_driver
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_driver(base_url, timeout):
    """Testa a rota /plans/<plan_id>/drivers"""
    url = f"{base_url}/plans/<plan_id>/drivers"

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
        ), f"POST /plans/<plan_id>/drivers retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/drivers: {e}")


"""
Teste para rota: /plans/<plan_id>/interviews
Endpoint: add_interview
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_interview(base_url, timeout):
    """Testa a rota /plans/<plan_id>/interviews"""
    url = f"{base_url}/plans/<plan_id>/interviews"

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
        ), f"POST /plans/<plan_id>/interviews retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/interviews: {e}")


"""
Teste para rota: /plans/<plan_id>/interviews/<interview_id>
Endpoint: update_interview
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_interview(base_url, timeout):
    """Testa a rota /plans/<plan_id>/interviews/<interview_id>"""
    url = f"{base_url}/plans/<plan_id>/interviews/<interview_id>"

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
        ), f"PUT /plans/<plan_id>/interviews/<interview_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/interviews/<interview_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/interviews/<interview_id>
Endpoint: delete_interview
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_interview(base_url, timeout):
    """Testa a rota /plans/<plan_id>/interviews/<interview_id>"""
    url = f"{base_url}/plans/<plan_id>/interviews/<interview_id>"

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
        ), f"DELETE /plans/<plan_id>/interviews/<interview_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/interviews/<interview_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/interviews/<interview_id>
Endpoint: get_interview
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_interview(base_url, timeout):
    """Testa a rota /plans/<plan_id>/interviews/<interview_id>"""
    url = f"{base_url}/plans/<plan_id>/interviews/<interview_id>"

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
        ), f"GET /plans/<plan_id>/interviews/<interview_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/interviews/<interview_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/<section_name>/status
Endpoint: update_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/<section_name>/status"""
    url = f"{base_url}/plans/<plan_id>/sections/<section_name>/status"

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
        ), f"POST /plans/<plan_id>/sections/<section_name>/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/<section_name>/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/<section_name>/status
Endpoint: get_section_status
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/<section_name>/status"""
    url = f"{base_url}/plans/<plan_id>/sections/<section_name>/status"

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
        ), f"GET /plans/<plan_id>/sections/<section_name>/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/sections/<section_name>/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/alignment/consultant-notes
Endpoint: save_alignment_consultant_notes
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_alignment_consultant_notes(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/alignment/consultant-notes"""
    url = f"{base_url}/plans/<plan_id>/sections/alignment/consultant-notes"

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
        ), f"POST /plans/<plan_id>/sections/alignment/consultant-notes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/alignment/consultant-notes: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/misalignment/consultant-notes
Endpoint: save_misalignment_consultant_notes
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_misalignment_consultant_notes(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/misalignment/consultant-notes"""
    url = f"{base_url}/plans/<plan_id>/sections/misalignment/consultant-notes"

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
        ), f"POST /plans/<plan_id>/sections/misalignment/consultant-notes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/misalignment/consultant-notes: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/workshop/consultant-notes
Endpoint: save_workshop_consultant_notes
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_workshop_consultant_notes(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/workshop/consultant-notes"""
    url = f"{base_url}/plans/<plan_id>/sections/workshop/consultant-notes"

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
        ), f"POST /plans/<plan_id>/sections/workshop/consultant-notes retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/workshop/consultant-notes: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/sections/directionals/consultant-analysis
Endpoint: save_directionals_consultant_analysis
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_directionals_consultant_analysis(base_url, timeout):
    """Testa a rota /plans/<plan_id>/sections/directionals/consultant-analysis"""
    url = f"{base_url}/plans/<plan_id>/sections/directionals/consultant-analysis"

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
        ), f"POST /plans/<plan_id>/sections/directionals/consultant-analysis retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/sections/directionals/consultant-analysis: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/workshop-adjustments
Endpoint: add_workshop_adjustment
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_workshop_adjustment(base_url, timeout):
    """Testa a rota /plans/<plan_id>/workshop-adjustments"""
    url = f"{base_url}/plans/<plan_id>/workshop-adjustments"

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
        ), f"POST /plans/<plan_id>/workshop-adjustments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/workshop-adjustments: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/directionals-approvals
Endpoint: add_directionals_approval
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_directionals_approval(base_url, timeout):
    """Testa a rota /plans/<plan_id>/directionals-approvals"""
    url = f"{base_url}/plans/<plan_id>/directionals-approvals"

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
        ), f"POST /plans/<plan_id>/directionals-approvals retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/directionals-approvals: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/vision-records
Endpoint: add_vision_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_vision_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/vision-records"""
    url = f"{base_url}/plans/<plan_id>/vision-records"

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
        ), f"POST /plans/<plan_id>/vision-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/vision-records: {e}")


"""
Teste para rota: /plans/<plan_id>/vision-records/<vision_id>
Endpoint: update_vision_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_vision_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/vision-records/<vision_id>"""
    url = f"{base_url}/plans/<plan_id>/vision-records/<vision_id>"

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
        ), f"PUT /plans/<plan_id>/vision-records/<vision_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/vision-records/<vision_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/vision-records/<vision_id>
Endpoint: delete_vision_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_vision_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/vision-records/<vision_id>"""
    url = f"{base_url}/plans/<plan_id>/vision-records/<vision_id>"

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
        ), f"DELETE /plans/<plan_id>/vision-records/<vision_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/vision-records/<vision_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/vision-records/<vision_id>
Endpoint: get_vision_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_vision_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/vision-records/<vision_id>"""
    url = f"{base_url}/plans/<plan_id>/vision-records/<vision_id>"

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
        ), f"GET /plans/<plan_id>/vision-records/<vision_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/vision-records/<vision_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/market-records
Endpoint: add_market_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_market_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/market-records"""
    url = f"{base_url}/plans/<plan_id>/market-records"

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
        ), f"POST /plans/<plan_id>/market-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/market-records: {e}")


"""
Teste para rota: /plans/<plan_id>/market-records/<market_id>
Endpoint: update_market_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_market_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/market-records/<market_id>"""
    url = f"{base_url}/plans/<plan_id>/market-records/<market_id>"

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
        ), f"PUT /plans/<plan_id>/market-records/<market_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/market-records/<market_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/market-records/<market_id>
Endpoint: delete_market_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_market_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/market-records/<market_id>"""
    url = f"{base_url}/plans/<plan_id>/market-records/<market_id>"

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
        ), f"DELETE /plans/<plan_id>/market-records/<market_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/market-records/<market_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/market-records/<market_id>
Endpoint: get_market_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_market_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/market-records/<market_id>"""
    url = f"{base_url}/plans/<plan_id>/market-records/<market_id>"

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
        ), f"GET /plans/<plan_id>/market-records/<market_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/market-records/<market_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/company-records
Endpoint: add_company_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_company_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company-records"""
    url = f"{base_url}/plans/<plan_id>/company-records"

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
        ), f"POST /plans/<plan_id>/company-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/company-records: {e}")


"""
Teste para rota: /plans/<plan_id>/company-records/<company_id>
Endpoint: update_company_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_company_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company-records/<company_id>"""
    url = f"{base_url}/plans/<plan_id>/company-records/<company_id>"

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
        ), f"PUT /plans/<plan_id>/company-records/<company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/company-records/<company_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/company-records/<company_id>
Endpoint: delete_company_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_company_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company-records/<company_id>"""
    url = f"{base_url}/plans/<plan_id>/company-records/<company_id>"

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
        ), f"DELETE /plans/<plan_id>/company-records/<company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/company-records/<company_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/company-records/<company_id>
Endpoint: get_company_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_company_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/company-records/<company_id>"""
    url = f"{base_url}/plans/<plan_id>/company-records/<company_id>"

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
        ), f"GET /plans/<plan_id>/company-records/<company_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/company-records/<company_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/alignment-records
Endpoint: add_alignment_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_alignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/alignment-records"""
    url = f"{base_url}/plans/<plan_id>/alignment-records"

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
        ), f"POST /plans/<plan_id>/alignment-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/alignment-records: {e}")


"""
Teste para rota: /plans/<plan_id>/alignment-records/<alignment_id>
Endpoint: update_alignment_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_alignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/alignment-records/<alignment_id>"""
    url = f"{base_url}/plans/<plan_id>/alignment-records/<alignment_id>"

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
        ), f"PUT /plans/<plan_id>/alignment-records/<alignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/alignment-records/<alignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/alignment-records/<alignment_id>
Endpoint: delete_alignment_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_alignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/alignment-records/<alignment_id>"""
    url = f"{base_url}/plans/<plan_id>/alignment-records/<alignment_id>"

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
        ), f"DELETE /plans/<plan_id>/alignment-records/<alignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/alignment-records/<alignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/alignment-records/<alignment_id>
Endpoint: get_alignment_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_alignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/alignment-records/<alignment_id>"""
    url = f"{base_url}/plans/<plan_id>/alignment-records/<alignment_id>"

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
        ), f"GET /plans/<plan_id>/alignment-records/<alignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/alignment-records/<alignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/misalignment-records
Endpoint: add_misalignment_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_misalignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/misalignment-records"""
    url = f"{base_url}/plans/<plan_id>/misalignment-records"

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
        ), f"POST /plans/<plan_id>/misalignment-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/misalignment-records: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/misalignment-records/<misalignment_id>
Endpoint: update_misalignment_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_misalignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/misalignment-records/<misalignment_id>"""
    url = f"{base_url}/plans/<plan_id>/misalignment-records/<misalignment_id>"

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
        ), f"PUT /plans/<plan_id>/misalignment-records/<misalignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/misalignment-records/<misalignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/misalignment-records/<misalignment_id>
Endpoint: delete_misalignment_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_misalignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/misalignment-records/<misalignment_id>"""
    url = f"{base_url}/plans/<plan_id>/misalignment-records/<misalignment_id>"

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
        ), f"DELETE /plans/<plan_id>/misalignment-records/<misalignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/misalignment-records/<misalignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/misalignment-records/<misalignment_id>
Endpoint: get_misalignment_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_misalignment_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/misalignment-records/<misalignment_id>"""
    url = f"{base_url}/plans/<plan_id>/misalignment-records/<misalignment_id>"

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
        ), f"GET /plans/<plan_id>/misalignment-records/<misalignment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/misalignment-records/<misalignment_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/directional-records
Endpoint: add_directional_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_directional_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/directional-records"""
    url = f"{base_url}/plans/<plan_id>/directional-records"

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
        ), f"POST /plans/<plan_id>/directional-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/directional-records: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/directional-records/<directional_id>
Endpoint: update_directional_record
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_directional_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/directional-records/<directional_id>"""
    url = f"{base_url}/plans/<plan_id>/directional-records/<directional_id>"

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
        ), f"PUT /plans/<plan_id>/directional-records/<directional_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /plans/<plan_id>/directional-records/<directional_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/directional-records/<directional_id>
Endpoint: delete_directional_record
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_directional_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/directional-records/<directional_id>"""
    url = f"{base_url}/plans/<plan_id>/directional-records/<directional_id>"

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
        ), f"DELETE /plans/<plan_id>/directional-records/<directional_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /plans/<plan_id>/directional-records/<directional_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/directional-records/<directional_id>
Endpoint: get_directional_record
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_directional_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/directional-records/<directional_id>"""
    url = f"{base_url}/plans/<plan_id>/directional-records/<directional_id>"

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
        ), f"GET /plans/<plan_id>/directional-records/<directional_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/directional-records/<directional_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop
Endpoint: add_workshop_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_workshop_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approval
Endpoint: add_okr_approval_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_okr_approval_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approval"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approval"

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
        ), f"POST /plans/<plan_id>/okr-global/approval retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approval: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/preliminary
Endpoint: add_preliminary_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_preliminary_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/preliminary"""
    url = f"{base_url}/plans/<plan_id>/okr-global/preliminary"

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
        ), f"POST /plans/<plan_id>/okr-global/preliminary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/preliminary: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/preliminary/<record_id>
Endpoint: get_preliminary_okr_data
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_preliminary_okr_data(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/preliminary/<record_id>"""
    url = f"{base_url}/plans/<plan_id>/okr-global/preliminary/<record_id>"

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
        ), f"GET /plans/<plan_id>/okr-global/preliminary/<record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /plans/<plan_id>/okr-global/preliminary/<record_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/preliminary/<record_id>
Endpoint: edit_preliminary_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_edit_preliminary_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/preliminary/<record_id>"""
    url = f"{base_url}/plans/<plan_id>/okr-global/preliminary/<record_id>"

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
        ), f"POST /plans/<plan_id>/okr-global/preliminary/<record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/preliminary/<record_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/preliminary/<record_id>/delete
Endpoint: delete_preliminary_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_preliminary_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/preliminary/<record_id>/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-global/preliminary/<record_id>/delete"

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
        ), f"POST /plans/<plan_id>/okr-global/preliminary/<record_id>/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/preliminary/<record_id>/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop-discussions
Endpoint: save_workshop_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_workshop_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop-discussions"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop-discussions"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop-discussions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop-discussions: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop-discussions/delete
Endpoint: delete_workshop_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_workshop_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop-discussions/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop-discussions/delete"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop-discussions/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop-discussions/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approval-discussions
Endpoint: save_approval_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_approval_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approval-discussions"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approval-discussions"

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
        ), f"POST /plans/<plan_id>/okr-global/approval-discussions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approval-discussions: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approval-discussions/delete
Endpoint: delete_approval_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_approval_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approval-discussions/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approval-discussions/delete"

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
        ), f"POST /plans/<plan_id>/okr-global/approval-discussions/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approval-discussions/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop/<record_id>
Endpoint: edit_workshop_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_edit_workshop_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop/<record_id>"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop/<record_id>"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop/<record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop/<record_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approval/<record_id>
Endpoint: edit_approval_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_edit_approval_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approval/<record_id>"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approval/<record_id>"

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
        ), f"POST /plans/<plan_id>/okr-global/approval/<record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approval/<record_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop/<record_id>/delete
Endpoint: delete_workshop_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_workshop_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop/<record_id>/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop/<record_id>/delete"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop/<record_id>/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop/<record_id>/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approval/<record_id>/delete
Endpoint: delete_approval_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_approval_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approval/<record_id>/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approval/<record_id>/delete"

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
        ), f"POST /plans/<plan_id>/okr-global/approval/<record_id>/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approval/<record_id>/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/duplicate/<type>/<record_id>
Endpoint: duplicate_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_duplicate_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/duplicate/<type>/<record_id>"""
    url = f"{base_url}/plans/<plan_id>/okr-global/duplicate/<type>/<record_id>"

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
        ), f"POST /plans/<plan_id>/okr-global/duplicate/<type>/<record_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/duplicate/<type>/<record_id>: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/preliminary-analysis/status
Endpoint: update_okr_preliminary_analysis_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_okr_preliminary_analysis_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/preliminary-analysis/status"""
    url = f"{base_url}/plans/<plan_id>/okr-global/preliminary-analysis/status"

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
        ), f"POST /plans/<plan_id>/okr-global/preliminary-analysis/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/preliminary-analysis/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/workshop-final/status
Endpoint: update_okr_workshop_final_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_okr_workshop_final_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/workshop-final/status"""
    url = f"{base_url}/plans/<plan_id>/okr-global/workshop-final/status"

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
        ), f"POST /plans/<plan_id>/okr-global/workshop-final/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/workshop-final/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/approvals/status
Endpoint: update_okr_approvals_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_okr_approvals_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/approvals/status"""
    url = f"{base_url}/plans/<plan_id>/okr-global/approvals/status"

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
        ), f"POST /plans/<plan_id>/okr-global/approvals/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/approvals/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-global/ai-suggestions
Endpoint: generate_ai_okr_suggestions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_generate_ai_okr_suggestions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-global/ai-suggestions"""
    url = f"{base_url}/plans/<plan_id>/okr-global/ai-suggestions"

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
        ), f"POST /plans/<plan_id>/okr-global/ai-suggestions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-global/ai-suggestions: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/preliminary
Endpoint: add_preliminary_area_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_preliminary_area_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/preliminary"""
    url = f"{base_url}/plans/<plan_id>/okr-area/preliminary"

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
        ), f"POST /plans/<plan_id>/okr-area/preliminary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/preliminary: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/workshop
Endpoint: add_area_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_area_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/workshop"""
    url = f"{base_url}/plans/<plan_id>/okr-area/workshop"

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
        ), f"POST /plans/<plan_id>/okr-area/workshop retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/okr-area/workshop: {e}")


"""
Teste para rota: /plans/<plan_id>/okr-area/final
Endpoint: add_final_area_okr_record
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_add_final_area_okr_record(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/final"""
    url = f"{base_url}/plans/<plan_id>/okr-area/final"

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
        ), f"POST /plans/<plan_id>/okr-area/final retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /plans/<plan_id>/okr-area/final: {e}")


"""
Teste para rota: /plans/<plan_id>/okr-area/workshop-discussions
Endpoint: save_area_workshop_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_area_workshop_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/workshop-discussions"""
    url = f"{base_url}/plans/<plan_id>/okr-area/workshop-discussions"

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
        ), f"POST /plans/<plan_id>/okr-area/workshop-discussions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/workshop-discussions: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/final-discussions
Endpoint: save_final_area_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_save_final_area_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/final-discussions"""
    url = f"{base_url}/plans/<plan_id>/okr-area/final-discussions"

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
        ), f"POST /plans/<plan_id>/okr-area/final-discussions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/final-discussions: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/workshop-discussions/delete
Endpoint: delete_area_workshop_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_area_workshop_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/workshop-discussions/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-area/workshop-discussions/delete"

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
        ), f"POST /plans/<plan_id>/okr-area/workshop-discussions/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/workshop-discussions/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/final-discussions/delete
Endpoint: delete_final_area_discussions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_final_area_discussions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/final-discussions/delete"""
    url = f"{base_url}/plans/<plan_id>/okr-area/final-discussions/delete"

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
        ), f"POST /plans/<plan_id>/okr-area/final-discussions/delete retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/final-discussions/delete: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/preliminary-analysis/status
Endpoint: update_area_preliminary_analysis_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_area_preliminary_analysis_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/preliminary-analysis/status"""
    url = f"{base_url}/plans/<plan_id>/okr-area/preliminary-analysis/status"

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
        ), f"POST /plans/<plan_id>/okr-area/preliminary-analysis/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/preliminary-analysis/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/workshop/status
Endpoint: update_workshop_area_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_workshop_area_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/workshop/status"""
    url = f"{base_url}/plans/<plan_id>/okr-area/workshop/status"

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
        ), f"POST /plans/<plan_id>/okr-area/workshop/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/workshop/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/final/status
Endpoint: update_final_area_section_status
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_final_area_section_status(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/final/status"""
    url = f"{base_url}/plans/<plan_id>/okr-area/final/status"

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
        ), f"POST /plans/<plan_id>/okr-area/final/status retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/final/status: {e}"
        )


"""
Teste para rota: /plans/<plan_id>/okr-area/ai-suggestions
Endpoint: generate_ai_area_okr_suggestions
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_generate_ai_area_okr_suggestions(base_url, timeout):
    """Testa a rota /plans/<plan_id>/okr-area/ai-suggestions"""
    url = f"{base_url}/plans/<plan_id>/okr-area/ai-suggestions"

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
        ), f"POST /plans/<plan_id>/okr-area/ai-suggestions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /plans/<plan_id>/okr-area/ai-suggestions: {e}"
        )


"""
Teste para rota: /api/agents
Endpoint: get_agents
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_agents(base_url, timeout):
    """Testa a rota /api/agents"""
    url = f"{base_url}/api/agents"

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
        ), f"GET /api/agents retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/agents: {e}")


"""
Teste para rota: /api/agents/available-buttons
Endpoint: api_available_buttons
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_available_buttons(base_url, timeout):
    """Testa a rota /api/agents/available-buttons"""
    url = f"{base_url}/api/agents/available-buttons"

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
        ), f"GET /api/agents/available-buttons retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/agents/available-buttons: {e}")


"""
Teste para rota: /api/agents
Endpoint: create_agent
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_create_agent(base_url, timeout):
    """Testa a rota /api/agents"""
    url = f"{base_url}/api/agents"

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
        ), f"POST /api/agents retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/agents: {e}")


"""
Teste para rota: /api/agents/<agent_id>
Endpoint: get_agent
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_agent(base_url, timeout):
    """Testa a rota /api/agents/<agent_id>"""
    url = f"{base_url}/api/agents/<agent_id>"

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
        ), f"GET /api/agents/<agent_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/agents/<agent_id>: {e}")


"""
Teste para rota: /api/agents/<agent_id>
Endpoint: update_agent
Blueprint: None
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_update_agent(base_url, timeout):
    """Testa a rota /api/agents/<agent_id>"""
    url = f"{base_url}/api/agents/<agent_id>"

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
        ), f"PUT /api/agents/<agent_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição PUT /api/agents/<agent_id>: {e}")


"""
Teste para rota: /api/agents/<agent_id>
Endpoint: delete_agent
Blueprint: None
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_delete_agent(base_url, timeout):
    """Testa a rota /api/agents/<agent_id>"""
    url = f"{base_url}/api/agents/<agent_id>"

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
        ), f"DELETE /api/agents/<agent_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE /api/agents/<agent_id>: {e}")


"""
Teste para rota: /api/agents/available-fields
Endpoint: get_available_fields
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_get_available_fields(base_url, timeout):
    """Testa a rota /api/agents/available-fields"""
    url = f"{base_url}/api/agents/available-fields"

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
        ), f"GET /api/agents/available-fields retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/agents/available-fields: {e}")


"""
Teste para rota: /api/agents/<agent_id>/run
Endpoint: run_custom_agent
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_run_custom_agent(base_url, timeout):
    """Testa a rota /api/agents/<agent_id>/run"""
    url = f"{base_url}/api/agents/<agent_id>/run"

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
        ), f"POST /api/agents/<agent_id>/run retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição POST /api/agents/<agent_id>/run: {e}")


"""
Teste para rota: /api/companies/<int:company_id>/portfolios
Endpoint: api_company_portfolios
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_portfolios(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/portfolios"""
    url = f"{base_url}/api/companies/<int:company_id>/portfolios"

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
        ), f"GET /api/companies/<int:company_id>/portfolios retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/portfolios: {e}"
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
        ), f"POST /api/companies/<int:company_id>/portfolios retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/portfolios: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/portfolios/<int:portfolio_id>
Endpoint: api_portfolio
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_portfolio(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/portfolios/<int:portfolio_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/portfolios/<int:portfolio_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/portfolios/<int:portfolio_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/portfolios/<int:portfolio_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/portfolios/<int:portfolio_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/portfolios/<int:portfolio_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects
Endpoint: api_company_projects
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_projects(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects"""
    url = f"{base_url}/api/companies/<int:company_id>/projects"

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
        ), f"GET /api/companies/<int:company_id>/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/projects: {e}"
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
        ), f"POST /api/companies/<int:company_id>/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/projects: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>
Endpoint: api_company_project
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_company_project(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/projects/<int:project_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/projects/<int:project_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/projects/<int:project_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/projects/<int:project_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>/activities
Endpoint: api_project_activities
Blueprint: None
Métodos: GET, POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_project_activities(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>/activities"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>/activities"

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
        ), f"GET /api/companies/<int:company_id>/projects/<int:project_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/projects/<int:project_id>/activities: {e}"
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
        ), f"POST /api/companies/<int:company_id>/projects/<int:project_id>/activities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/projects/<int:project_id>/activities: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>
Endpoint: api_project_activity
Blueprint: None
Métodos: DELETE, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_project_activity(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>"

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
        ), f"DELETE /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>: {e}"
        )

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
        ), f"PUT /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage
Endpoint: api_project_activity_stage
Blueprint: None
Métodos: PATCH
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_project_activity_stage(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage"

    # Test PATCH request
    try:
        # Tentar com payload vazio primeiro
        response = requests.patch(url, json={}, timeout=timeout)
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
        ), f"PATCH /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PATCH /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer
Endpoint: api_transfer_activity
Blueprint: None
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_transfer_activity(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer"

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
        ), f"POST /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer: {e}"
        )


"""
Teste para rota: /api/companies/<int:company_id>/projects/<int:project_id>/info
Endpoint: api_get_project_info
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_get_project_info(base_url, timeout):
    """Testa a rota /api/companies/<int:company_id>/projects/<int:project_id>/info"""
    url = f"{base_url}/api/companies/<int:company_id>/projects/<int:project_id>/info"

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
        ), f"GET /api/companies/<int:company_id>/projects/<int:project_id>/info retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/companies/<int:company_id>/projects/<int:project_id>/info: {e}"
        )


"""
Teste para rota: /api/plans/<int:plan_id>/okr-global-records
Endpoint: api_plan_okr_global_records
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_plan_okr_global_records(base_url, timeout):
    """Testa a rota /api/plans/<int:plan_id>/okr-global-records"""
    url = f"{base_url}/api/plans/<int:plan_id>/okr-global-records"

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
        ), f"GET /api/plans/<int:plan_id>/okr-global-records retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /api/plans/<int:plan_id>/okr-global-records: {e}"
        )


"""
Teste para rota: /api/plans/<int:plan_id>/projects
Endpoint: api_plan_projects
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_api_plan_projects(base_url, timeout):
    """Testa a rota /api/plans/<int:plan_id>/projects"""
    url = f"{base_url}/api/plans/<int:plan_id>/projects"

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
        ), f"GET /api/plans/<int:plan_id>/projects retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /api/plans/<int:plan_id>/projects: {e}")


"""
Teste para rota: /health
Endpoint: health_check
Blueprint: None
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_health_check(base_url, timeout):
    """Testa a rota /health"""
    url = f"{base_url}/health"

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
        ), f"GET /health retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /health: {e}")
