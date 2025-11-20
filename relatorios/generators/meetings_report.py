#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Relatório de Reuniões
Sistema PEVAPP22
Gera relatórios de reuniões usando a sistemática de padrões e modelos
"""

import json
from datetime import datetime
from relatorios.generators.base import BaseReportGenerator
from config_database import get_db
from relatorios.config.visual_identity import *


class MeetingsReportGenerator(BaseReportGenerator):
    """
    Gerador de relatórios de reuniões
    """

    def __init__(self, report_model_id=None):
        """
        Inicializa o gerador de relatórios de reuniões

        Args:
            report_model_id: ID do modelo de página a ser usado
        """
        super().__init__(report_model_id)
        self.db = get_db()

        # Configuração das seções disponíveis
        self.available_sections = {
            "info": "Informações da Reunião",
            "guests": "Convidados",
            "agenda": "Pauta",
            "participants": "Participantes",
            "discussions": "Discussões",
            "activities": "Atividades Geradas",
        }

        # Seções incluídas por padrão
        self.include_info = True
        self.include_guests = True
        self.include_agenda = True
        self.include_participants = True
        self.include_discussions = True
        self.include_activities = True

    def configure(
        self,
        info=True,
        guests=True,
        agenda=True,
        participants=True,
        discussions=True,
        activities=True,
    ):
        """
        Configura quais seções incluir no relatório

        Args:
            info: Incluir informações da reunião
            guests: Incluir convidados
            agenda: Incluir pauta
            participants: Incluir participantes
            discussions: Incluir discussões
            activities: Incluir atividades geradas
        """
        self.include_info = info
        self.include_guests = guests
        self.include_agenda = agenda
        self.include_participants = participants
        self.include_discussions = discussions
        self.include_activities = activities

    def get_report_title(self):
        """Retorna o título do relatório"""
        return "Relatório de Reuniões"

    def fetch_data(self, company_id, meeting_id=None):
        """
        Busca os dados necessários para o relatório

        Args:
            company_id: ID da empresa
            meeting_id: ID da reunião específica (opcional)
        """
        # Buscar dados da empresa
        company = self.db.get_company(company_id)
        if not company:
            raise ValueError(f"Empresa {company_id} não encontrada")

        # Buscar reuniões
        if meeting_id:
            meeting = self.db.get_meeting(meeting_id)
            if not meeting or meeting.get("company_id") != company_id:
                raise ValueError(f"Reunião {meeting_id} não encontrada")
            meetings = [meeting]
        else:
            meetings = self.db.list_company_meetings(company_id)

        if not meetings:
            raise ValueError("Nenhuma reunião encontrada")

        # Armazenar dados
        self.data = {"company": company, "meetings": meetings, "meeting_id": meeting_id}

    def build_sections(self):
        """
        Constrói as seções do relatório
        """
        # Limpar seções anteriores
        self.clear_sections()

        company = self.data["company"]
        meetings = self.data["meetings"]
        meeting_id = self.data["meeting_id"]

        # Processar cada reunião
        for meeting in meetings:
            # Adicionar título do relatório (primeira seção)
            self._add_title_section(
                company, meeting_id, meeting.get("title", "Reunião")
            )

            # Adicionar seções da reunião
            self._add_meeting_sections(meeting)

    def generate_html(self, company_id, meeting_id=None):
        """
        Gera o HTML do relatório de reuniões

        Args:
            company_id: ID da empresa
            meeting_id: ID da reunião específica (None para todas)

        Returns:
            str: HTML do relatório
        """
        # Usar o método da classe base
        return super().generate_html(company_id=company_id, meeting_id=meeting_id)

    def _build_html_template(self):
        """Monta o template HTML completo com CSS específico para reuniões"""

        # Determinar offsets padrão para cabeçalho/rodapé
        mm_to_px = 96 / 25.4
        extra_spacing_mm = 3.0

        def _safe_mm(value, fallback):
            try:
                return float(value)
            except (TypeError, ValueError):
                return fallback

        header_conf = (
            (self.report_model or {}).get("header", {}) if self.report_model else {}
        )
        footer_conf = (
            (self.report_model or {}).get("footer", {}) if self.report_model else {}
        )

        # Para Model_7 (sem cabeçalho/rodapé), usar offsets zero
        if self.report_model and self.report_model.get("id") == 7:
            header_height_mm = 0
            footer_height_mm = 0
            header_offset_mm = 0
            footer_offset_mm = 0
        else:
            header_height_mm = _safe_mm(
                header_conf.get("height"), SPACING.get("header_height", 25)
            )
            footer_height_mm = _safe_mm(
                footer_conf.get("height"), SPACING.get("footer_height", 15)
            )
            header_offset_mm = header_height_mm + extra_spacing_mm
            footer_offset_mm = footer_height_mm + extra_spacing_mm

        header_offset_value = f"{header_offset_mm:.2f}mm"
        footer_offset_value = f"{footer_offset_mm:.2f}mm"

        header_offset_px = header_offset_mm * mm_to_px
        footer_offset_px = footer_offset_mm * mm_to_px

        # CSS base + CSS específico para reuniões
        base_css = f"""
        {self.get_page_css()}
        
        /* Variáveis CSS */
        :root {{
            {get_css_variables()}
            --report-header-offset: {header_offset_value};
            --report-footer-offset: {footer_offset_value};
        }}
        
        /* Estilos específicos para relatórios de reuniões */
        {self._get_custom_css()}
        
        /* Reset e Base */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {TYPOGRAPHY['font_family_primary']};
            font-size: {TYPOGRAPHY['font_size_body']};
            line-height: {TYPOGRAPHY['line_height_normal']};
            color: {COLORS['text_dark']};
            margin: 0;
            padding: 0;
        }}
        
        /* Seções */
        {generate_section_css()}
        
        /* Folha de Rosto/Capa */
        .cover-page {{
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            position: relative;
        }}
        
        .cover-content {{
            max-width: 80%;
            margin: 0 auto;
        }}
        
        .cover-title {{
            margin-bottom: 4rem;
        }}
        
        .cover-title h2 {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {COLORS['text_dark']};
            margin-bottom: 1.5rem;
            text-transform: uppercase;
            letter-spacing: 3px;
        }}
        
        .cover-title h3 {{
            font-size: 1.8rem;
            font-weight: normal;
            color: {COLORS['text_medium']};
            margin-bottom: 0;
        }}
        
        .cover-company {{
            margin-bottom: 4rem;
        }}
        
        .client-logo {{
            width: 80px;
            height: auto;
            margin-bottom: 1.5rem;
        }}
        
        .cover-company h4 {{
            font-size: 2.2rem;
            font-weight: bold;
            color: {COLORS['text_dark']};
            margin-bottom: 0.8rem;
        }}
        
        .cover-company p {{
            font-size: 1.3rem;
            color: {COLORS['text_medium']};
            margin-bottom: 0;
        }}
        
        .cover-footer {{
            border-top: 2px solid {COLORS['primary']};
            padding-top: 2rem;
            margin-bottom: 3rem;
        }}
        
        .cover-footer p {{
            font-size: 1rem;
            color: {COLORS['text_medium']};
            margin-bottom: 0.5rem;
        }}
        
        .cover-versus-info {{
            position: absolute;
            bottom: 2rem;
            right: 2rem;
            text-align: right;
            opacity: 0.7;
        }}
        
        .versus-logo-small {{
            width: 40px;
            height: auto;
            margin-bottom: 0.5rem;
        }}
        
        .versus-text {{
            font-size: 0.9rem;
            font-weight: 600;
            color: {COLORS['text_medium']};
            margin-bottom: 0.2rem;
        }}
        
        .versus-subtitle {{
            font-size: 0.8rem;
            color: {COLORS['text_light']};
            margin-bottom: 0;
        }}
        
        /* Quebra de página após capa */
        .page-break {{
            page-break-before: always;
        }}
        
        /* CSS específico para impressão - evitar páginas em branco */
        @media print {{
            .cover-page {{
                page-break-after: always;
                page-break-inside: avoid;
            }}
            
            body {{
                margin: 0;
                padding: 0;
            }}
            
            .report-section:first-of-type {{
                page-break-before: avoid;
            }}
            
            /* Evitar quebras de página desnecessárias */
            .cover-page-wrapper {{
                page-break-before: avoid;
            }}
            
            /* Garantir que não há espaços extras */
            * {{
                box-sizing: border-box;
            }}
        }}
        
        /* Tabelas */
        {generate_table_css()}
        
        /* Quebras de página */
        {generate_page_break_css()}
        
        /* Cabeçalho e Rodapé - Configuração para impressão */
        @page {{
            @top-center {{
                content: element(page-header);
            }}
            @bottom-center {{
                content: element(page-footer);
            }}
        }}
        
        /* Cabeçalho */
        .custom-report-header {{
            position: running(page-header);
        }}
        
        .custom-report-footer {{
            position: running(page-footer);
        }}
        
        /* Para navegadores que não suportam position: running() */
        @media print {{
            .custom-report-header {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                z-index: 1000;
                background: white;
            }}
            
            .custom-report-footer {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                z-index: 1000;
                background: white;
            }}
            
            .report-content {{
                margin-top: var(--report-header-offset);
                margin-bottom: var(--report-footer-offset);
            }}
        }}

        .report-content {{
            margin-top: var(--report-header-offset);
            margin-bottom: var(--report-footer-offset);
        }}
        
        .report-header {{
            border-bottom: 2px solid {COLORS['primary']};
            padding-bottom: {SPACING['padding_md']};
            margin-bottom: {SPACING['space_md']};
        }}
        
        .header-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
        }}
        
        .header-cell {{
            font-size: {TYPOGRAPHY['font_size_small']};
        }}
        
        .header-center {{
            text-align: center;
        }}
        
        .header-right {{
            text-align: right;
        }}
        
        /* Rodapé */
        .report-footer {{
            border-top: 1px solid {COLORS['border_medium']};
            padding-top: {SPACING['padding_sm']};
            margin-top: {SPACING['space_lg']};
            font-size: {TYPOGRAPHY['font_size_small']};
        }}
        
        .footer-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
        }}
        
        .footer-right {{
            text-align: right;
        }}

        .page-number,
        .total-pages {{
            display: inline-block;
            min-width: 2ch;
            text-align: center;
            font-variant-numeric: tabular-nums;
        }}

        .page-number::after {{
            content: attr(data-page);
        }}

        .total-pages::after {{
            content: attr(data-total);
        }}

        @media print {{
            .page-number::after {{
                content: counter(page);
            }}
            
            .total-pages::after {{
                content: counter(pages);
            }}
        }}
        
        /* Info boxes */
        .info-box {{
            padding: {SPACING['padding_md']};
            margin: {SPACING['space_sm']} 0;
            border-left: 4px solid;
            border-radius: {BORDERS['radius_md']};
        }}
        
        .info-box-info {{
            background: {COLORS['bg_light']};
            border-color: {COLORS['info']};
        }}
        
        .info-box-warning {{
            background: #fef3c7;
            border-color: {COLORS['warning']};
        }}
        
        .info-box-success {{
            background: #d1fae5;
            border-color: {COLORS['success']};
        }}
        
        .info-box-error {{
            background: #fee2e2;
            border-color: {COLORS['error']};
        }}
        
        .info-box-title {{
            font-weight: {TYPOGRAPHY['font_weight_semibold']};
            margin-bottom: 4px;
        }}
        
        /* Customizações específicas */
        {self.get_custom_styles()}
        """

        page_script = """
    <script>
    (function() {
        'use strict';

        function pad(value) {
            return String(value).padStart(2, '0');
        }

        function getViewportHeight() {
            return window.innerHeight || document.documentElement.clientHeight || 1;
        }

        function getTotalPages() {
            var body = document.body;
            var html = document.documentElement;
            var totalHeight = Math.max(
                body.scrollHeight,
                body.offsetHeight,
                html.clientHeight,
                html.scrollHeight,
                html.offsetHeight
            );
            var viewport = getViewportHeight();
            return Math.max(1, Math.ceil(totalHeight / viewport));
        }

        function getCurrentPage(totalPages) {
            var scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
            var viewport = getViewportHeight();
            return Math.min(totalPages, Math.max(1, Math.floor(scrollTop / viewport) + 1));
        }

        const DEFAULT_HEADER_OFFSET = {header_offset_px:.2f};
        const DEFAULT_FOOTER_OFFSET = {footer_offset_px:.2f};

        function collectSpacing(element, fallback) {
            if (!element) {
                return fallback;
            }

            var styles = window.getComputedStyle(element);
            var height = element.offsetHeight || 0;
            var marginTop = parseFloat(styles.marginTop || '0');
            var marginBottom = parseFloat(styles.marginBottom || '0');

            var total = height + marginTop + marginBottom;
            return total > 0 ? total : fallback;
        }

        function updateLayoutSpacing() {
            var root = document.documentElement;
            var header = document.querySelector('.custom-report-header') || document.querySelector('.report-header');
            var footer = document.querySelector('.custom-report-footer') || document.querySelector('.report-footer');

            var headerOffset = collectSpacing(header, DEFAULT_HEADER_OFFSET);
            var footerOffset = collectSpacing(footer, DEFAULT_FOOTER_OFFSET);

            if (headerOffset > 0) {
                root.style.setProperty('--report-header-offset', headerOffset + 'px');
            }

            if (footerOffset > 0) {
                root.style.setProperty('--report-footer-offset', footerOffset + 'px');
            }
        }

        function updatePagination() {
            var totalPages = getTotalPages();
            var currentPage = getCurrentPage(totalPages);

            document.querySelectorAll('.page-number').forEach(function (el) {
                el.dataset.page = pad(currentPage);
                el.textContent = pad(currentPage);
            });

            document.querySelectorAll('.total-pages').forEach(function (el) {
                el.dataset.total = pad(totalPages);
                el.textContent = pad(totalPages);
            });
        }

        function refreshLayout() {
            updateLayoutSpacing();
            updatePagination();
        }

        document.addEventListener('DOMContentLoaded', refreshLayout);
        window.addEventListener('load', refreshLayout);
        window.addEventListener('resize', refreshLayout);
        window.addEventListener('scroll', updatePagination);
    })();
    </script>
        """

        # Montar HTML
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.get_report_title()}</title>
    <style>
        {base_css}
    </style>
</head>
<body>
    {self.get_header()}
    
    <div class="report-content">
        {''.join([self._render_section(s) for s in self.sections])}
    </div>
    
    {self.get_footer()}
    {page_script}
</body>
</html>
        """

        return html

    def _get_custom_css(self):
        """Retorna CSS específico para relatórios de reuniões, alinhado com a identidade visual."""
        return """
        /* Estilos específicos para relatórios de reuniões */
        .book-title-wrapper > h1 { display: none; } /* Oculta H1 da seção do título */

        /* Nova estrutura do relatório */
        .report-title-section {
            margin-top: 0;
            margin-bottom: 8mm;
        }
        
        .report-title-section h1 {
            font-size: 24pt;
            font-weight: 700;
            color: #1a76ff;
            margin: 0 0 2mm 0;
            text-align: center;
        }
        
        .report-title-section h2 {
            font-size: 9pt;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 4mm 0;
            border-bottom: 2px solid #1a76ff;
            padding-bottom: 4mm;
        }
        
        .report-info-list {
            margin-top: 4mm;
            margin-left: 0;
            list-style: none;
            padding: 0;
        }
        
        .report-info-list li {
            margin-bottom: 2mm;
            font-size: 10pt;
            color: #475569;
        }
        
        /* Seções principais */
        .preliminary-section, .execution-section, .activities-section {
            margin-bottom: 12mm;
        }
        
        .preliminary-item, .execution-item {
            margin-bottom: 6mm;
            padding: 4mm;
            background: #f8fafc;
            border-left: 4px solid #1a76ff;
            border-radius: 4px;
        }
        
        .preliminary-item strong, .execution-item strong {
            color: #1a76ff;
            font-weight: 600;
        }
        
        /* Cards de convidados e participantes em 4 colunas */
        .guests-list, .participants-list {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 3mm;
            margin-top: 4mm;
        }
        
        .guest-item, .participant-item {
            background: #f1f5f9;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 3mm;
            font-size: 9pt;
            text-align: center;
        }
        
        .guest-item strong, .participant-item strong {
            display: block;
            font-weight: 600;
            color: #1a76ff;
            margin-bottom: 1mm;
        }
        
        .guest-item .contact-info, .participant-item .contact-info {
            font-size: 8pt;
            color: #64748b;
            margin-top: 1mm;
        }
        
        /* Listas normais para outras seções */
        .agenda-list, .discussions-list {
            margin-top: 4mm;
            margin-left: 8mm;
        }
        
        .agenda-item {
            margin-bottom: 2mm;
            font-size: 10pt;
        }
        
        .discussion-item {
            margin-bottom: 4mm;
            padding: 4mm;
            background: #fefce8;
            border-left: 3px solid #f59e0b;
            border-radius: 4px;
        }
        
        /* Tabela de atividades */
        .activities-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 4mm;
            font-size: 9pt;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .activities-table th {
            background: linear-gradient(135deg, #1a76ff, #0d47a1);
            color: white;
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            border: none;
            font-size: 10pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .activities-table td {
            padding: 8px 12px;
            border: none;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: top;
            font-size: 9pt;
        }
        
        .activities-table tr:nth-child(even) {
            background: #f8fafc;
        }
        
        .activities-table tr:nth-child(odd) {
            background: white;
        }
        
        .activities-table tr:hover {
            background: #e3f2fd;
            transition: background-color 0.2s ease;
        }
        
        .activities-table tr:last-child td {
            border-bottom: none;
        }

        .meeting-info-grid {
            display: grid;
            gap: 4mm;
            margin-bottom: 8mm;
        }
        
        .meeting-info-row {
            display: flex;
            align-items: flex-start;
            gap: 4mm;
        }
        
        .meeting-info-label {
            font-weight: 600;
            color: #475569;
            min-width: 120px;
            flex-shrink: 0;
        }
        
        .meeting-info-value {
            color: #0f172a;
            flex: 1;
        }
        
        .guests-list, .participants-list {
            display: grid;
            gap: 4mm;
            margin-top: 4mm;
        }
        
        .guest-item, .participant-item {
            background: #f8fafc;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            padding: 6mm;
        }
        
        .guest-contact, .participant-contact {
            display: flex;
            gap: 6mm;
            margin-top: 4mm;
            font-size: 9pt;
            color: #64748b;
        }
        
        .guest-contact span, .participant-contact span {
            display: flex;
            align-items: center;
            gap: 2mm;
        }
        
        .guest-contact span:empty, .participant-contact span:empty {
            display: none;
        }
        
        .agenda-list {
            display: grid;
            gap: 4mm;
        }
        
        .agenda-item {
            display: flex;
            gap: 4mm;
            align-items: flex-start;
        }
        
        .agenda-number {
            background: #1a76ff;
            color: #ffffff;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9pt;
            font-weight: 700;
            flex-shrink: 0;
        }
        
        .agenda-content {
            flex: 1;
            padding-top: 2px; /* Alinhamento fino */
        }
        
        .discussions-list {
            display: grid;
            gap: 4mm;
        }
        
        .discussion-item {
            background: #fefce8;
            border: 1px solid #f59e0b;
            border-left-width: 4px;
            border-radius: 6px;
            padding: 6mm;
        }
        
        .discussion-item h4 {
            margin: 0 0 4mm 0;
            color: #0f172a;
            font-size: 11pt;
            font-weight: 600;
        }
        
        .discussion-content {
            color: #475569;
            line-height: 1.5;
            white-space: pre-line;
        }
        
        .activities-list {
            display: grid;
            gap: 4mm;
        }
        
        .activity-item {
            background: #f0fdf4;
            border: 1px solid #10b981;
            border-left-width: 4px;
            border-radius: 6px;
            padding: 6mm;
        }
        
        .activity-item h4 {
            margin: 0 0 4mm 0;
            color: #0f172a;
            font-size: 11pt;
            font-weight: 600;
        }
        
        .activity-details {
            display: grid;
            gap: 2mm;
        }
        
        .activity-detail-row {
            display: flex;
            gap: 4mm;
        }
        
        .activity-label {
            font-weight: 600;
            color: #475569;
            min-width: 80px;
            flex-shrink: 0;
        }
        
        .activity-value {
            color: #0f172a;
            flex: 1;
        }
        
        .report-metadata {
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6mm;
            margin-top: 8mm;
            font-size: 9pt;
        }
        
        .report-metadata p {
            margin: 2px 0;
            color: #475569;
        }
        
        /* Melhorias visuais */
        .report-section {
            margin-bottom: 12mm;
        }
        
        .report-section h1 {
            border-bottom: 2px solid #1a76ff;
            padding-bottom: 4mm;
            margin-bottom: 8mm;
        }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 2mm 4mm;
            border-radius: 4px;
            font-size: 8pt;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-completed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-in-progress {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-draft {
            background: #e5e7eb;
            color: #374151;
        }
        """

    def _add_title_section(self, company, meeting_id, meeting_title):
        """Adiciona folha de rosto/capa"""
        current_datetime = datetime.now().strftime("%d/%m/%Y às %H:%M")

        cover_html = f"""
        <div class="cover-page">
            <div class="cover-content">
                <div class="cover-title">
                    <h2>RELATÓRIO DE REUNIÃO</h2>
                    <h3>{meeting_title}</h3>
                </div>
                
                <div class="cover-company">
                    <img src="/uploads/logos/company_{company.get('id', '')}_square.png" alt="Logo da Empresa" class="client-logo">
                    <h4>{company.get('name', 'Empresa')}</h4>
                    <p>{company.get('description', 'Descrição da empresa')}</p>
                </div>
                
                <div class="cover-footer">
                    <p>Gerado em: {current_datetime}</p>
                    <p>ID da Reunião: {meeting_id}</p>
                </div>
                
                <div class="cover-versus-info">
                    <img src="/static/img/versus-logo.png" alt="Versus Gestão Corporativa" class="versus-logo-small">
                    <p class="versus-text">Versus Gestão Corporativa</p>
                    <p class="versus-subtitle">Sistema de Gestão Empresarial</p>
                </div>
            </div>
        </div>
        """
        self.add_section(
            "", cover_html, section_class="cover-page-wrapper", break_before=False
        )

    def _add_meeting_sections(self, meeting):
        """Adiciona seções de uma reunião específica seguindo a nova estrutura"""

        # 1. Dados Preliminares e Convites
        self._add_preliminary_section(meeting)

        # 2. Execução da Reunião
        self._add_execution_section(meeting)

        # 3. Atividades Cadastradas
        self._add_activities_table_section(meeting)

    def _add_preliminary_section(self, meeting):
        """Seção: Dados Preliminares e Convites"""
        content_html = f"""
        <div class="preliminary-section">
            <div class="preliminary-item">
                <strong>Agendamento:</strong> {meeting.get('scheduled_date', 'N/A')} às {meeting.get('scheduled_time', 'N/A')}
            </div>
        """

        # Convidados
        guests_data = meeting.get("guests") or meeting.get("guests_json")
        if guests_data:
            try:
                guests = (
                    json.loads(guests_data)
                    if isinstance(guests_data, str)
                    else guests_data
                )
                if guests.get("internal") or guests.get("external"):
                    content_html += """
            <div class="preliminary-item">
                <strong>Convidados:</strong>
                <div class="guests-list">
                    """

                    # Convidados internos
                    if guests.get("internal"):
                        for guest in guests["internal"]:
                            email = guest.get("email", "").strip()
                            whatsapp = guest.get("whatsapp", "").strip()
                            contact_info = ""
                            if email and email != "N/A":
                                contact_info += f"📧 {email}"
                            if whatsapp and whatsapp != "N/A":
                                if contact_info:
                                    contact_info += "<br>"
                                contact_info += f"📱 {whatsapp}"

                            content_html += f"""
                    <div class="guest-item">
                        <strong>{guest.get('name', 'N/A')}</strong>
                        <div class="contact-info">{contact_info}</div>
                    </div>
                    """

                    # Convidados externos
                    if guests.get("external"):
                        for guest in guests["external"]:
                            email = guest.get("email", "").strip()
                            whatsapp = guest.get("whatsapp", "").strip()
                            contact_info = ""
                            if email and email != "N/A":
                                contact_info += f"📧 {email}"
                            if whatsapp and whatsapp != "N/A":
                                if contact_info:
                                    contact_info += "<br>"
                                contact_info += f"📱 {whatsapp}"

                            content_html += f"""
                    <div class="guest-item">
                        <strong>{guest.get('name', 'N/A')}</strong>
                        <div class="contact-info">{contact_info}</div>
                    </div>
                    """

                    content_html += """
                </div>
            </div>
                    """
            except:
                pass

        # Pauta
        agenda_data = meeting.get("agenda") or meeting.get("agenda_json")
        if agenda_data:
            try:
                agenda = (
                    json.loads(agenda_data)
                    if isinstance(agenda_data, str)
                    else agenda_data
                )
                if agenda:
                    content_html += """
            <div class="preliminary-item">
                <strong>Pauta:</strong>
                <div class="agenda-list">
                    """
                    for i, item in enumerate(agenda, 1):
                        if isinstance(item, dict):
                            title = item.get("title", f"Item {i}")
                        else:
                            title = str(item)
                        content_html += f"""
                    <div class="agenda-item">
                        {i}. {title}
                    </div>
                    """
                    content_html += """
                </div>
            </div>
                    """
            except:
                pass

        # Observações
        if meeting.get("invite_notes"):
            content_html += f"""
            <div class="preliminary-item">
                <strong>Observações:</strong> {meeting.get('invite_notes')}
            </div>
            """

        content_html += "</div>"
        self.add_section("📋 Dados Preliminares e Convites", content_html)

    def _add_execution_section(self, meeting):
        """Seção: Execução da Reunião"""
        content_html = f"""
        <div class="execution-section">
            <div class="execution-item">
                <strong>Executada em:</strong> {meeting.get('actual_date', 'N/A')} às {meeting.get('actual_time', 'N/A')}
            </div>
        """

        # Participantes
        participants_data = meeting.get("participants") or meeting.get(
            "participants_json"
        )
        if participants_data:
            try:
                participants = (
                    json.loads(participants_data)
                    if isinstance(participants_data, str)
                    else participants_data
                )
                if participants.get("internal") or participants.get("external"):
                    content_html += """
            <div class="execution-item">
                <strong>Participantes:</strong>
                <div class="participants-list">
                    """

                    # Participantes internos
                    if participants.get("internal"):
                        for p in participants["internal"]:
                            email = p.get("email", "").strip()
                            whatsapp = p.get("whatsapp", "").strip()
                            contact_info = ""
                            if email and email != "N/A":
                                contact_info += f"📧 {email}"
                            if whatsapp and whatsapp != "N/A":
                                if contact_info:
                                    contact_info += "<br>"
                                contact_info += f"📱 {whatsapp}"

                            content_html += f"""
                    <div class="participant-item">
                        <strong>{p.get('name', 'N/A')}</strong>
                        <div class="contact-info">{contact_info}</div>
                    </div>
                    """

                    # Participantes externos
                    if participants.get("external"):
                        for p in participants["external"]:
                            email = p.get("email", "").strip()
                            whatsapp = p.get("whatsapp", "").strip()
                            contact_info = ""
                            if email and email != "N/A":
                                contact_info += f"📧 {email}"
                            if whatsapp and whatsapp != "N/A":
                                if contact_info:
                                    contact_info += "<br>"
                                contact_info += f"📱 {whatsapp}"

                            content_html += f"""
                    <div class="participant-item">
                        <strong>{p.get('name', 'N/A')}</strong>
                        <div class="contact-info">{contact_info}</div>
                    </div>
                    """

                    content_html += """
                </div>
            </div>
                    """
            except:
                pass

        # Assuntos discutidos
        discussions_data = meeting.get("discussions") or meeting.get("discussions_json")
        if discussions_data:
            try:
                discussions = (
                    json.loads(discussions_data)
                    if isinstance(discussions_data, str)
                    else discussions_data
                )
                if discussions:
                    content_html += """
            <div class="execution-item">
                <strong>Assuntos discutidos:</strong>
                <div class="discussions-list">
                    """
                    for i, discussion in enumerate(discussions, 1):
                        if isinstance(discussion, dict):
                            title = discussion.get("title", f"Tópico {i}")
                            content = discussion.get(
                                "discussion", discussion.get("content", "")
                            )
                        else:
                            title = f"Tópico {i}"
                            content = str(discussion)

                        content_html += f"""
                    <div class="discussion-item">
                        <strong>{i}. {title}</strong><br>
                        {content}
                    </div>
                    """
                    content_html += """
                </div>
            </div>
                    """
            except:
                pass

        # Notas Gerais da Reunião
        if meeting.get("meeting_notes"):
            content_html += f"""
            <div class="execution-item">
                <strong>Notas Gerais da Reunião:</strong><br>
                {meeting.get('meeting_notes')}
            </div>
            """

        content_html += "</div>"
        self.add_section("⚡ Execução da Reunião", content_html)

    def _add_activities_table_section(self, meeting):
        """Seção: Atividades Cadastradas em formato de tabela"""
        activities_data = meeting.get("activities") or meeting.get("activities_json")
        if not activities_data:
            content_html = """
        <div class="activities-section">
            <p>Nenhuma atividade cadastrada.</p>
        </div>
            """
            self.add_section("📝 Atividades Cadastradas", content_html)
            return

        try:
            activities = (
                json.loads(activities_data)
                if isinstance(activities_data, str)
                else activities_data
            )
        except:
            activities = []

        if not activities:
            content_html = """
        <div class="activities-section">
            <p>Nenhuma atividade cadastrada.</p>
        </div>
            """
            self.add_section("📝 Atividades Cadastradas", content_html)
            return

        # Criar tabela de atividades
        content_html = """
        <div class="activities-section">
            <table class="activities-table">
                <thead>
                    <tr>
                        <th>O que</th>
                        <th>Quem</th>
                        <th>Quando</th>
                        <th>Como</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """

        for activity in activities:
            status_labels = {
                "pending": "Pendente",
                "in_progress": "Em Andamento",
                "completed": "Concluída",
                "cancelled": "Cancelada",
            }
            status = status_labels.get(activity.get("status"), "Desconhecido")

            content_html += f"""
                    <tr>
                        <td>{activity.get('title', 'Sem título')}</td>
                        <td>{activity.get('responsible', 'N/A')}</td>
                        <td>{activity.get('deadline', 'N/A')}</td>
                        <td>{activity.get('how', 'N/A')}</td>
                        <td>{status}</td>
                    </tr>
            """

        content_html += """
                </tbody>
            </table>
        </div>
        """

        self.add_section("📝 Atividades Cadastradas", content_html)

    def get_header(self):
        """
        Retorna o cabeçalho (pode usar modelo ou padrão)

        Se o modelo tiver conteúdo de cabeçalho, usa ele.
        Senão, usa o padrão.
        Para Model_7 (sem cabeçalho), retorna vazio.
        """
        # Model_7 não tem cabeçalho
        if self.report_model and self.report_model.get("id") == 7:
            return ""

        if (
            self.report_model
            and self.report_model.get("header")
            and self.report_model["header"].get("content")
        ):
            # Processar o conteúdo do modelo
            return self._process_header_content(self.report_model["header"]["content"])
        else:
            # Usar padrão
            return self.get_default_header()

    def get_footer(self):
        """
        Retorna o rodapé - sempre vazio para relatórios de reuniões
        """
        return ""

    def _add_meeting_info_section(self, meeting):
        """Adiciona seção de informações da reunião"""
        status_labels = {
            "draft": "Rascunho",
            "in_progress": "Em Andamento",
            "completed": "Concluída",
        }
        status = status_labels.get(meeting.get("status"), "Desconhecido")

        # Criar badge de status
        status_class = f"status-{meeting.get('status', 'unknown').replace('_', '-')}"
        status_badge = f'<span class="status-badge {status_class}">{status}</span>'

        content_html = f"""
            <div class="meeting-info-grid">
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Título:</span>
                    <span class="meeting-info-value"><strong>{meeting.get('title', 'N/A')}</strong></span>
                </div>
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Status:</span>
                    <span class="meeting-info-value">{status_badge}</span>
                </div>
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Data Prevista:</span>
                    <span class="meeting-info-value">{meeting.get('scheduled_date', 'N/A')} às {meeting.get('scheduled_time', 'N/A')}</span>
                </div>
        """

        if meeting.get("actual_date"):
            content_html += f"""
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Data Realizada:</span>
                    <span class="meeting-info-value">{meeting.get('actual_date')} às {meeting.get('actual_time', 'N/A')}</span>
                </div>
            """

        if meeting.get("invite_notes"):
            content_html += f"""
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Observações do Convite:</span>
                    <span class="meeting-info-value">{meeting.get('invite_notes')}</span>
                </div>
            """

        if meeting.get("meeting_notes"):
            content_html += f"""
                <div class="meeting-info-row">
                    <span class="meeting-info-label">Notas da Reunião:</span>
                    <span class="meeting-info-value">{meeting.get('meeting_notes')}</span>
                </div>
            """

        content_html += "</div>"
        self.add_section("📋 Informações da Reunião", content_html)

    def _add_guests_section(self, meeting):
        """Adiciona seção de convidados"""
        guests_data = meeting.get("guests") or meeting.get("guests_json")
        if not guests_data:
            return
        try:
            guests = (
                json.loads(guests_data) if isinstance(guests_data, str) else guests_data
            )
        except:
            return

        content_html = ""
        if guests.get("internal"):
            content_html += """
                <h3>Colaboradores Internos</h3>
                <div class="guests-list">
            """
            for guest in guests["internal"]:
                email = guest.get("email", "").strip()
                whatsapp = guest.get("whatsapp", "").strip()

                contact_html = ""
                if email and email != "N/A":
                    contact_html += f"<span>📧 {email}</span>"
                if whatsapp and whatsapp != "N/A":
                    contact_html += f"<span>📱 {whatsapp}</span>"

                content_html += f"""
                    <div class="guest-item">
                        <strong>{guest.get('name', 'N/A')}</strong>
                        {f'<div class="guest-contact">{contact_html}</div>' if contact_html else ''}
                    </div>
                """
            content_html += "</div>"

        if guests.get("external"):
            content_html += """
                <h3>Convidados Externos</h3>
                <div class="guests-list">
            """
            for guest in guests["external"]:
                email = guest.get("email", "").strip()
                whatsapp = guest.get("whatsapp", "").strip()

                contact_html = ""
                if email and email != "N/A":
                    contact_html += f"<span>📧 {email}</span>"
                if whatsapp and whatsapp != "N/A":
                    contact_html += f"<span>📱 {whatsapp}</span>"

                content_html += f"""
                    <div class="guest-item">
                        <strong>{guest.get('name', 'N/A')}</strong>
                        {f'<div class="guest-contact">{contact_html}</div>' if contact_html else ''}
                    </div>
                """
            content_html += "</div>"

        if content_html:
            self.add_section("👥 Convidados", content_html)

    def _add_agenda_section(self, meeting):
        """Adiciona seção de pauta"""
        agenda_data = meeting.get("agenda") or meeting.get("agenda_json")
        if not agenda_data:
            return
        try:
            agenda = (
                json.loads(agenda_data) if isinstance(agenda_data, str) else agenda_data
            )
        except:
            return
        if not agenda:
            return

        content_html = '<div class="agenda-list">'
        for i, item in enumerate(agenda, 1):
            # Se item é um dicionário, extrair o título
            if isinstance(item, dict):
                title = item.get("title", f"Item {i}")
            else:
                title = str(item)

            content_html += f"""
                <div class="agenda-item">
                    <div class="agenda-number">{i}.</div>
                    <div class="agenda-content">{title}</div>
                </div>
            """
        content_html += "</div>"
        self.add_section("📋 Pauta da Reunião", content_html)

    def _add_participants_section(self, meeting):
        """Adiciona seção de participantes"""
        participants_data = meeting.get("participants") or meeting.get(
            "participants_json"
        )
        if not participants_data:
            return
        try:
            participants = (
                json.loads(participants_data)
                if isinstance(participants_data, str)
                else participants_data
            )
        except:
            return

        content_html = ""
        if participants.get("internal"):
            content_html += """
                <h3>Colaboradores que Participaram</h3>
                <div class="participants-list">
            """
            for p in participants["internal"]:
                email = p.get("email", "").strip()
                whatsapp = p.get("whatsapp", "").strip()

                contact_html = ""
                if email and email != "N/A":
                    contact_html += f"<span>📧 {email}</span>"
                if whatsapp and whatsapp != "N/A":
                    contact_html += f"<span>📱 {whatsapp}</span>"

                content_html += f"""
                    <div class="participant-item">
                        <strong>{p.get('name', 'N/A')}</strong>
                        {f'<div class="participant-contact">{contact_html}</div>' if contact_html else ''}
                    </div>
                """
            content_html += "</div>"

        if participants.get("external"):
            content_html += """
                <h3>Participantes Externos</h3>
                <div class="participants-list">
            """
            for p in participants["external"]:
                email = p.get("email", "").strip()
                whatsapp = p.get("whatsapp", "").strip()

                contact_html = ""
                if email and email != "N/A":
                    contact_html += f"<span>📧 {email}</span>"
                if whatsapp and whatsapp != "N/A":
                    contact_html += f"<span>📱 {whatsapp}</span>"

                content_html += f"""
                    <div class="participant-item">
                        <strong>{p.get('name', 'N/A')}</strong>
                        {f'<div class="participant-contact">{contact_html}</div>' if contact_html else ''}
                    </div>
                """
            content_html += "</div>"

        if content_html:
            self.add_section("✅ Participantes", content_html)

    def _add_discussions_section(self, meeting):
        """Adiciona seção de discussões"""
        discussions_data = meeting.get("discussions") or meeting.get("discussions_json")
        if not discussions_data:
            return
        try:
            discussions = (
                json.loads(discussions_data)
                if isinstance(discussions_data, str)
                else discussions_data
            )
        except:
            return
        if not discussions:
            return

        content_html = '<div class="discussions-list">'
        for i, discussion in enumerate(discussions, 1):
            # Se discussion é um dicionário, extrair campos
            if isinstance(discussion, dict):
                title = discussion.get("title", f"Tópico {i}")
                content = discussion.get(
                    "discussion",
                    discussion.get("content", "Nenhuma discussão registrada"),
                )
            else:
                title = f"Tópico {i}"
                content = str(discussion)

            content_html += f"""
                <div class="discussion-item">
                    <h4>{i}. {title}</h4>
                    <div class="discussion-content">
                        {content}
                    </div>
                </div>
            """
        content_html += "</div>"
        self.add_section("💬 Discussões e Decisões", content_html)

    def _add_activities_section(self, meeting):
        """Adiciona seção de atividades geradas"""
        activities_data = meeting.get("activities") or meeting.get("activities_json")
        if not activities_data:
            return
        try:
            activities = (
                json.loads(activities_data)
                if isinstance(activities_data, str)
                else activities_data
            )
        except:
            return
        if not activities:
            return

        content_html = '<div class="activities-list">'
        for i, activity in enumerate(activities, 1):
            status_labels = {
                "pending": "Pendente",
                "in_progress": "Em Andamento",
                "completed": "Concluída",
                "cancelled": "Cancelada",
            }
            status = status_labels.get(activity.get("status"), "Desconhecido")
            deadline = activity.get("deadline", "N/A")

            # Criar badge de status
            status_class = (
                f"status-{activity.get('status', 'unknown').replace('_', '-')}"
            )
            status_badge = f'<span class="status-badge {status_class}">{status}</span>'

            content_html += f"""
                <div class="activity-item">
                    <h4>{i}. {activity.get('title', 'Atividade sem título')}</h4>
                    <div class="activity-details">
                        <div class="activity-detail-row">
                            <span class="activity-label">Responsável:</span>
                            <span class="activity-value">{activity.get('responsible', 'N/A')}</span>
                        </div>
                        <div class="activity-detail-row">
                            <span class="activity-label">Prazo:</span>
                            <span class="activity-value">{deadline}</span>
                        </div>
                        <div class="activity-detail-row">
                            <span class="activity-label">Status:</span>
                            <span class="activity-value">{status_badge}</span>
                        </div>
                    </div>
                </div>
            """
        content_html += "</div>"
        self.add_section("📝 Atividades Geradas", content_html)


def generate_meetings_report(
    company_id, meeting_id=None, model_id=None, save_path=None
):
    """
    Função auxiliar para gerar relatório de reuniões

    Args:
        company_id: ID da empresa
        meeting_id: ID da reunião específica (None para todas)
        model_id: ID do modelo de página
        save_path: Caminho para salvar o arquivo

    Returns:
        str: HTML do relatório
    """
    generator = MeetingsReportGenerator(report_model_id=model_id)

    # Configurar seções (todas por padrão)
    generator.configure(
        info=True,
        guests=True,
        agenda=True,
        participants=True,
        discussions=True,
        activities=True,
    )

    # Gerar HTML
    html_content = generator.generate_html(company_id, meeting_id)

    # Salvar se especificado
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Relatório salvo em: {save_path}")

    return html_content


if __name__ == "__main__":
    # Exemplo de uso
    html = generate_meetings_report(
        company_id=13,
        meeting_id=None,  # Todas as reuniões
        model_id=7,
        save_path="relatorio_reunioes.html",
    )
    print("Relatório gerado com sucesso!")
