from __future__ import annotations

from app32.tests.e2e.core.functional_guards import contains_public_error, is_html_success


def test_contains_public_error_detects_common_public_messages():
    assert contains_public_error("Erro interno do servidor. Tente novamente ou contate o suporte.")
    assert contains_public_error("Erro ao salvar")
    assert not contains_public_error("Operação concluída com sucesso.")


def test_contains_public_error_ignores_non_visible_script_text():
    html = """
    <main>Gestão de Reuniões</main>
    <script>console.error('Erro ao salvar reunião:', error)</script>
    """
    assert not contains_public_error(html)


def test_is_html_success_requires_markers_and_rejects_public_error():
    assert is_html_success("<div>API / MCP</div>", any_markers=("API / MCP",))
    assert not is_html_success("<div>Erro ao salvar</div>", any_markers=("Salvar",))
    assert not is_html_success("<div>Sem marcador</div>", all_markers=("marker-a",))
