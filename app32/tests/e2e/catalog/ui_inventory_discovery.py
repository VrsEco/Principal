from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback para runtime enxuto
    yaml = None

from app32.tests.e2e.catalog.drift_detector import normalize_route
from app32.tests.e2e.catalog.inventory import iter_inventory_items


MUTATION_HINTS = (
    "add",
    "adicionar",
    "alterar",
    "aprovar",
    "baixar",
    "cancel",
    "cancelar",
    "create",
    "criar",
    "delete",
    "editar",
    "excluir",
    "finalizar",
    "gerar",
    "importar",
    "inativar",
    "processar",
    "remove",
    "remover",
    "salvar",
    "save",
    "submit",
)
CONFIRMATION_HINTS = ("delete", "excluir", "remove", "remover", "cancel", "cancelar", "inativar", "aprovar")


@dataclass(frozen=True)
class UIElementCandidate:
    screen_id: str
    template: str
    route: str | None
    element_type: str
    selector: str
    label: str | None
    action_kind: str
    requires_data: bool
    requires_confirmation: bool
    requires_cleanup: bool
    contract_status: str


@dataclass(frozen=True)
class UIScreenCandidate:
    screen_id: str
    template: str
    routes: list[str]
    is_partial: bool
    fields_total: int
    buttons_total: int
    links_total: int
    forms_total: int
    elements_total: int
    contract_status: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def templates_root() -> Path:
    return repo_root() / "app32" / "templates"


