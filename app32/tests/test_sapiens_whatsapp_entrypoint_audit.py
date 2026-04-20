import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBHOOK_FILE = ROOT / "api" / "webhooks" / "whatsapp_webhook.py"
APP_FILE = ROOT / "app.py"
AUDIT_DOC = ROOT / "docs" / "audits" / "sapiens_whatsapp_company_flow_entrypoints.md"


def _module_tree(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _function_names(tree):
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def test_whatsapp_blueprint_is_registered_under_webhook_prefix():
    source = APP_FILE.read_text(encoding="utf-8")

    assert "from api.webhooks.whatsapp_webhook import whatsapp_webhook_bp" in source
    assert "app.register_blueprint(whatsapp_webhook_bp, url_prefix='/webhook')" in source
    assert "request.path.startswith('/webhook/')" in source


def test_whatsapp_and_instagram_entrypoints_exist_in_same_blueprint():
    source = WEBHOOK_FILE.read_text(encoding="utf-8")
    tree = _module_tree(WEBHOOK_FILE)
    names = _function_names(tree)

    assert "whatsapp_webhook_bp = Blueprint('whatsapp_webhook', __name__)" in source
    assert "@whatsapp_webhook_bp.route('/whatsapp', methods=['POST'])" in source
    assert "@whatsapp_webhook_bp.route('/instagram', methods=['POST'])" in source
    assert {"handle_whatsapp", "handle_instagram", "process_whatsapp_message"}.issubset(names)


def test_whatsapp_orchestration_calls_identity_company_menu_and_agent_layers():
    source = WEBHOOK_FILE.read_text(encoding="utf-8")

    assert (
        "resolve_user_identity(phone, \"whatsapp\")" in source
        or "resolve_user_identity(phone, 'whatsapp')" in source
    )

    required_calls = [
        "get_best_company_id(user)",
        "handle_menu_message(",
        "run_agent_with_context(",
        "company_id=company_id",
        "thread_id=thread_id",
    ]
    for call in required_calls:
        assert call in source

    assert "channel=\"whatsapp\"" in source or "channel='whatsapp'" in source
    assert "Company.query.first()" not in source


def test_entrypoint_audit_document_is_kept_with_required_sections():
    doc = AUDIT_DOC.read_text(encoding="utf-8")

    for section in [
        "Entry points HTTP",
        "Registro Flask",
        "Arquivo central de orquestração do webhook",
        "Dependências críticas mapeadas",
        "Ordem operacional atual",
        "Guardrails confirmados",
    ]:
        assert section in doc

    assert "/webhook/whatsapp" in doc
    assert "resolve_user_identity" in doc
    assert "get_best_company_id" in doc
