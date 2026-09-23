import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "screen_inventory", Path(__file__).resolve().parents[1] / "scripts/qa/build_screen_performance_inventory.py"
)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_routes_dynamic_templates_and_api_registration(tmp_path):
    root = tmp_path / "app32"
    write(root, "app.py", "app.register_blueprint(bp, url_prefix='/override')\napi.add_resource(Resource, '/api/items')")
    write(root, "api/routes/example.py", """
bp = Blueprint('x', __name__, url_prefix='/base')
@bp.route('/one', methods=['GET', 'POST'])
def one():
    return render_template('page.html')
@bp.get('/two')
def two():
    return render_template(template_name)
""")
    result = inventory.build(root)
    assert result["summary"]["route_declarations"] == 2
    assert result["summary"]["dynamic_template_handlers"] == 1
    assert result["routes"][0]["candidate_rule"] == "/base/one"
    assert result["blueprint_registrations"][0]["override_prefix"] == "/override"
    assert not result["routes"][0]["runtime_verified"]
    assert result["resource_registrations"][0]["rules"] == ["/api/items"]


def test_template_inheritance_cycle_css_and_assets(tmp_path):
    root = tmp_path / "app32"
    write(root, "templates/base.html", "<head><link rel='stylesheet' href='/static/css/base.css'></head>{% include 'page.html' %}")
    write(root, "templates/page.html", """{% extends 'base.html' %}
{% block workspace_content %}<link rel='stylesheet' href='/static/css/page.css'>
<script src="{{ url_for('static', filename='js/page.js') }}"></script>{% endblock %}""")
    rows, _ = inventory.template_inventory(root)
    assert rows["base.html"]["css_in_content_candidates"] == []
    assert rows["page.html"]["css_in_content_candidates"] == [2]
    assert rows["page.html"]["possible_assets_with_inheritance"] == ["css/base.css", "css/page.css", "js/page.js"]


def test_parse_errors_are_visible_and_no_app_import(tmp_path):
    root = tmp_path / "app32"
    write(root, "app.py", "raise RuntimeError('MUST NOT EXECUTE')")
    write(root, "api/routes/bad.py", "def broken(:")
    result = inventory.build(root)
    assert result["summary"]["python_parse_errors"] == 1
    assert result["parse_errors"][0]["file"] == "api/routes/bad.py"


def test_public_asset_drift_and_determinism(tmp_path):
    root = tmp_path / "app32"
    write(root, "static/js/a.js", "fetch('/api/a');\nlocation.reload();")
    write(tmp_path, "static/js/a.js", "old")
    first = inventory.build(root)
    assert first == inventory.build(root)
    assert first["scripts"][0]["local_public_copy_differs"]
    assert first["scripts"][0]["signals"]["fetch"] == [1]
    assert first["scripts"][0]["signals"]["full_reload"] == [2]


def test_imported_blueprint_prefix(tmp_path):
    root = tmp_path / "app32"
    write(root, "api/routes/base.py", "financial_bp = Blueprint('finance', __name__, url_prefix='/financial')")
    write(root, "api/routes/reports.py", "from .base import financial_bp\n@financial_bp.get('/reports/<slug>')\ndef report(slug):\n return render_template('reports.html')")
    result = inventory.build(root)
    assert result["routes"][0]["candidate_rule"] == "/financial/reports/<slug>"
