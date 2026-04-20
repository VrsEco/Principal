from pathlib import Path


def test_bordero_rollout_contract_contains_required_guardrails():
    service = Path(r"C:\GestaoVersus\app32\app32\services\financial_bordero_service.py").read_text(encoding="utf-8")
    assert "financial_bordero_settlement_v2" in service
    assert "_sync_bordero_totals_from_items" in service
    assert "Somente Títulos Financeiros operacionais" in service
    assert "reconcile_via_bordero" in service
    assert "bordero_trace" in service


def test_bordero_rollout_ui_uses_canonical_title_language():
    template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\borderos.html").read_text(encoding="utf-8")
    frontend = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_borderos.js").read_text(encoding="utf-8")
    assert "Títulos Financeiros elegíveis" in template
    assert "títulos financeiros elegíveis" in frontend
    assert "Selecione ao menos um título financeiro." in frontend
