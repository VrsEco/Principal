# -*- coding: utf-8 -*-
"""
Migra ui_pages/ui_elements para ui_pages_v2/ui_elements_v2 com códigos fixos
Formato: page_code XXX, element_code XXX
"""

from pathlib import Path
from database.postgres_helper import connect


def normalize(code: str) -> str:
    code = (code or "").strip()
    if code.isdigit():
        return code.zfill(3)
    return code[:3]


def get_next(cur, table: str, column: str) -> str:
    cur.execute(f"SELECT {column} FROM {table} ORDER BY {column} DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        return "001"
    try:
        return str(int(row[0]) + 1).zfill(3)
    except Exception:
        return "001"


def migrate():
    conn = connect()
    cur = conn.cursor()

    # Carregar páginas antigas
    cur.execute("SELECT id, page_code, page_name, page_route, template_file FROM ui_pages ORDER BY id")
    pages_old = cur.fetchall()

    page_map = {}  # old_id -> new_id

    for old_id, page_code, page_name, page_route, template_file in pages_old:
        code = normalize(page_code) if page_code else None
        if not code:
            code = get_next(cur, 'ui_pages_v2', 'page_code')
        cur.execute(
            """
            INSERT INTO ui_pages_v2 (page_code, page_name, template_file, page_route, description, active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (code, page_name, template_file or '', page_route, f"Migrado de ui_pages id={old_id}")
        )
        new_id = cur.fetchone()[0]
        page_map[old_id] = (new_id, code)

    # Carregar elementos antigos
    cur.execute("SELECT page_id, element_code, element_type, element_name, html_id, html_class FROM ui_elements ORDER BY page_id, element_code")
    elems_old = cur.fetchall()

    for page_id, element_code, element_type, element_name, html_id, html_class in elems_old:
        if page_id not in page_map:
            continue
        new_page_id, _ = page_map[page_id]
        code = normalize(element_code) if element_code else None
        if not code:
            code = get_next(cur, 'ui_elements_v2', 'element_code')
        cur.execute(
            """
            INSERT INTO ui_elements_v2 (page_id, element_code, element_name, element_type, html_id, html_class, description, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            """,
            (
                new_page_id,
                code,
                element_name or f"Elemento {code}",
                element_type,
                html_id,
                html_class,
                f"Migrado de ui_elements page_id={page_id}"
            )
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
