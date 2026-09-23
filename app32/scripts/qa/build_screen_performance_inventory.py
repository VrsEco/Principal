"""Read-only static inventory; never imports Flask or executes application code.

Counts declarations, not live URLs or validated performance defects. Dynamic
routes/templates and inherited assets remain explicit coverage limitations.
"""
import argparse
import ast
import csv
import hashlib
import json
import re
from pathlib import Path


def literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return default


def name(node):
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""


def line_at(text, offset):
    return text.count("\n", 0, offset) + 1


def signals(text):
    patterns = {
        "fetch": r"\bfetch\s*\(", "await": r"\bawait\b",
        "promise_all": r"Promise\.all\s*\(",
        "abort_controller": r"\bAbortController\b",
        "interval": r"\bsetInterval\s*\(",
        "full_reload": r"\blocation\.reload\s*\(",
        "dom_ready": r"DOMContentLoaded",
        "mutation_observer": r"\bMutationObserver\b",
    }
    return {key: [line_at(text, m.start()) for m in re.finditer(pattern, text)]
            for key, pattern in patterns.items()}


def python_inventory(root):
    sources = [root / "app.py"]
    sources += [p for sub in ("api", "src") for p in (root / sub).rglob("*.py")]
    routes, resources, errors, registrations, hashes = [], [], [], [], {}
    definitions, imported = {}, {}
    for path in sorted(set(sources)):
        if not path.exists():
            continue
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        hashes[rel] = hashlib.sha256(raw).hexdigest()
        try:
            tree = ast.parse(raw.decode("utf-8-sig"))
        except (SyntaxError, UnicodeError) as exc:
            errors.append({"file": rel, "error": str(exc)})
            continue
        prefixes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = list(Path(rel).parent.parts)
                    for _ in range(node.level - 1):
                        if parts:
                            parts.pop()
                    parts += (node.module or "").split(".") if node.module else []
                else:
                    parts = (node.module or "").split(".")
                target_file = "/".join(parts) + ".py"
                for alias in node.names:
                    imported[(rel, alias.asname or alias.name)] = (target_file, alias.name)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and name(node.value.func) == "Blueprint":
                prefix = next((literal(k.value) for k in node.value.keywords if k.arg == "url_prefix"), "")
                for target in node.targets:
                    prefixes[name(target)] = prefix
                    definitions[(rel, name(target))] = prefix
            if isinstance(node, ast.Call) and name(node.func) == "register_blueprint":
                registrations.append({"file": rel, "line": node.lineno,
                                      "blueprint": name(node.args[0]) if node.args else "dynamic",
                                      "override_prefix": next((literal(k.value) for k in node.keywords if k.arg == "url_prefix"), None)})
            if isinstance(node, ast.Call) and name(node.func) in ("add_resource", "add_url_rule"):
                values = [literal(a) for a in node.args]
                resources.append({"file": rel, "line": node.lineno, "kind": name(node.func),
                                  "rules": [v for v in values if isinstance(v, str) and v.startswith("/")]})
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            templates, dynamic = [], False
            for call in ast.walk(fn):
                if isinstance(call, ast.Call) and name(call.func) == "render_template":
                    val = literal(call.args[0]) if call.args else None
                    if isinstance(val, str):
                        templates.append(val)
                    else:
                        dynamic = True
            for dec in fn.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or dec.func.attr not in ("route", "get", "post", "put", "delete", "patch"):
                    continue
                rule = literal(dec.args[0]) if dec.args else None
                methods = next((literal(k.value) for k in dec.keywords if k.arg == "methods"), None)
                if methods is None:
                    methods = ["GET"] if dec.func.attr == "route" else [dec.func.attr.upper()]
                receiver = name(dec.func.value)
                prefix = prefixes.get(receiver, "" if receiver == "app" else None)
                resolved = prefix + rule if isinstance(prefix, str) and isinstance(rule, str) else None
                routes.append({"file": rel, "line": dec.lineno, "handler": fn.name,
                               "blueprint_variable": receiver, "declared_rule": rule,
                               "candidate_rule": resolved, "methods": methods,
                               "templates": sorted(set(templates)), "dynamic_template": dynamic,
                               "runtime_verified": False})
    def resolve(key, seen):
        if key in seen:
            return None
        if key in definitions:
            return definitions[key]
        return resolve(imported[key], seen | {key}) if key in imported else None

    for row in routes:
        if row["candidate_rule"] is None and isinstance(row["declared_rule"], str):
            prefix = resolve((row["file"], row["blueprint_variable"]), set())
            if isinstance(prefix, str):
                row["candidate_rule"] = prefix + row["declared_rule"]
    return routes, resources, registrations, errors, hashes


