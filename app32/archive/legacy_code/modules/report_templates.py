"""Gerenciador e gerador de templates de relatórios."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.postgres_helper import connect as pg_connect
from modules.report_models import ReportModelsManager


class ReportTemplatesManager:
    """Gerencia templates de relatórios armazenados no banco."""

    JSON_FIELDS = ("sections_config", "variables")

    def __init__(self) -> None:
        self._schema_ready = False

    def _get_connection(self):
        return pg_connect()

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS report_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                report_type VARCHAR(120) NOT NULL,
                page_config_id INTEGER NOT NULL REFERENCES report_models(id) ON DELETE CASCADE,
                sections_config TEXT,
                variables TEXT,
                created_by VARCHAR(120),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_report_templates_type
            ON report_templates(report_type)
            """
        )
        self._ensure_columns(cursor)
        conn.commit()
        conn.close()
        self._schema_ready = True

    def _ensure_columns(self, cursor) -> None:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'report_templates'
        """
        )
        existing = {row[0] for row in cursor.fetchall()}
        if "variables" not in existing:
            cursor.execute("ALTER TABLE report_templates ADD COLUMN variables TEXT")
        if "created_by" not in existing:
            cursor.execute(
                "ALTER TABLE report_templates ADD COLUMN created_by VARCHAR(120)"
            )
        if "updated_at" not in existing:
            cursor.execute(
                "ALTER TABLE report_templates ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )

    def _serialize_row(self, row) -> Dict[str, Any]:
        data = dict(row)
        for field in self.JSON_FIELDS:
            value = data.get(field)
            if isinstance(value, str):
                try:
                    data[field] = json.loads(value)
                except json.JSONDecodeError:
                    data[field] = None
        return data

    def get_all_templates(self) -> List[Dict[str, Any]]:
        self._ensure_schema()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, description, report_type, page_config_id,
                   sections_config, variables, created_by, created_at, updated_at
            FROM report_templates
            ORDER BY name ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._serialize_row(row) for row in rows]

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        self._ensure_schema()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, description, report_type, page_config_id,
                   sections_config, variables, created_by, created_at, updated_at
            FROM report_templates
            WHERE id = %s
            """,
            (template_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return self._serialize_row(row) if row else None

    def get_templates_by_type(self, report_type: str) -> List[Dict[str, Any]]:
        self._ensure_schema()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, description, report_type, page_config_id,
                   sections_config, variables, created_by, created_at, updated_at
            FROM report_templates
            WHERE report_type = %s
            ORDER BY name ASC
            """,
            (report_type,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._serialize_row(row) for row in rows]

    def save_template(self, template_data: Dict[str, Any]) -> Optional[int]:
        self._ensure_schema()
        required_fields = ("name", "report_type", "page_config_id")
        for field in required_fields:
            if not template_data.get(field):
                raise ValueError(f"Campo obrigatório: {field}")

        conn = self._get_connection()
        cursor = conn.cursor()
        sections_config = json.dumps(
            template_data.get("sections_config") or {}, ensure_ascii=False
        )
        variables = json.dumps(template_data.get("variables") or {}, ensure_ascii=False)

        cursor.execute(
            """
            INSERT INTO report_templates (
                name, description, report_type, page_config_id,
                sections_config, variables, created_by, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                template_data["name"],
                template_data.get("description"),
                template_data["report_type"],
                template_data["page_config_id"],
                sections_config,
                variables,
                template_data.get("created_by", "system"),
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return row[0] if row else None

    def update_template(
        self, template_id: int, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._ensure_schema()
        current = self.get_template(template_id)
        if not current:
            return {"success": False, "error": "Template não encontrado"}

        merged = {**current, **template_data}
        sections_config = json.dumps(
            merged.get("sections_config") or {}, ensure_ascii=False
        )
        variables = json.dumps(merged.get("variables") or {}, ensure_ascii=False)

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE report_templates
            SET name = %s,
                description = %s,
                report_type = %s,
                page_config_id = %s,
                sections_config = %s,
                variables = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                merged.get("name"),
                merged.get("description"),
                merged.get("report_type"),
                merged.get("page_config_id"),
                sections_config,
                variables,
                datetime.utcnow(),
                template_id,
            ),
        )
        conn.commit()
        conn.close()
        return {"success": True}

    def delete_template(self, template_id: int) -> Dict[str, Any]:
        self._ensure_schema()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM report_templates WHERE id = %s", (template_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected:
            return {"success": True}
        return {"success": False, "error": "Template não encontrado"}


class ReportTemplateGenerator:
    """Responsável por gerar HTML simples a partir de templates configurados."""

    def __init__(self, manager: Optional[ReportTemplatesManager] = None) -> None:
        self.templates_manager = manager or ReportTemplatesManager()
        self.models_manager = ReportModelsManager()

    def generate_report_from_template(
        self, template_id: int, data_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data_context = data_context or {}
        template = self.templates_manager.get_template(template_id)
        if not template:
            return {"error": "Template não encontrado"}

        page_config = self.models_manager.get_model(template["page_config_id"])
        if not page_config:
            return {"error": "Configuração de página não encontrada"}

        html = self._render_html(template, page_config, data_context)
        return {
            "success": True,
            "html": html,
            "template_name": template["name"],
            "page_config_name": page_config.get("name"),
            "report_type": template["report_type"],
        }

    def _render_html(
        self,
        template: Dict[str, Any],
        page_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        header_title = context.get("report_title") or template["name"]
        company_name = context.get("company_name", "Empresa")
        sections = template.get("sections_config") or {}

        section_html: List[str] = []
        for section_key, section_meta in sections.items():
            if isinstance(section_meta, dict) and not section_meta.get("enabled", True):
                continue
            section_html.append(
                self._render_section(
                    section_key, section_meta, context.get(section_key)
                )
            )

        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='pt-BR'>",
            "<head>",
            "<meta charset='utf-8' />",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 24px; }",
            "h1 { font-size: 24px; margin-bottom: 4px; }",
            "h2 { margin-top: 32px; }",
            ".section { margin-bottom: 24px; }",
            ".section pre { background: #f7f7f7; padding: 12px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{header_title}</h1>",
            f"<p><strong>Empresa:</strong> {company_name}</p>",
            f"<p><strong>Configuração de página:</strong> {page_config.get('name')}</p>",
            f"<p><strong>Tipo de relatório:</strong> {template.get('report_type')}</p>",
            *section_html,
            "</body>",
            "</html>",
        ]
        return "\n".join(html_parts)

    def _render_section(
        self, key: str, meta: Any, data: Any  # pragma: no cover - render helper
    ) -> str:
        meta = meta or {}
        title = meta.get("title") if isinstance(meta, dict) else None
        title = title or key.replace("_", " ").title()
        description = ""
        if isinstance(meta, dict):
            description = meta.get("description") or ""

        if isinstance(data, list):
            content = (
                "<ul>"
                + "".join(
                    f"<li>{json.dumps(item, ensure_ascii=False)}</li>" for item in data
                )
                + "</ul>"
            )
        elif isinstance(data, dict):
            content = f"<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"
        elif data:
            content = f"<p>{data}</p>"
        else:
            content = "<p><em>Sem dados fornecidos para esta seção.</em></p>"

        return (
            "<div class='section'>"
            f"<h2>{title}</h2>"
            f"{f'<p>{description}</p>' if description else ''}"
            f"{content}"
            "</div>"
        )
