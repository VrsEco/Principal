"""Gerador simples de relatórios em HTML."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from modules.report_models import ReportModelsManager


class ReportGenerator:
    """Gera previews e arquivos HTML baseados em modelos de relatório."""

    def __init__(self) -> None:
        self.models_manager = ReportModelsManager()
        self.output_dir = Path("temp_pdfs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_preview(
        self, model_config: Optional[Dict[str, Any]] = None, model_id: Optional[int] = None
    ) -> str:
        """Retorna HTML com base no modelo fornecido ou salvo."""
        model = None
        if model_id:
            model = self.models_manager.get_model(model_id)
        combined_model = {**(model or {}), **(model_config or {})}
        return self._render_html(combined_model)

    def generate_pdf_report(
        self, model_config: Optional[Dict[str, Any]] = None, model_id: Optional[int] = None
    ) -> str:
        """Gera arquivo HTML (placeholder de PDF) e retorna o caminho."""
        html = self.generate_html_preview(model_config, model_id)
        filename = (
            f"report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}.html"
        )
        file_path = self.output_dir / filename
        file_path.write_text(html, encoding="utf-8")
        return str(file_path)

    def _render_html(self, model: Dict[str, Any]) -> str:
        title = model.get("name", "Relatório")
        description = model.get("description", "Visualização de relatório.")
        margins = model.get(
            "margins",
            {
                "top": model.get("margin_top", 20),
                "right": model.get("margin_right", 15),
                "bottom": model.get("margin_bottom", 15),
                "left": model.get("margin_left", 20),
            },
        )
        sections = model.get("sections") or [
            "Resumo Executivo",
            "Detalhes",
            "Conclusões",
        ]

        html_sections = []
        for section in sections:
            if isinstance(section, dict):
                section_title = section.get("title") or section.get("name") or "Seção"
                section_desc = section.get("description") or ""
            else:
                section_title = str(section)
                section_desc = ""
            html_sections.append(
                "<section>"
                f"<h2>{section_title}</h2>"
                f"{f'<p>{section_desc}</p>' if section_desc else ''}"
                "<p><em>Conteúdo disponível após integrar dados reais.</em></p>"
                "</section>"
            )

        return "\n".join(
            [
                "<!DOCTYPE html>",
                "<html lang='pt-BR'>",
                "<meta charset='utf-8' />",
                "<style>",
                "body { font-family: Arial, sans-serif; margin: 24px; }",
                "header, footer { margin-bottom: 16px; }",
                "section { margin-bottom: 24px; }",
                "</style>",
                "<body>",
                "<header>",
                f"<h1>{title}</h1>",
                f"<p>{description}</p>",
                (
                    f"<small>Margens - "
                    f"Superior: {margins.get('top')} | "
                    f"Direita: {margins.get('right')} | "
                    f"Inferior: {margins.get('bottom')} | "
                    f"Esquerda: {margins.get('left')}</small>"
                ),
                "</header>",
                *html_sections,
                "<footer>",
                f"<small>Prévia gerada em {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC</small>",
                "</footer>",
                "</body>",
                "</html>",
            ]
        )

