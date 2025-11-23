# -*- coding: utf-8 -*-
"""
UI Reference Service V2
- Códigos fixos, formato XXX (página) e XXX (elemento)
- Sem reciclagem: marcar active=false ao invés de reutilizar
"""

from typing import Optional, List, Dict
from database.postgres_helper import connect


class UIReferenceServiceV2:
    @staticmethod
    def _normalize_page_code(code: str) -> str:
        code = (code or "").strip()
        if code.isdigit():
            return code.zfill(3)
        return code[:3]

    @staticmethod
    def _normalize_element_code(code: str) -> str:
        code = (code or "").strip()
        if code.isdigit():
            return code.zfill(3)
        return code[:3]

    @staticmethod
    def _get_next_page_code(conn) -> str:
        cur = conn.cursor()
        cur.execute("SELECT page_code FROM ui_pages_v2 ORDER BY page_code DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "001"
        last = row[0].strip()
        try:
            nxt = int(last) + 1
            return str(nxt).zfill(3)
        except Exception:
            return "001"

    @staticmethod
    def _get_next_element_code(conn, page_id: int) -> str:
        cur = conn.cursor()
        cur.execute(
            "SELECT element_code FROM ui_elements_v2 WHERE page_id=%s ORDER BY element_code DESC LIMIT 1",
            (page_id,),
        )
        row = cur.fetchone()
        if not row:
            return "001"
        last = row[0].strip()
        try:
            nxt = int(last) + 1
            return str(nxt).zfill(3)
        except Exception:
            return "001"

    @staticmethod
    def register_page(
        page_name: str,
        template_file: str,
        page_route: Optional[str] = None,
        page_code: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, page_code FROM ui_pages_v2 WHERE template_file=%s",
                (template_file,),
            )
            existing = cur.fetchone()
            if existing:
                return {"id": existing[0], "page_code": existing[1], "status": "exists"}

            code = (
                UIReferenceServiceV2._normalize_page_code(page_code)
                if page_code
                else None
            )
            if not code:
                code = UIReferenceServiceV2._get_next_page_code(conn)

            cur.execute(
                """
                INSERT INTO ui_pages_v2 (page_code, page_name, template_file, page_route, description, active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING id
                """,
                (code, page_name, template_file, page_route, description),
            )
            page_id = cur.fetchone()[0]
            conn.commit()
            return {"id": page_id, "page_code": code, "status": "created"}
        finally:
            conn.close()

    @staticmethod
    def register_element(
        page_code: str,
        element_name: str,
        element_type: Optional[str] = None,
        html_id: Optional[str] = None,
        html_class: Optional[str] = None,
        element_code: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM ui_pages_v2 WHERE page_code=%s AND active=TRUE",
                (page_code,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Página {page_code} não encontrada ou inativa")
            page_id = row[0]

            code = (
                UIReferenceServiceV2._normalize_element_code(element_code)
                if element_code
                else None
            )
            if not code:
                code = UIReferenceServiceV2._get_next_element_code(conn, page_id)

            cur.execute(
                """
                INSERT INTO ui_elements_v2 (page_id, element_code, element_name, element_type, html_id, html_class, description, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id
                """,
                (page_id, code, element_name, element_type, html_id, html_class, description),
            )
            el_id = cur.fetchone()[0]
            conn.commit()
            return {"id": el_id, "element_code": code, "status": "created"}
        finally:
            conn.close()

    @staticmethod
    def deactivate_page(page_code: str) -> bool:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE ui_pages_v2 SET active=FALSE WHERE page_code=%s", (page_code,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def deactivate_element(page_code: str, element_code: str) -> bool:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE ui_elements_v2
                SET active=FALSE
                WHERE page_id = (SELECT id FROM ui_pages_v2 WHERE page_code=%s)
                AND element_code=%s
                """,
                (page_code, element_code),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def get_page_by_template(template_file: str) -> Optional[Dict]:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, page_code, page_name, page_route, template_file, active
                FROM ui_pages_v2
                WHERE template_file=%s
                """,
                (template_file,),
            )
            row = cur.fetchone()
            if not row:
                return None
            keys = ["id", "page_code", "page_name", "page_route", "template_file", "active"]
            return dict(zip(keys, row))
        finally:
            conn.close()

    @staticmethod
    def get_all_pages() -> List[Dict]:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT page_code, page_name, page_route, template_file, active
                FROM ui_pages_v2
                ORDER BY page_code
                """
            )
            rows = cur.fetchall()
            keys = ["page_code", "page_name", "page_route", "template_file", "active"]
            return [dict(zip(keys, r)) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_elements_by_page(page_code: str) -> List[Dict]:
        conn = connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT e.element_code, e.element_name, e.element_type, e.html_id, e.html_class, e.active
                FROM ui_elements_v2 e
                JOIN ui_pages_v2 p ON e.page_id = p.id
                WHERE p.page_code=%s
                ORDER BY e.element_code
                """,
                (page_code,),
            )
            rows = cur.fetchall()
            keys = ["element_code", "element_name", "element_type", "html_id", "html_class", "active"]
            return [dict(zip(keys, r)) for r in rows]
        finally:
            conn.close()