def template_inventory(root):
    rows, hashes = {}, {}
    for path in sorted((root / "templates").rglob("*.html")):
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        rel = path.relative_to(root / "templates").as_posix()
        hashes["templates/" + rel] = hashlib.sha256(raw).hexdigest()
        links = re.findall(r"{%\s*(?:extends|include|import)\s+['\"]([^'\"]+)['\"]", text)
        assets = set(re.findall(r"/static/([\w./-]+\.(?:js|css))", text))
        assets.update(re.findall(r"filename\s*=\s*['\"]([^'\"]+\.(?:js|css))['\"]", text))
        late_css = []
        # Child templates often have no body tag. Track the enclosing block,
        # and report only candidates; final inheritance must be inspected.
        for m in re.finditer(r"<link\b[^>]*>", text, re.I):
            if not re.search(r"stylesheet", m.group(), re.I):
                continue
            blocks = []
            for b in re.finditer(r"{%\s*(block\s+(\w+)|endblock\b)[^%]*%}", text[:m.start()]):
                if b.group(2):
                    blocks.append(b.group(2))
                elif blocks:
                    blocks.pop()
            body = text.lower().rfind("<body", 0, m.start()) >= 0
            if body or any(b in ("content", "workspace_content", "layout", "main_content") for b in blocks):
                late_css.append(line_at(text, m.start()))
        rows[rel] = {"file": "templates/" + rel, "bytes": len(raw),
                     "template_dependencies": sorted(set(links)), "direct_assets": sorted(assets),
                     "css_in_content_candidates": late_css, "signals": signals(text)}
    for rel, row in rows.items():
        pending, seen, inherited = [rel], set(), set()
        while pending:
            cur = pending.pop()
            if cur in seen or cur not in rows:
                continue
            seen.add(cur)
            inherited.update(rows[cur]["direct_assets"])
            pending.extend(rows[cur]["template_dependencies"])
        row["possible_assets_with_inheritance"] = sorted(inherited)
        row["missing_literal_dependencies"] = [d for d in row["template_dependencies"] if d not in rows]
    return rows, hashes


def build(root):
    routes, resources, registrations, errors, hashes = python_inventory(root)
    templates, template_hashes = template_inventory(root)
    hashes.update(template_hashes)
    scripts = []
    for path in sorted((root / "static").rglob("*.js")):
        raw = path.read_bytes()
        rel = path.relative_to(root).as_posix()
        hashes[rel] = hashlib.sha256(raw).hexdigest()
        public = root.parent / rel
        scripts.append({"file": rel, "bytes": len(raw),
                        "signals": signals(raw.decode("utf-8-sig", errors="replace")),
                        "local_public_copy_differs": public.exists() and public.read_bytes() != raw,
                        "local_public_copy_exists": public.exists()})
    referenced = {t for r in routes for t in r["templates"]}
    for t, row in templates.items():
        row["direct_route_references"] = sum(t in r["templates"] for r in routes)
    return {
        "schema_version": 1, "artifact_class": "Harness", "mode": "static-working-tree-not-runtime",
        "scope": ["app.py", "api/**/*.py", "src/**/*.py", "templates/**/*.html", "static/**/*.js"],
        "limitations": [
            "Declaration count is not a count of live screens; registration and prefix overrides require runtime validation.",
            "Dynamic rules/rendering and nested Jinja expressions are not fully resolved.",
            "Inherited assets are a possible superset: overridden blocks and conditional includes can remove them.",
            "Lexical JS signals include comments/strings and do not prove sequential requests or absence of shared timeouts.",
            "No browser timings, authenticated access or financial operations were executed.",
            "Legacy root apps and archived modules are outside the canonical application roots; templates include legacy candidates.",
        ],
        "summary": {"python_sources": len(hashes) - len(template_hashes) - len(scripts),
                    "route_declarations": len(routes), "resource_registrations": len(resources),
                    "get_route_declarations_with_literal_template": sum(bool(r["templates"]) and "GET" in (r["methods"] or []) for r in routes),
                    "dynamic_template_handlers": len({(r["file"],r["handler"]) for r in routes if r["dynamic_template"]}),
                    "templates": len(templates), "templates_directly_referenced": len(referenced),
                    "javascript_files": len(scripts), "python_parse_errors": len(errors)},
        "routes": routes, "resource_registrations": resources, "blueprint_registrations": registrations,
        "templates": templates, "scripts": scripts, "parse_errors": errors, "source_sha256": hashes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.app_root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "screen_inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output_dir / "routes.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["file", "line", "handler", "candidate_rule", "declared_rule", "methods", "templates", "dynamic_template", "runtime_verified"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["routes"])
    with (args.output_dir / "templates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["file", "bytes", "direct_route_references", "css_in_content_candidates", "direct_assets", "possible_assets_with_inheritance"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["templates"].values())
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
