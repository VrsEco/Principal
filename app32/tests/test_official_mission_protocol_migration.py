import ast
import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIGRATION_PATH = os.path.join(
    ROOT,
    "migrations",
    "versions",
    "20260721_0900_seed_official_mission_protocol.py",
)


def _migration_source():
    with open(MIGRATION_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_official_mission_protocol_migration_is_valid_and_tenant_safe():
    source = _migration_source()

    ast.parse(source)
    assert 'revision = "20260721_0900"' in source
    assert 'down_revision = "20260720_0900"' in source
    assert 'PROTOCOL_VERSION = "mission-official-v1.0"' in source
    assert "client_code = 'AA'" in source
    assert "company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)" in source
    assert "seed:mission-official-v1.0:global" in source
    assert "seed:mission-official-v1.0:tenant-aa" in source
    assert "company_id=9" not in source.replace(" ", "")
    assert "consultive_assisted_analyses" not in source


def test_official_mission_protocol_contains_methodological_contract():
    source = _migration_source()

    required_questions = [
        "O que a empresa entrega que não deveria deixar de existir?",
        "Quem é o cliente contratante prioritário e quais stakeholders são beneficiados?",
        "Qual transformação concreta o cliente percebe?",
        "Qual problema empresarial central a empresa existe para resolver?",
        "Quais processos, capacidades, pessoas e recursos provam que a promessa é entregável?",
        "O que a empresa não pretende ser ou executar pelo cliente?",
        "A missão atual representa a entrega real de hoje ou uma intenção futura?",
        "Quais evidências internas e externas sustentam cada afirmação?",
    ]
    for question in required_questions:
        assert question in source

    assert '"journey_ref": "structuring-journey-v2.1"' in source
    assert '"journey_version": "mission-maturity-v1.2"' in source
    assert '"analysis_type": "methodological"' in source
    assert '"canonical_write_allowed_before_consultant_decision": False' in source
    assert '"requires_explicit_human_confirmation": True' in source
    assert "pesquisa profunda e vasta" in source
    assert "fontes primárias" in source
    assert "Simule a aderência" in source
    assert '"client", "versus", "engineering_when_required", "consultant"' in source


def test_canonical_documents_and_client_harness_reference_official_protocol():
    paths = [
        os.path.join(ROOT, "docs", "papers", "paper_metodo_versus_estruturacao_evolutiva_v1.md"),
        os.path.join(ROOT, "docs", "spec", "contrato_tecnico_analise_assistida_mcp_v1.md"),
        os.path.join(ROOT, "docs", "harnesses", "squad_cliente", "harness_coordenador_cliente_v1.md"),
    ]

    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            body = handle.read()
        assert "mission-official-v1.0" in body

    with open(paths[1], "r", encoding="utf-8") as handle:
        spec = handle.read()
    assert "snapshot gravado em cada análise é imutável" in spec

    with open(paths[2], "r", encoding="utf-8") as handle:
        harness = handle.read()
    assert "`id` não nulo" in harness
    assert "Se a resolução retornar `fallback`" in harness
