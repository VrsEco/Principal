#!/usr/bin/env python3
"""
UI cataloger (v2)
-----------------
Rebuilds the UI addressing catalog using ui_pages_v2/ui_elements_v2.
This prevents the "??-XXX" fallback by ensuring every rendered template
has a fixed 3-digit page code and data-ref elements are registered.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set

from bs4 import BeautifulSoup

# Make project modules importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.ui_reference_service_v2 import UIReferenceServiceV2

LOGGER = logging.getLogger("ui_catalog_v2")

EXCLUDED_DIRS = {"components", "partials", "includes", "fragments", "macros"}
MAX_NAME_LENGTH = 120


@dataclass
class PageCandidate:
    template_path: Path
    route: str
    name: str


@dataclass
class ElementCandidate:
    code: str
    element_type: str
    name: str
    html_id: Optional[str]
    html_class: Optional[str]


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def normalize_code(raw_code: str) -> str:
    clean = (raw_code or "").strip()
    if clean.isdigit():
        return clean.zfill(3)
    return clean[:3].upper()


def read_file(path: Path) -> Optional[str]:
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    LOGGER.error("Could not read file with supported encodings: %s", path)
    return None


def infer_route(template_path: Path, content: str) -> str:
    route_match = re.search(r"Route:\s*([/\w\-\._]+)", content, flags=re.IGNORECASE)
    if route_match:
        return route_match.group(1)
    return "/" + template_path.with_suffix("").as_posix()


def infer_page_name(template_path: Path, content: str) -> str:
    title_match = re.search(
        r"{%\s*block\s+title\s*%}(.+?){%\s*endblock\s*%}",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if title_match:
        title = re.sub(r"\s*\|.*$", "", title_match.group(1)).strip()
        if title:
            return title[:MAX_NAME_LENGTH]
    return template_path.stem.replace("_", " ").title()[:MAX_NAME_LENGTH]


def extract_elements(content: str) -> List[ElementCandidate]:
    soup = BeautifulSoup(content, "html.parser")
    elements: List[ElementCandidate] = []
    for node in soup.select("[data-ref]"):
        raw_code = node.get("data-ref")
        if not raw_code:
            continue
        code = normalize_code(raw_code)
        element_type = node.name or "element"
        name = (
            node.get("aria-label")
            or node.get("title")
            or node.get_text(strip=True)
            or node.get("id")
            or element_type
        )
        html_id = node.get("id")
        html_class = " ".join(node.get("class", [])) or None
        elements.append(
            ElementCandidate(
                code=code,
                element_type=element_type,
                name=name[:MAX_NAME_LENGTH],
                html_id=html_id,
                html_class=html_class,
            )
        )
    return elements


class UICatalogV2:
    def __init__(self, templates_dir: Path, dry_run: bool = False):
        self.templates_dir = templates_dir
        self.dry_run = dry_run
        self.pages_created = 0
        self.pages_reused = 0
        self.elements_created = 0

    def run(self) -> None:
        html_files = list(self._discover_templates())
        LOGGER.info("Scanning %d templates for UI references", len(html_files))

        for template in html_files:
            self._process_template(template)

        LOGGER.info(
            "Finished. Pages created: %d | reused: %d | elements created: %d",
            self.pages_created,
            self.pages_reused,
            self.elements_created,
        )

    def _discover_templates(self) -> Iterable[Path]:
        for path in self.templates_dir.rglob("*.html"):
            if path.name == "base.html":
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            yield path

    def _process_template(self, template_path: Path) -> None:
        content = read_file(template_path)
        if content is None:
            return

        rel_path = template_path.relative_to(self.templates_dir)
        route = infer_route(rel_path, content)
        page_name = infer_page_name(rel_path, content)
        elements = extract_elements(content)

        page_code = self._ensure_page(rel_path, page_name, route)
        if not page_code:
            LOGGER.error(
                "Skipping element sync because page code is empty for %s", rel_path
            )
            return

        self._sync_elements(page_code, elements)

    def _ensure_page(self, rel_path: Path, page_name: str, route: str) -> Optional[str]:
        template_key = rel_path.as_posix()
        existing = UIReferenceServiceV2.get_page_by_template(template_key)
        if existing and existing.get("active"):
            self.pages_reused += 1
            LOGGER.debug("Reused page %s -> %s", existing["page_code"], template_key)
            return normalize_code(existing["page_code"])

        if self.dry_run:
            LOGGER.info("[DRY RUN] Would create page for %s (%s)", template_key, route)
            self.pages_created += 1
            return "<pending>"

        created = UIReferenceServiceV2.register_page(
            page_name=page_name,
            template_file=template_key,
            page_route=route,
            description=f"Auto-registered from {template_key}",
        )
        self.pages_created += 1
        LOGGER.info("Registered page %s (%s)", created["page_code"], template_key)
        return normalize_code(created["page_code"])

    def _sync_elements(self, page_code: str, elements: List[ElementCandidate]) -> None:
        if not elements:
            return

        existing_codes: Set[str] = {
            normalize_code(el["element_code"])
            for el in UIReferenceServiceV2.get_elements_by_page(page_code)
        }

        for element in elements:
            if normalize_code(element.code) in existing_codes:
                continue
            if self.dry_run:
                LOGGER.info(
                    "[DRY RUN] Would register element %s-%s (%s)",
                    page_code,
                    element.code,
                    element.name,
                )
                self.elements_created += 1
                continue

            UIReferenceServiceV2.register_element(
                page_code=page_code,
                element_name=element.name,
                element_type=element.element_type,
                html_id=element.html_id,
                html_class=element.html_class,
                element_code=element.code,
                description="Auto-registered from data-ref",
            )
            self.elements_created += 1
            LOGGER.debug(
                "Registered element %s-%s (%s)", page_code, element.code, element.name
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catalog UI elements into ui_pages_v2/ui_elements_v2."
    )
    parser.add_argument(
        "--templates-dir",
        default="templates",
        help="Templates directory relative to project root (default: templates).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report actions without writing to the database.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(verbose=args.verbose)

    templates_dir = (PROJECT_ROOT / args.templates_dir).resolve()
    if not templates_dir.exists():
        LOGGER.error("Templates directory not found: %s", templates_dir)
        sys.exit(1)

    LOGGER.info(
        "Starting UI catalog (v2) | dir=%s | dry_run=%s",
        templates_dir,
        args.dry_run,
    )

    catalog = UICatalogV2(templates_dir=templates_dir, dry_run=args.dry_run)
    catalog.run()


if __name__ == "__main__":
    main()
