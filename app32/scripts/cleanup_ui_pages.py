#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Higieniza o catálogo de UI:
 - consolida registros duplicados por template
 - alinha page_route/template_file com as rotas reais detectadas
"""

import argparse
import ast
import inspect
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app_pev import app  # noqa: E402
from database.postgres_helper import connect  # noqa: E402


def normalize_template_name(template: Optional[str]) -> str:
    """Normaliza caminho de template (sem templates/, lowercase)."""
    if not template:
        return ""

    normalized = str(template).replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("templates/"):
        normalized = normalized[len("templates/") :]
    if normalized.startswith("/"):
        normalized = normalized[1:]

    return normalized.lower()


def build_filesystem_index() -> Dict[str, str]:
    """Mapeia templates existentes no disco."""
    templates_dir = BASE_DIR / "templates"
    index: Dict[str, str] = {}

    for path in templates_dir.rglob("*.html"):
        rel_path = path.relative_to(templates_dir)
        key = normalize_template_name(str(rel_path))
        index[key] = str(rel_path).replace("\\", "/")

    return index


class TemplateVisitor(ast.NodeVisitor):
    """Encontra strings passadas para render_template."""

    def __init__(self) -> None:
        self.templates: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        is_render_call = False

        if isinstance(func, ast.Name) and func.id == "render_template":
            is_render_call = True
        elif isinstance(func, ast.Attribute) and func.attr == "render_template":
            is_render_call = True

        if is_render_call and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self.templates.add(arg.value.strip())

        self.generic_visit(node)


def extract_templates_from_func(view_func) -> Set[str]:
    """Retorna templates literais usados em um view."""
    try:
        source = inspect.getsource(view_func)
        source = textwrap.dedent(source)
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return set()

    visitor = TemplateVisitor()
    visitor.visit(tree)
    return visitor.templates


def collect_template_routes() -> Dict[str, Dict[str, Set[str]]]:
    """Relaciona templates às rotas reais registradas no Flask."""
    mapping: Dict[str, Dict[str, Set[str]]] = {}

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        view_func = app.view_functions.get(rule.endpoint)
        if not view_func:
            continue

        for template in extract_templates_from_func(view_func):
            key = normalize_template_name(template)
            if not key:
                continue

            entry = mapping.setdefault(
                key,
                {
                    "template": template,
                    "routes": set(),
                },
            )
            entry["routes"].add(rule.rule)

    return mapping


def load_ui_pages() -> List[Dict]:
    """Carrega dados atuais de ui_pages."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, page_code, page_name, page_route, module, template_file
        FROM ui_pages
        ORDER BY id
        """
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    page_list: List[Dict] = []
    for row in rows:
        data = {key: row[key] for key in row.keys()}
        data["normalized_template"] = normalize_template_name(data.get("template_file"))
        page_list.append(data)

    return page_list


def choose_canonical(records: List[Dict]) -> Dict:
    """Escolhe qual registro manter em caso de duplicatas."""
    return sorted(
        records,
        key=lambda r: (
            0 if r.get("page_route") else 1,
            r["id"],
        ),
    )[0]


def plan_cleanup(
    pages: List[Dict],
    template_routes: Dict[str, Dict[str, Set[str]]],
    fs_index: Dict[str, str],
) -> Tuple[List[Dict], Dict[str, int]]:
    """Calcula quais ações serão necessárias."""
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for page in pages:
        key = page.get("normalized_template") or ""
        if not key:
            continue
        grouped[key].append(page)

    actions: List[Dict] = []
    summary = {
        "templates_indexados": len(grouped),
        "templates_com_duplicatas": 0,
        "acoes_update": 0,
        "acoes_merge": 0,
    }

    for template_key, records in sorted(grouped.items()):
        canonical = choose_canonical(records)
        duplicates = [r for r in records if r["id"] != canonical["id"]]

        if duplicates:
            summary["templates_com_duplicatas"] += 1

        # Descobrir template/rota alvo
        template_meta = template_routes.get(template_key)
        target_template = (
            template_meta.get("template")
            if template_meta
            else fs_index.get(template_key, canonical.get("template_file"))
        )
        target_route = None
        if template_meta and template_meta["routes"]:
            target_route = sorted(template_meta["routes"], key=len)[0]

        updates = {}
        if target_template and canonical.get("template_file") != target_template:
            updates["template_file"] = target_template

        if target_route and canonical.get("page_route") != target_route:
            updates["page_route"] = target_route

        if updates:
            actions.append(
                {
                    "type": "update",
                    "page_id": canonical["id"],
                    "page_code": canonical["page_code"],
                    "fields": updates,
                    "template_key": template_key,
                }
            )
            summary["acoes_update"] += 1

        for duplicate in duplicates:
            actions.append(
                {
                    "type": "merge",
                    "source_id": duplicate["id"],
                    "source_code": duplicate["page_code"],
                    "target_id": canonical["id"],
                    "target_code": canonical["page_code"],
                    "template_key": template_key,
                }
            )
            summary["acoes_merge"] += 1

    return actions, summary


def apply_actions(actions: List[Dict], dry_run: bool = True) -> None:
    """Executa (ou apenas simula) as operações planejadas."""
    if not actions:
        print("Nenhuma ação necessária.")
        return

    if dry_run:
        print("\n[DRY RUN] Nenhuma alteração foi gravada. Use --apply para persistir.")
        return

    conn = connect()
    cursor = conn.cursor()

    try:
        for action in actions:
            if action["type"] == "update":
                fields = action["fields"]
                assignments = ", ".join(f"{k} = %s" for k in fields.keys())
                params = list(fields.values()) + [action["page_id"]]
                cursor.execute(
                    f"UPDATE ui_pages SET {assignments} WHERE id = %s",
                    params,
                )
            elif action["type"] == "merge":
                cursor.execute(
                    "DELETE FROM ui_pages WHERE id = %s",
                    (action["source_id"],),
                )

        conn.commit()
        print(f"[OK] {len(actions)} operações aplicadas.")
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Falha ao aplicar alterações: {exc}") from exc
    finally:
        cursor.close()
        conn.close()


def describe_action(action: Dict) -> str:
    """Retorna string resumindo a ação."""
    if action["type"] == "update":
        fields = ", ".join(f"{k}={v}" for k, v in action["fields"].items())
        return (
            f"[UPDATE] page_code={action['page_code']} "
            f"({action['template_key']}): {fields}"
        )

    return (
        f"[MERGE] Remover {action['source_code']} (dup) mantendo {action['target_code']} "
        f"({action['template_key']})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deduplica ui_pages e sincroniza rotas/template."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as alterações no banco (padrão: dry-run).",
    )
    args = parser.parse_args()

    print("Gerando índices...")
    template_routes = collect_template_routes()
    fs_index = build_filesystem_index()
    pages = load_ui_pages()

    actions, summary = plan_cleanup(pages, template_routes, fs_index)

    print(
        f"Templates indexados: {summary['templates_indexados']} "
        f"(duplicatas: {summary['templates_com_duplicatas']})"
    )
    print(
        f"Ações planejadas: updates={summary['acoes_update']}, "
        f"merges={summary['acoes_merge']}"
    )

    for action in actions:
        print(describe_action(action))

    apply_actions(actions, dry_run=not args.apply)


if __name__ == "__main__":
    main()
