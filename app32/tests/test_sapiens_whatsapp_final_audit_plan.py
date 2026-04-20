from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DOC = ROOT / "docs" / "audits" / "sapiens_whatsapp_company_flow_entrypoints.md"
FINAL_PLAN = ROOT / "docs" / "audits" / "sapiens_whatsapp_company_flow_final_plan.md"


def test_final_audit_doc_consolidates_gaps_and_minimum_plan():
    doc = AUDIT_DOC.read_text(encoding="utf-8")

    assert "Passo 4/4 — Lacunas consolidadas e proposta mínima" in doc
    assert "Usuário com múltiplas empresas ativas" in doc
    assert "Persistir seleção temporária" in doc
    assert "Nenhum fallback global para empresa ativa do banco" in doc
    assert "Próxima frente recomendada" in doc


def test_final_plan_keeps_tenant_safe_execution_flow():
    plan = FINAL_PLAN.read_text(encoding="utf-8")

    required = [
        "company_id` é obrigatório",
        "não há fallback para primeira empresa ativa",
        "Solicitar seleção explícita",
        "Persistir contexto por thread",
        "Company.query",
    ]
    for item in required:
        assert item in plan


def test_final_plan_references_regression_contracts():
    plan = FINAL_PLAN.read_text(encoding="utf-8")

    assert "Testes de contrato devem falhar" in plan
    assert "Testes de entrypoint" in plan
    assert "Testes de identidade" in plan
