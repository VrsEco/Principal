from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FILE = ROOT / "src" / "intelligence" / "identity.py"
AUDIT_DOC = ROOT / "docs" / "audits" / "sapiens_whatsapp_company_flow_entrypoints.md"


def test_company_resolution_contract_has_trace_and_employee_only_scope():
    source = IDENTITY_FILE.read_text(encoding="utf-8")

    assert "class CompanyResolutionTrace" in source
    assert "def get_company_resolution_with_trace" in source
    assert 'Employee.query.filter_by(user_id=user_id, status="active")' in source
    assert "Employee.query.filter_by(user_id=user_id)" in source
    assert "SAPIENS COMPANY RESOLUTION TRACE" in source


def test_company_resolution_does_not_fallback_to_global_company():
    source = IDENTITY_FILE.read_text(encoding="utf-8")

    assert "from models.company import Company" not in source
    assert "Company.query" not in source
    assert "first_company" not in source
    assert "admin_without_employee_link" in source


def test_company_resolution_audit_doc_records_tenant_safe_policy():
    doc = AUDIT_DOC.read_text(encoding="utf-8")

    assert "Passo 3/4 — Resolução de empresas vinculadas" in doc
    assert "exclusivamente dos vínculos do usuário em `Employee`" in doc
    assert "Admin sem vínculo explícito não recebe fallback" in doc
    assert "CompanyResolutionTrace" in doc
