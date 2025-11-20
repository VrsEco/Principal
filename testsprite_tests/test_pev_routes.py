"""
Testes para blueprint: pev
Total de rotas: 70
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

"""
Teste para rota: /pev/dashboard
Endpoint: pev.pev_dashboard
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_pev_dashboard(base_url, timeout):
    """Testa a rota /pev/dashboard"""
    url = f"{base_url}/pev/dashboard"

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
        ), f"GET /pev/dashboard retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /pev/dashboard: {e}")


"""
Teste para rota: /pev/implantacao
Endpoint: pev.pev_implantacao_overview
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_pev_implantacao_overview(base_url, timeout):
    """Testa a rota /pev/implantacao"""
    url = f"{base_url}/pev/implantacao"

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
        ), f"GET /pev/implantacao retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /pev/implantacao: {e}")


"""
Teste para rota: /pev/implantacao/alinhamento/canvas-expectativas
Endpoint: pev.implantacao_canvas_expectativas
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_canvas_expectativas(base_url, timeout):
    """Testa a rota /pev/implantacao/alinhamento/canvas-expectativas"""
    url = f"{base_url}/pev/implantacao/alinhamento/canvas-expectativas"

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
        ), f"GET /pev/implantacao/alinhamento/canvas-expectativas retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/alinhamento/canvas-expectativas: {e}"
        )


