import ast
import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIGRATION_PATH = os.path.join(
    ROOT,
    "migrations",
    "versions",
    "20260727_1800_seed_official_positioning_protocol.py",
)


def _source():
    with open(MIGRATION_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_positioning_protocol_migration_is_valid_and_tenant_safe():
    source = _source()

    ast.parse(source)
    assert 'revision = "20260727_1800"' in source
    assert 'down_revision = "20260723_1000"' in source
    assert 'PROTOCOL_VERSION = "positioning-official-v1.0"' in source
    assert "client_code = 'AA'" in source
    assert "company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)" in source
    assert "company_id=9" not in source.replace(" ", "")
    assert "consultive_assisted_analyses" not in source


def test_positioning_protocol_has_complete_methodological_contract():
    source = _source()

    questions = [
        "Quem é o cliente prioritário, em qual situação de compra",
        "Qual problema relevante, necessidade ou trabalho a realizar",
        "Em qual categoria de referência a empresa deseja ser comparada",
        "Quais atributos são requisitos básicos da categoria",
        "Quais evidências, capacidades, processos, ofertas e experiências",
        "O que a empresa deliberadamente não pretende ser",
        "Como o Posicionamento se conecta à Missão, Visão, Valores, ICP",
    ]
    for question in questions:
        assert question in source

    assert '"journey_version": "positioning-maturity-v1.0"' in source
    assert '"declared_positioning_is_not_market_perception": True' in source
    assert '"final_identity_coherence_review_required": True' in source
    assert '"scenarios": ["favorable", "base", "adverse"]' in source
    assert "Não reduza Posicionamento a slogan" in source


def test_positioning_protocol_is_reflected_in_paper_spec_and_harness():
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
        assert "positioning-official-v1.0" in body
        assert "Posicionamento" in body

    spec = open(paths[1], "r", encoding="utf-8").read()
    assert "identity/positioning" in spec
    assert "positioning-maturity-v1.0" in spec
    assert "Análises de Missão, Visão ou Valores não podem avançar essa jornada" in spec

    harness = open(paths[2], "r", encoding="utf-8").read()
    assert "separar requisito básico de diferencial defensável" in harness