def _screen_id(template: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", template.replace(".html", "")).strip("_").lower()
    return normalized or "template"


def _selector(tag: str, attrs: dict[str, str]) -> str:
    if attrs.get("data-testid"):
        return f"[data-testid='{attrs['data-testid']}']"
    if attrs.get("id"):
        return f"#{attrs['id']}"
    if attrs.get("name"):
        return f"{tag}[name='{attrs['name']}']"
    if attrs.get("href") and tag == "a":
        return f"a[href='{attrs['href']}']"
    if attrs.get("type"):
        return f"{tag}[type='{attrs['type']}']"
    return tag


def _label(attrs: dict[str, str]) -> str | None:
    for key in ("aria-label", "title", "placeholder", "name", "id", "value", "data-action"):
        value = str(attrs.get(key) or "").strip()
        if value:
            return value[:180]
    return None


def _action_kind(tag: str, attrs: dict[str, str]) -> str:
    input_type = str(attrs.get("type") or "").lower()
    if tag in {"input", "textarea"}:
        if input_type in {"checkbox", "radio"}:
            return "toggle"
        if input_type in {"submit", "button"}:
            return "click"
        return "fill"
    if tag == "select":
        return "select"
    if tag == "form":
        return "submit"
    if tag == "a":
        return "navigate"
    return "click"


def _element_type(tag: str, attrs: dict[str, str]) -> str:
    if tag == "input":
        return f"input:{str(attrs.get('type') or 'text').lower()}"
    if tag in {"textarea", "select", "button", "form", "a"}:
        return tag
    if str(attrs.get("role") or "").lower() == "button":
        return "button"
    if attrs.get("data-action") or attrs.get("onclick"):
        return "action"
    return tag


def _looks_actionable(tag: str, attrs: dict[str, str]) -> bool:
    if tag in {"input", "textarea", "select", "button", "form"}:
        return True
    if tag == "a" and attrs.get("href"):
        return True
    if str(attrs.get("role") or "").lower() == "button":
        return True
    return bool(attrs.get("data-action") or attrs.get("onclick"))


def _requires_data(tag: str, attrs: dict[str, str]) -> bool:
    input_type = str(attrs.get("type") or "").lower()
    if tag in {"textarea", "select"}:
        return True
    return tag == "input" and input_type not in {"button", "submit", "reset", "hidden", "checkbox", "radio"}


def _contains_hint(attrs: dict[str, str], hints: tuple[str, ...]) -> bool:
    haystack = " ".join(str(value or "").lower() for value in attrs.values())
    return any(hint in haystack for hint in hints)


class _TemplateElementParser(HTMLParser):
    def __init__(self, *, template: str, routes: list[str], contracted_routes: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.template = template
        self.routes = routes
        self.contracted_routes = contracted_routes
        self.elements: list[UIElementCandidate] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        if not _looks_actionable(tag, attrs):
            return
        selector = _selector(tag, attrs)
        route = self.routes[0] if self.routes else None
        contract_status = "contracted" if route and route in self.contracted_routes else "discovered"
        self.elements.append(
            UIElementCandidate(
                screen_id=_screen_id(self.template),
                template=self.template,
                route=route,
                element_type=_element_type(tag, attrs),
                selector=selector,
                label=_label(attrs),
                action_kind=_action_kind(tag, attrs),
                requires_data=_requires_data(tag, attrs),
                requires_confirmation=_contains_hint(attrs, CONFIRMATION_HINTS),
                requires_cleanup=_contains_hint(attrs, MUTATION_HINTS),
                contract_status=contract_status,
            )
        )


def _iter_python_sources() -> list[Path]:
    app_root = repo_root() / "app32"
    ignored = {"archive", "docs", "tests", "__pycache__", ".agent"}
    return [
        path
        for path in app_root.rglob("*.py")
        if not any(part in ignored for part in path.parts) and not path.name.startswith(".codex_temp")
    ]


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _blueprint_prefixes(tree: ast.AST) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if not isinstance(func, ast.Name) or func.id != "Blueprint":
            continue
        prefix = ""
        for kw in node.value.keywords:
            if kw.arg == "url_prefix":
                prefix = _literal_string(kw.value) or ""
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    return prefixes


def _decorator_route(decorator: ast.AST, prefixes: dict[str, str]) -> str | None:
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if not isinstance(func, ast.Attribute) or func.attr != "route":
        return None
    if not decorator.args:
        return None
    route = _literal_string(decorator.args[0])
    if not route:
        return None
    prefix = ""
    if isinstance(func.value, ast.Name):
        prefix = prefixes.get(func.value.id, "")
    return normalize_route(f"{prefix.rstrip('/')}/{route.lstrip('/')}" if prefix else route)


def _rendered_templates(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    templates: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "render_template" and node.args:
            template = _literal_string(node.args[0])
            if template:
                templates.append(template)
    return templates


def discover_template_routes() -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = {}
    for path in _iter_python_sources():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        prefixes = _blueprint_prefixes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            routes = [route for deco in node.decorator_list if (route := _decorator_route(deco, prefixes))]
            if not routes:
                continue
            for template in _rendered_templates(node):
                mapping.setdefault(template, set()).update(routes)
    return {template: sorted(routes) for template, routes in mapping.items()}


def _is_partial_template(template: str, routes: list[str]) -> bool:
    parts = set(Path(template).parts)
    filename = Path(template).name
    return not routes or "components" in parts or "partials" in parts or filename.startswith("_")


def _scan_template(path: Path, *, template: str, routes: list[str], contracted_routes: set[str]) -> list[UIElementCandidate]:
    parser = _TemplateElementParser(template=template, routes=routes, contracted_routes=contracted_routes)
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser.elements


def discover_ui_inventory() -> dict[str, Any]:
    root = templates_root()
    route_map = discover_template_routes()
    contracted_routes = {normalize_route(item["route"]) for item in iter_inventory_items() if item.get("route")}

    screens: list[UIScreenCandidate] = []
    elements: list[UIElementCandidate] = []
    for path in sorted(root.rglob("*.html")):
        template = path.relative_to(root).as_posix()
        routes = [normalize_route(route) for route in route_map.get(template, [])]
        template_elements = _scan_template(path, template=template, routes=routes, contracted_routes=contracted_routes)
        elements.extend(template_elements)
        screen_contract = "contracted" if routes and any(route in contracted_routes for route in routes) else "discovered"
        screens.append(
            UIScreenCandidate(
                screen_id=_screen_id(template),
                template=template,
                routes=routes,
                is_partial=_is_partial_template(template, routes),
                fields_total=sum(1 for item in template_elements if item.action_kind in {"fill", "select", "toggle"}),
                buttons_total=sum(1 for item in template_elements if item.action_kind in {"click", "submit"}),
                links_total=sum(1 for item in template_elements if item.action_kind == "navigate"),
                forms_total=sum(1 for item in template_elements if item.element_type == "form"),
                elements_total=len(template_elements),
                contract_status=screen_contract,
            )
        )

    missing_contract_screens = [item for item in screens if not item.is_partial and item.contract_status == "discovered"]
    missing_contract_elements = [item for item in elements if item.contract_status == "discovered"]
    return {
        "generated_at": datetime.now().isoformat(),
        "screens_total": len(screens),
        "routable_screens_total": sum(1 for item in screens if item.routes),
        "partial_templates_total": sum(1 for item in screens if item.is_partial),
        "elements_total": len(elements),
        "fields_total": sum(1 for item in elements if item.action_kind in {"fill", "select", "toggle"}),
        "buttons_total": sum(1 for item in elements if item.action_kind in {"click", "submit"}),
        "links_total": sum(1 for item in elements if item.action_kind == "navigate"),
        "mutation_candidates_total": sum(1 for item in elements if item.requires_cleanup),
        "missing_contract_screens_total": len(missing_contract_screens),
        "missing_contract_elements_total": len(missing_contract_elements),
        "screens": [asdict(item) for item in screens],
        "elements": [asdict(item) for item in elements],
        "missing_contract_screens": [asdict(item) for item in missing_contract_screens[:200]],
        "missing_contract_elements": [asdict(item) for item in missing_contract_elements[:500]],
    }


def write_ui_inventory_report(base_dir: Path) -> Path:
    report = discover_ui_inventory()
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = base_dir / "ui_inventory_scan" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "ui_inventory.json"
    yaml_path = target_dir / "ui_inventory.yaml"
    summary_path = target_dir / "summary.json"
    manifest_path = target_dir / "manifest.json"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if yaml is not None:
        yaml_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        yaml_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "generated_at": report["generated_at"],
        "screens_total": report["screens_total"],
        "routable_screens_total": report["routable_screens_total"],
        "elements_total": report["elements_total"],
        "fields_total": report["fields_total"],
        "buttons_total": report["buttons_total"],
        "links_total": report["links_total"],
        "mutation_candidates_total": report["mutation_candidates_total"],
        "missing_contract_screens_total": report["missing_contract_screens_total"],
        "missing_contract_elements_total": report["missing_contract_elements_total"],
        "json_path": str(json_path),
        "yaml_path": str(yaml_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "environment": "DEV_FULL",
                "generated_at": report["generated_at"],
                "suite_id": "ui_inventory_contract_scan",
                "journeys": [
                    {
                        "journey": "governance::ui_inventory_contract_scan",
                        "suite_id": "ui_inventory_contract_scan",
                        "domain": "governance",
                        "status": "passed",
                        "failed_step": None,
                        "failure_type": None,
                    }
                ],
                "events": [{"event": "ui_inventory_scan_completed", **summary}],
                "artifacts": [{"kind": "ui_inventory", "path": "ui_inventory.json"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path