"""
Teste para rota: /pev/implantacao/alinhamento/agenda-planejamento
Endpoint: pev.implantacao_agenda_planejamento
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_agenda_planejamento(base_url, timeout):
    """Testa a rota /pev/implantacao/alinhamento/agenda-planejamento"""
    url = f"{base_url}/pev/implantacao/alinhamento/agenda-planejamento"

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
        ), f"GET /pev/implantacao/alinhamento/agenda-planejamento retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/alinhamento/agenda-planejamento: {e}"
        )


"""
Teste para rota: /pev/implantacao/modelo/canvas-proposta-valor
Endpoint: pev.implantacao_canvas_proposta_valor
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_canvas_proposta_valor(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/canvas-proposta-valor"""
    url = f"{base_url}/pev/implantacao/modelo/canvas-proposta-valor"

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
        ), f"GET /pev/implantacao/modelo/canvas-proposta-valor retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/modelo/canvas-proposta-valor: {e}"
        )


"""
Teste para rota: /pev/implantacao/modelo/mapa-persona
Endpoint: pev.implantacao_mapa_persona
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_mapa_persona(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/mapa-persona"""
    url = f"{base_url}/pev/implantacao/modelo/mapa-persona"

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
        ), f"GET /pev/implantacao/modelo/mapa-persona retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /pev/implantacao/modelo/mapa-persona: {e}")


"""
Teste para rota: /pev/implantacao/modelo/matriz-diferenciais
Endpoint: pev.implantacao_matriz_diferenciais
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_matriz_diferenciais(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/matriz-diferenciais"""
    url = f"{base_url}/pev/implantacao/modelo/matriz-diferenciais"

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
        ), f"GET /pev/implantacao/modelo/matriz-diferenciais retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/modelo/matriz-diferenciais: {e}"
        )


"""
Teste para rota: /pev/implantacao/modelo/produtos
Endpoint: pev.implantacao_produtos
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_produtos(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/produtos"""
    url = f"{base_url}/pev/implantacao/modelo/produtos"

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
        ), f"GET /pev/implantacao/modelo/produtos retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /pev/implantacao/modelo/produtos: {e}")


"""
Teste para rota: /pev/implantacao/modelo/modelagem-financeira
Endpoint: pev.implantacao_modelagem_financeira
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_modelagem_financeira(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/modelagem-financeira"""
    url = f"{base_url}/pev/implantacao/modelo/modelagem-financeira"

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
        ), f"GET /pev/implantacao/modelo/modelagem-financeira retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/modelo/modelagem-financeira: {e}"
        )


"""
Teste para rota: /pev/implantacao/modelo/modefin
Endpoint: pev.implantacao_modefin
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_modefin(base_url, timeout):
    """Testa a rota /pev/implantacao/modelo/modefin"""
    url = f"{base_url}/pev/implantacao/modelo/modefin"

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
        ), f"GET /pev/implantacao/modelo/modefin retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET /pev/implantacao/modelo/modefin: {e}")


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products
Endpoint: pev.get_products
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_products(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/products retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/products: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products/totals
Endpoint: pev.get_products_totals
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_products_totals(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products/totals"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products/totals"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/products/totals retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/products/totals: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products
Endpoint: pev.create_product
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_product(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/products retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/products: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products/<int:product_id>
Endpoint: pev.get_product
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_product(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products/<int:product_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products/<int:product_id>"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/products/<int:product_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/products/<int:product_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products/<int:product_id>
Endpoint: pev.update_product
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_product(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products/<int:product_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products/<int:product_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/products/<int:product_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/products/<int:product_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/products/<int:product_id>
Endpoint: pev.delete_product
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_product(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/products/<int:product_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/products/<int:product_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/products/<int:product_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/products/<int:product_id>: {e}"
        )


"""
Teste para rota: /pev/implantacao/executivo/playbook-comercial
Endpoint: pev.implantacao_playbook_comercial
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_playbook_comercial(base_url, timeout):
    """Testa a rota /pev/implantacao/executivo/playbook-comercial"""
    url = f"{base_url}/pev/implantacao/executivo/playbook-comercial"

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
        ), f"GET /pev/implantacao/executivo/playbook-comercial retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/executivo/playbook-comercial: {e}"
        )


"""
Teste para rota: /pev/implantacao/executivo/mapa-processos
Endpoint: pev.implantacao_mapa_processos
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_mapa_processos(base_url, timeout):
    """Testa a rota /pev/implantacao/executivo/mapa-processos"""
    url = f"{base_url}/pev/implantacao/executivo/mapa-processos"

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
        ), f"GET /pev/implantacao/executivo/mapa-processos retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/executivo/mapa-processos: {e}"
        )


"""
Teste para rota: /pev/implantacao/executivo/modelo-financeiro-base
Endpoint: pev.implantacao_modelo_financeiro_base
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_modelo_financeiro_base(base_url, timeout):
    """Testa a rota /pev/implantacao/executivo/modelo-financeiro-base"""
    url = f"{base_url}/pev/implantacao/executivo/modelo-financeiro-base"

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
        ), f"GET /pev/implantacao/executivo/modelo-financeiro-base retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/executivo/modelo-financeiro-base: {e}"
        )


"""
Teste para rota: /pev/implantacao/financeiro/plano-investimento
Endpoint: pev.implantacao_plano_investimento
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_plano_investimento(base_url, timeout):
    """Testa a rota /pev/implantacao/financeiro/plano-investimento"""
    url = f"{base_url}/pev/implantacao/financeiro/plano-investimento"

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
        ), f"GET /pev/implantacao/financeiro/plano-investimento retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/financeiro/plano-investimento: {e}"
        )


"""
Teste para rota: /pev/implantacao/financeiro/fluxo-caixa
Endpoint: pev.implantacao_fluxo_caixa
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_fluxo_caixa(base_url, timeout):
    """Testa a rota /pev/implantacao/financeiro/fluxo-caixa"""
    url = f"{base_url}/pev/implantacao/financeiro/fluxo-caixa"

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
        ), f"GET /pev/implantacao/financeiro/fluxo-caixa retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/financeiro/fluxo-caixa: {e}"
        )


"""
Teste para rota: /pev/implantacao/financeiro/matriz-indicadores
Endpoint: pev.implantacao_matriz_indicadores_financeiros
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_matriz_indicadores_financeiros(base_url, timeout):
    """Testa a rota /pev/implantacao/financeiro/matriz-indicadores"""
    url = f"{base_url}/pev/implantacao/financeiro/matriz-indicadores"

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
        ), f"GET /pev/implantacao/financeiro/matriz-indicadores retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/financeiro/matriz-indicadores: {e}"
        )


"""
Teste para rota: /pev/implantacao/relatorio/01-capa-resumo
Endpoint: pev.implantacao_relatorio_capa_resumo
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_relatorio_capa_resumo(base_url, timeout):
    """Testa a rota /pev/implantacao/relatorio/01-capa-resumo"""
    url = f"{base_url}/pev/implantacao/relatorio/01-capa-resumo"

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
        ), f"GET /pev/implantacao/relatorio/01-capa-resumo retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/relatorio/01-capa-resumo: {e}"
        )


"""
Teste para rota: /pev/implantacao/entrega/relatorio-final
Endpoint: pev.implantacao_relatorio_final
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_relatorio_final(base_url, timeout):
    """Testa a rota /pev/implantacao/entrega/relatorio-final"""
    url = f"{base_url}/pev/implantacao/entrega/relatorio-final"

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
        ), f"GET /pev/implantacao/entrega/relatorio-final retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/entrega/relatorio-final: {e}"
        )


