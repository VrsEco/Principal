#!/usr/bin/env python3
"""
Renumber ui_pages_v2/ui_elements_v2 to a fully numeric 3-digit standard.

Default mode is --dry-run (no writes). Review the mapping and rerun without
--dry-run to apply. Ordering is stable by page id, then element_code.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path to import database helpers
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres_helper import connect


def fetch_pages(cur) -> List[Tuple[int, str, str]]:
    cur.execute(
        """
        SELECT id, page_code, template_file
        FROM ui_pages_v2
        ORDER BY id
        """
    )
    return cur.fetchall()


def fetch_elements(cur, page_id: int) -> List[Tuple[int, str]]:
    cur.execute(
        """
        SELECT id, element_code
        FROM ui_elements_v2
        WHERE page_id=%s
        ORDER BY element_code
        """,
        (page_id,),
    )
    return cur.fetchall()


def normalize_numeric(code: str) -> str:
    clean = (code or "").strip()
    if clean.isdigit():
        return clean.zfill(3)
    return ""


def build_page_mapping(pages: List[Tuple[int, str, str]]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    next_code = 1
    for page_id, _, _ in pages:
        mapping[page_id] = f"{next_code:03d}"
        next_code += 1
    return mapping


def build_temp_page_mapping(pages: List[Tuple[int, str, str]]) -> Dict[int, str]:
    """
    Use a non-overlapping 3-char code (prefix 'T' + base36) to avoid unique
    conflicts while updating page codes in-place. Guarantees length == 3.
    """
    mapping: Dict[int, str] = {}
    next_code = 1
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def to_base36(num: int) -> str:
        if num < 0:
            num = 0
        if num >= 36 * 36:
            # Fallback to last valid 2-char base36
            num = 36 * 36 - 1
        d1 = alphabet[num // 36]
        d0 = alphabet[num % 36]
        return f"{d1}{d0}"

    for page_id, _, _ in pages:
        suffix = to_base36(next_code)
        mapping[page_id] = f"T{suffix}"
        next_code += 1
    return mapping


def build_element_mapping(elements: List[Tuple[int, str]]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    next_code = 1
    for element_id, _ in elements:
        mapping[element_id] = f"{next_code:03d}"
        next_code += 1
    return mapping


def renumber(dry_run: bool) -> None:
    conn = connect()
    cur = conn.cursor()

    pages = fetch_pages(cur)
    if not pages:
        print("No pages found in ui_pages_v2.")
        conn.close()
        return

    page_map = build_page_mapping(pages)

    print("Planned page remap (old -> new):")
    for page_id, old_code, template in pages:
        print(f"  {old_code or '???':>4} -> {page_map[page_id]}  ({template})")

    total_elem_updates = 0

    # First pass: element updates (safe, no unique constraint on element_code per page_id)
    for page_id, old_page_code, template in pages:
        elements = fetch_elements(cur, page_id)
        if not elements:
            continue
        elem_map = build_element_mapping(elements)
        if dry_run:
            for elem_id, old_elem_code in elements:
                print(
                    f"    [{old_page_code or '???'}-{old_elem_code or '??'}] "
                    f"-> [{page_map[page_id]}-{elem_map[elem_id]}] ({template})"
                )
            continue

        for elem_id, _ in elements:
            cur.execute(
                "UPDATE ui_elements_v2 SET element_code=%s WHERE id=%s",
                (elem_map[elem_id], elem_id),
            )
            total_elem_updates += 1

    if dry_run:
        print("\nDry-run only. No changes applied.")
        conn.close()
        return

    # Second pass: pages using temp codes to avoid unique conflicts
    temp_map = build_temp_page_mapping(pages)
    for page_id, _old_code, _ in pages:
        cur.execute(
            "UPDATE ui_pages_v2 SET page_code=%s WHERE id=%s",
            (temp_map[page_id], page_id),
        )

    for page_id, _old_code, _ in pages:
        cur.execute(
            "UPDATE ui_pages_v2 SET page_code=%s WHERE id=%s",
            (page_map[page_id], page_id),
        )

    conn.commit()
    conn.close()
    print(
        f"Renumber completed. Pages updated: {len(pages)}, "
        f"elements updated: {total_elem_updates}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Renumber ui_pages_v2/ui_elements_v2 to numeric 3-digit codes."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without applying (default).",
    )
    args = parser.parse_args()
    dry_run = True if args.dry_run or args.dry_run is None else False
    renumber(dry_run=dry_run)


if __name__ == "__main__":
    main()
