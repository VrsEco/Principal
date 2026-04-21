from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_financial_direct_keeps_brazilian_date_input_contract():
    for rel in ["static/js/financial_entry_direct.js", "app32/static/js/financial_entry_direct.js"]:
        source = read(rel)
        assert "return `${digits.slice(0, 2)}/${digits.slice(2)}`" in source
        assert "return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`" in source
        assert "return `${digits.slice(4)}-${digits.slice(2, 4)}-${digits.slice(0, 2)}`" in source
        assert "new Date().toLocaleDateString('pt-BR')" in source


def test_global_input_formatter_supports_rollout_formats():
    source = read("static/js/input_formatters.js")
    required_tokens = [
        "case 'currency'",
        "case 'percent'",
        "case 'hours-decimal'",
        "case 'duration-minutes'",
        "case 'score'",
        "case 'weight'",
        "parseClockToDecimalHours",
        "parseClockToMinutes",
        "window.FormData = class extends NativeFormData",
    ]
    for token in required_tokens:
        assert token in source


def test_representative_templates_use_global_data_format_contract():
    representative_templates = {
        "app32/templates/meetings_manage.html": ['data-format="duration-minutes"', "getMeetingDurationMinutes"],
        "app32/templates/modules/companies/company_form_v2.html": ['data-format="score"', "normalizeForSubmit"],
        "app32/templates/modules/financial/bank_reconciliation.html": ['data-format="currency"'],
        "app32/templates/modules/projects/project_manage.html": ['data-format="hours-decimal"', 'data-format="weight"'],
        "app32/templates/my_work.html": ['data-format="hours-decimal"'],
        "app32/templates/routine_details.html": ['data-format="weight"', 'data-format="hours-decimal"'],
    }
    for rel, tokens in representative_templates.items():
        source = read(rel)
        for token in tokens:
            assert token in source