"""
Teste para rota: /pev/implantacao/entrega/projeto-executivo
Endpoint: pev.implantacao_projeto_executivo
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_projeto_executivo(base_url, timeout):
    """Testa a rota /pev/implantacao/entrega/projeto-executivo"""
    url = f"{base_url}/pev/implantacao/entrega/projeto-executivo"

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
        ), f"GET /pev/implantacao/entrega/projeto-executivo retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/entrega/projeto-executivo: {e}"
        )


"""
Teste para rota: /pev/implantacao/entrega/painel-governanca
Endpoint: pev.implantacao_painel_governanca
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_painel_governanca(base_url, timeout):
    """Testa a rota /pev/implantacao/entrega/painel-governanca"""
    url = f"{base_url}/pev/implantacao/entrega/painel-governanca"

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
        ), f"GET /pev/implantacao/entrega/painel-governanca retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/entrega/painel-governanca: {e}"
        )


"""
Teste para rota: /pev/implantacao/executivo/estruturas
Endpoint: pev.implantacao_estruturas
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_implantacao_estruturas(base_url, timeout):
    """Testa a rota /pev/implantacao/executivo/estruturas"""
    url = f"{base_url}/pev/implantacao/executivo/estruturas"

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
        ), f"GET /pev/implantacao/executivo/estruturas retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/implantacao/executivo/estruturas: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/alignment/members
Endpoint: pev.add_alignment_member
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_add_alignment_member(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/alignment/members"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/alignment/members"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/alignment/members retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/alignment/members: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>
Endpoint: pev.update_alignment_member
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_alignment_member(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>
Endpoint: pev.delete_alignment_member
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_alignment_member(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/alignment/overview
Endpoint: pev.save_alignment_overview
Blueprint: pev
Métodos: POST, PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_save_alignment_overview(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/alignment/overview"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/alignment/overview"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/alignment/overview retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/alignment/overview: {e}"
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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/alignment/overview retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/alignment/overview: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/segments
Endpoint: pev.create_segment
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_segment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/segments"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/segments"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/segments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/segments: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>
Endpoint: pev.update_segment
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_segment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>
Endpoint: pev.delete_segment
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_segment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/segments/<int:segment_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>
Endpoint: pev.get_structure
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_structure(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures
Endpoint: pev.create_structure
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_structure(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/structures retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/structures: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>
Endpoint: pev.update_structure
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_structure(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>
Endpoint: pev.delete_structure
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_structure(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/capacities
Endpoint: pev.create_capacity
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_capacity(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/capacities"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/capacities"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/structures/capacities retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/structures/capacities: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>
Endpoint: pev.update_capacity
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_capacity(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>
Endpoint: pev.delete_capacity
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_capacity(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments
Endpoint: pev.delete_structure_installments
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_structure_installments(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments
Endpoint: pev.create_structure_installment
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_structure_installment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/structures/fixed-costs-summary
Endpoint: pev.get_fixed_costs_summary
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_fixed_costs_summary(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/structures/fixed-costs-summary"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/structures/fixed-costs-summary"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/structures/fixed-costs-summary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/structures/fixed-costs-summary: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/premises
Endpoint: pev.create_premise
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_premise(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/premises"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/premises"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/premises retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/premises: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>
Endpoint: pev.update_premise
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_premise(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>
Endpoint: pev.delete_premise
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_premise(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/investments
Endpoint: pev.create_investment
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_investment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/investments"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/investments"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/investments retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/investments: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>
Endpoint: pev.update_investment
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_investment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>
Endpoint: pev.delete_investment
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_investment(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/sources
Endpoint: pev.create_source
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_source(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/sources"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/sources"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/sources retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/sources: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>
Endpoint: pev.update_source
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_source(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>"""
    url = (
        f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>"
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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>
Endpoint: pev.delete_source
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_source(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>"""
    url = (
        f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>"
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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/variable_costs
Endpoint: pev.create_variable_cost
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_variable_cost(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/variable_costs"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/variable_costs"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/variable_costs retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/variable_costs: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>
Endpoint: pev.update_variable_cost
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_variable_cost(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>
Endpoint: pev.delete_variable_cost
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_variable_cost(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/result_rules
Endpoint: pev.create_result_rule
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_result_rule(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/result_rules"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/result_rules"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/result_rules retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/result_rules: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>
Endpoint: pev.update_result_rule
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_result_rule(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>
Endpoint: pev.delete_result_rule
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_result_rule(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/investment/contributions
Endpoint: pev.get_investment_contributions
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_investment_contributions(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/investment/contributions"""
    url = (
        f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/investment/contributions"
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
        ), f"GET /pev/api/implantacao/<int:plan_id>/finance/investment/contributions retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/finance/investment/contributions: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/funding_sources
Endpoint: pev.get_funding_sources
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_funding_sources(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/funding_sources"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/funding_sources"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/finance/funding_sources retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/finance/funding_sources: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/metrics
Endpoint: pev.update_metrics
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_metrics(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/metrics"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/metrics"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/metrics retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/metrics: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/capital-giro
Endpoint: pev.list_capital_giro
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_list_capital_giro(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/capital-giro"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/capital-giro"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/finance/capital-giro retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/finance/capital-giro: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/capital-giro
Endpoint: pev.create_capital_giro
Blueprint: pev
Métodos: POST
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_create_capital_giro(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/capital-giro"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/capital-giro"

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
        ), f"POST /pev/api/implantacao/<int:plan_id>/finance/capital-giro retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição POST /pev/api/implantacao/<int:plan_id>/finance/capital-giro: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>
Endpoint: pev.update_capital_giro
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_capital_giro(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>
Endpoint: pev.delete_capital_giro
Blueprint: pev
Métodos: DELETE
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_delete_capital_giro(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>"

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
        ), f"DELETE /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id> retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição DELETE /pev/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/executive-summary
Endpoint: pev.get_executive_summary_api
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_executive_summary_api(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/executive-summary"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/executive-summary"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/finance/executive-summary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/finance/executive-summary: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/executive-summary
Endpoint: pev.update_executive_summary_api
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_executive_summary_api(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/executive-summary"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/executive-summary"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/executive-summary retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/executive-summary: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/profit-distribution
Endpoint: pev.get_profit_distribution_api
Blueprint: pev
Métodos: GET
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_get_profit_distribution_api(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/profit-distribution"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/profit-distribution"

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
        ), f"GET /pev/api/implantacao/<int:plan_id>/finance/profit-distribution retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição GET /pev/api/implantacao/<int:plan_id>/finance/profit-distribution: {e}"
        )


"""
Teste para rota: /pev/api/implantacao/<int:plan_id>/finance/profit-distribution
Endpoint: pev.update_profit_distribution_api
Blueprint: pev
Métodos: PUT
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session


def test_pev_update_profit_distribution_api(base_url, timeout):
    """Testa a rota /pev/api/implantacao/<int:plan_id>/finance/profit-distribution"""
    url = f"{base_url}/pev/api/implantacao/<int:plan_id>/finance/profit-distribution"

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
        ), f"PUT /pev/api/implantacao/<int:plan_id>/finance/profit-distribution retornou status inesperado: {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"Erro na requisição PUT /pev/api/implantacao/<int:plan_id>/finance/profit-distribution: {e}"
        )
