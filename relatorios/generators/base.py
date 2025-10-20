#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classe Base para Geradores de Relatórios
Sistema PEVAPP22

Esta classe fornece a estrutura base que todos os geradores
de relatórios específicos devem herdar.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from jinja2 import Template
import sys
import os

# Adiciona o diretório pai ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from relatorios.config.visual_identity import *
from modules.report_models import ReportModelsManager


class BaseReportGenerator(ABC):
    """
    Classe base para todos os geradores de relatórios
    
    Fornece:
    - Configuração de modelo de página
    - Estrutura de cabeçalho/rodapé padrão
    - Métodos para adicionar seções
    - Renderização final do HTML
    - Aplicação de identidade visual
    """
    
    def __init__(self, report_model_id=None):
        """
        Inicializa o gerador
        
        Args:
            report_model_id: ID do modelo de página (opcional)
        """
        self.report_model_id = report_model_id
        self.report_model = None
        self.sections = []
        self.data = {}
        self.custom_styles = {}
        
        # Carregar modelo se especificado
        if report_model_id:
            self._load_report_model()
    
    def _load_report_model(self):
        """Carrega o modelo de relatório do banco"""
        try:
            manager = ReportModelsManager()
            self.report_model = manager.get_model(self.report_model_id)
        except Exception as e:
            print(f"Erro ao carregar modelo {self.report_model_id}: {e}")
            self.report_model = None
    
    # ====================================
    # MÉTODOS ABSTRATOS (devem ser implementados)
    # ====================================
    
    @abstractmethod
    def get_report_title(self):
        """Retorna o título do relatório"""
        pass
    
    @abstractmethod
    def fetch_data(self, **kwargs):
        """
        Busca os dados necessários para o relatório
        
        Args:
            **kwargs: Parâmetros necessários (company_id, process_id, etc)
        """
        pass
    
    @abstractmethod
    def build_sections(self):
        """
        Constrói as seções do relatório
        
        Deve chamar self.add_section() para cada seção
        """
        pass
    
    # ====================================
    # CONFIGURAÇÃO DE PÁGINA
    # ====================================
    
    def set_page_model(self, model_id):
        """Define o modelo de página a ser usado"""
        self.report_model_id = model_id
        self._load_report_model()
    
    def get_page_css(self):
        """Retorna o CSS da página"""
        return generate_page_style(self.report_model)
    
    # ====================================
    # CABEÇALHO E RODAPÉ
    # ====================================
    
    def get_default_header(self):
        """
        Retorna estrutura padrão de cabeçalho
        
        Pode ser sobrescrito em geradores específicos
        """
        company_name = self.data.get('company', {}).get('name', 'Nome da Empresa')
        report_title = self.get_report_title()
        generation_date = datetime.now().strftime('%d/%m/%Y')
        
        return f"""
        <div class="report-header">
            <div class="header-grid">
                <div class="header-cell">
                    <strong>{company_name}</strong>
                </div>
                <div class="header-cell header-center">
                    <strong>{report_title}</strong>
                </div>
                <div class="header-cell header-right">
                    {generation_date}
                </div>
            </div>
        </div>
        """
    
    def get_default_footer(self):
        """
        Retorna estrutura padrão de rodapé
        
        Pode ser sobrescrito em geradores específicos
        """
        year = datetime.now().year
        
        return f"""
        <div class="report-footer">
            <div class="footer-grid">
                <div class="footer-cell">
                    © {year} Sistema PEVAPP22
                </div>
                <div class="footer-cell footer-right">
                    <span class="page-number"></span>
                </div>
            </div>
        </div>
        """
    
    def get_header(self):
        """
        Retorna o cabeçalho (pode usar modelo ou padrão)
        
        Se o modelo tiver altura 0, não retorna cabeçalho.
        Se o modelo tiver conteúdo de cabeçalho, usa ele.
        Senão, usa o padrão.
        """
        if self.report_model and self.report_model.get('header_height', 0) == 0:
            return ""  # Sem cabeçalho se altura for 0
        
        if self.report_model and self.report_model['header'].get('content'):
            # Processar o conteúdo do modelo
            return self._process_header_content(self.report_model['header']['content'])
        else:
            # Usar padrão
            return self.get_default_header()
    
    def get_footer(self):
        """
        Retorna o rodapé (pode usar modelo ou padrão)
        
        Se o modelo tiver altura 0, não retorna rodapé.
        Se o modelo tiver conteúdo de rodapé, usa ele.
        Senão, usa o padrão.
        """
        if self.report_model and self.report_model.get('footer_height', 0) == 0:
            return ""  # Sem rodapé se altura for 0
        
        if self.report_model and self.report_model['footer'].get('content'):
            return self._process_footer_content(self.report_model['footer']['content'])
        else:
            return self.get_default_footer()
    
    def _process_header_content(self, content):
        """Processa variáveis no conteúdo do cabeçalho"""
        # Substituir variáveis
        company = self.data.get('company', {})
        process = self.data.get('process', {})
        macro = self.data.get('macro', {})

        def _display(value, fallback='\u2014'):
            if isinstance(value, str):
                value = value.strip()
            if value in (None, ''):
                return fallback
            return str(value)

        macro_code_raw = macro.get('code')
        macro_name_raw = macro.get('name')
        macro_code = macro_code_raw.strip() if isinstance(macro_code_raw, str) else macro_code_raw
        macro_name = macro_name_raw.strip() if isinstance(macro_name_raw, str) else macro_name_raw

        if macro_code and macro_name:
            macro_display = f"{macro_code} - {macro_name}"
        elif macro_code:
            macro_display = macro_code
        elif macro_name:
            macro_display = macro_name
        else:
            macro_display = None

        content = content.replace('{{ company.name }}', _display(company.get('name')))
        content = content.replace('{{ report.title }}', self.get_report_title())
        content = content.replace('{{ date }}', datetime.now().strftime('%d/%m/%Y'))
        content = content.replace('{{ datetime }}', datetime.now().strftime('%d/%m/%Y %H:%M'))
        content = content.replace('{{ year }}', str(datetime.now().year))
        content = content.replace('{{ process.code }}', _display(process.get('code')))
        content = content.replace('{{ process.name }}', _display(process.get('name')))
        content = content.replace('{{ process.responsible }}', _display(process.get('responsible')))
        content = content.replace('{{ macro.name }}', _display(macro_name))
        content = content.replace('{{ macro.code }}', _display(macro_code))
        content = content.replace('{{ macro.display }}', _display(macro_display))

        # Se o conteúdo já define o wrapper principal (ex.: custom-report-header),
        # evitar adicionar uma camada extra que aplicaria estilos/classe do layout padrão.
        if 'custom-report-header' in content or 'class="report-header"' in content:
            return content

        return f'<div class="report-header">{content}</div>'
    
    def _process_footer_content(self, content):
        """Processa variáveis no conteúdo do rodapé"""
        content = content.replace('{{ system }}', 'Sistema PEVAPP22')
        content = content.replace('{{ page }}', '<span class="page-number"></span>')
        content = content.replace('{{ pages }}', '<span class="total-pages"></span>')
        content = content.replace('{{ year }}', str(datetime.now().year))

        if 'custom-report-footer' in content or 'class="report-footer"' in content:
            return content

        return f'<div class="report-footer">{content}</div>'
    
    # ====================================
    # GERENCIAMENTO DE SEÇÕES
    # ====================================
    
    def add_section(self, title, content, section_class='', break_before=False):
        """
        Adiciona uma seção ao relatório
        
        Args:
            title: Título da seção
            content: Conteúdo HTML da seção
            section_class: Classes CSS adicionais
            break_before: Se deve forçar quebra de página antes
        """
        self.sections.append({
            'title': title,
            'content': content,
            'class': section_class,
            'break_before': break_before
        })
    
    def clear_sections(self):
        """Limpa todas as seções"""
        self.sections = []
    
    # ====================================
    # ESTILOS CUSTOMIZADOS
    # ====================================
    
    def add_custom_style(self, name, css):
        """
        Adiciona um estilo customizado
        
        Args:
            name: Nome do estilo
            css: Código CSS
        """
        self.custom_styles[name] = css
    
    def get_custom_styles(self):
        """Retorna todos os estilos customizados"""
        return '\n'.join(self.custom_styles.values())
    
    # ====================================
    # MÉTODOS AUXILIARES PARA SEÇÕES
    # ====================================
    
    def create_table(self, headers, rows, table_class='data-table'):
        """
        Cria uma tabela HTML
        
        Args:
            headers: Lista de cabeçalhos
            rows: Lista de listas (dados das linhas)
            table_class: Classe CSS da tabela
        
        Returns:
            str: HTML da tabela
        """
        html = f'<table class="{table_class}">\n'
        
        # Cabeçalhos
        html += '  <thead>\n    <tr>\n'
        for header in headers:
            html += f'      <th>{header}</th>\n'
        html += '    </tr>\n  </thead>\n'
        
        # Linhas
        html += '  <tbody>\n'
        for row in rows:
            html += '    <tr>\n'
            for cell in row:
                html += f'      <td>{cell}</td>\n'
            html += '    </tr>\n'
        html += '  </tbody>\n'
        
        html += '</table>\n'
        return html
    
    def create_info_box(self, title, content, box_type='info'):
        """
        Cria uma caixa de informação
        
        Args:
            title: Título da caixa
            content: Conteúdo
            box_type: Tipo ('info', 'warning', 'success', 'error')
        
        Returns:
            str: HTML da caixa
        """
        return f"""
        <div class="info-box info-box-{box_type}">
            <div class="info-box-title">{title}</div>
            <div class="info-box-content">{content}</div>
        </div>
        """
    
    # ====================================
    # RENDERIZAÇÃO FINAL
    # ====================================
    
    def generate_html(self, **kwargs):
        """
        Gera o HTML final do relatório
        
        Args:
            **kwargs: Parâmetros para fetch_data
        
        Returns:
            str: HTML completo do relatório
        """
        # 1. Buscar dados
        self.fetch_data(**kwargs)
        
        # 2. Construir seções
        self.build_sections()
        
        # 3. Montar HTML
        html = self._build_html_template()
        
        return html
    
    def _build_html_template(self):
        """Monta o template HTML completo"""
        
        # Determinar offsets padrão para cabeçalho/rodapé
        mm_to_px = 96 / 25.4
        extra_spacing_mm = 3.0

        def _safe_mm(value, fallback):
            try:
                return float(value)
            except (TypeError, ValueError):
                return fallback

        header_conf = (self.report_model or {}).get('header', {}) if self.report_model else {}
        footer_conf = (self.report_model or {}).get('footer', {}) if self.report_model else {}

        header_height_mm = _safe_mm(header_conf.get('height'), SPACING.get('header_height', 25))
        footer_height_mm = _safe_mm(footer_conf.get('height'), SPACING.get('footer_height', 15))

        # Se altura for 0, não adicionar espaçamento extra
        header_offset_mm = header_height_mm + (extra_spacing_mm if header_height_mm > 0 else 0)
        footer_offset_mm = footer_height_mm + (extra_spacing_mm if footer_height_mm > 0 else 0)

        header_offset_value = f"{header_offset_mm:.2f}mm"
        footer_offset_value = f"{footer_offset_mm:.2f}mm"

        header_offset_px = header_offset_mm * mm_to_px
        footer_offset_px = footer_offset_mm * mm_to_px

        # CSS base
        base_css = f"""
        {self.get_page_css()}
        
        /* Variáveis CSS */
        :root {{
            {get_css_variables()}
            --report-header-offset: {header_offset_value};
            --report-footer-offset: {footer_offset_value};
        }}
        
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
        }}
        
        /* Seções */
        {generate_section_css()}
        
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
        }}

        /* Aplicar margens apenas se houver cabeçalho/rodapé */
        .report-content {{
            margin-top: var(--report-header-offset);
            margin-bottom: var(--report-footer-offset);
        }}
        
        /* CSS do cabeçalho - apenas se houver cabeçalho */
        {f'.report-header {{ border-bottom: 2px solid {COLORS["primary"]}; padding-bottom: {SPACING["padding_md"]}; margin-bottom: {SPACING["space_md"]}; }}' if header_height_mm > 0 else ''}
        
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
        
        /* CSS do rodapé - apenas se houver rodapé */
        {f'.report-footer {{ border-top: 1px solid {COLORS["border_medium"]}; padding-top: {SPACING["padding_sm"]}; margin-top: {SPACING["space_lg"]}; font-size: {TYPOGRAPHY["font_size_small"]}; }}' if footer_height_mm > 0 else ''}
        
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
    
    def _render_section(self, section):
        """Renderiza uma seção individual"""
        break_class = ' new-section' if section['break_before'] else ''
        
        return f"""
    <section class="report-section {section['class']}{break_class}">
        <h1>{section['title']}</h1>
        <div class="section-content">
            {section['content']}
        </div>
    </section>
        """

