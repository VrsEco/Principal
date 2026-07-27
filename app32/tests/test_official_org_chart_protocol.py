import ast
import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIGRATION_PATH = os.path.join(
    ROOT,
    "migrations",
    "versions",
    "20260727_2100_seed_official_org_chart_protocol.py",
)


def _source():
    with open(MIGRATION_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_org_chart_protocol_migration_is_valid_and_tenant_safe():
    source = _source()

    ast.parse(source)
    assert 'revision = "20260727_2100"' in source
    assert 'down_revision = "20260727_1800"' in source
    assert 'PROTOCOL_VERSION = "org-chart-official-v1.0"' in source
    assert "client_code = 'AA'" in source
    assert "company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)" in source
    assert "company_id=9" not in source.replace(" ", "")
    assert "consultive_assisted_analyses" not in source


def test_org_chart_protocol_has_complete_methodological_contract():
    source = _source()

    questions = [
        "Quais estratégia, processos e capacidades",
        "Quais papéis e cargos existem de fato",
        "Quais entregas, responsabilidades, decisões, alçadas",
        "Onde existem lacunas, sobreposições, conflitos",
        "Quais relações de reporte, níveis, amplitudes",
        "Quem responde por processos, indicadores, projetos e Squads",
        "Qual estrutura-alvo, capacidade, competência",
        "Como o Organograma se conecta ao MVV",
    ]
    for question in questions:
        assert question in source

    assert '"journey_version": "org-chart-maturity-v1.0"' in source
    assert '"distinguish_role_from_person": True' in source
    assert '"registered_chart_is_not_methodological_maturity": True' in source
    assert '"scenarios": ["current_operation", "planned_growth", "critical_role_absence"]' in source
    assert '"canonical_org_chart_mutation_via_client_cli": False' in source
    assert "não copie organogramas" in source


def test_org_chart_protocol_is_reflected_in_paper_spec_and_harness():
    paths = [
        os.path.join(
            ROOT,
            "docs",
            "papers",
            "paper_metodo_versus_estruturacao_evolutiva_v1.md",
        ),
        os.path.join(
            ROOT,
            "docs",
            "spec",
            "contrato_tecnico_analise_assistida_mcp_v1.md",
        ),
        os.path.join(
            ROOT,
            "docs",
            "harnesses",
            "squad_cliente",
            "harness_coordenador_cliente_v1.md",
        ),
    ]
    for path in paths:
        body = open(path, "r", encoding="utf-8").read()
        assert "org-chart-official-v1.0" in body
        assert "Organograma" in body

    spec = open(paths[1], "r", encoding="utf-8").read()
    assert "identity/org_chart" in spec
    assert "org-chart-maturity-v1.0" in spec
    assert "cargo, pessoa ocupante" in spec

    harness = open(paths[2], "r", encoding="utf-8").read()
    assert "estrutura formal de estrutura praticada" in harness
    assert "Não pode criar, alterar ou excluir cargos" in harness
