#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Relatório de POP de Processo
Sistema app28

Este é um exemplo completo de gerador de relatório.
Use-o como template para criar outros tipos de relatórios.

COMO USAR:
----------
from relatorios.generators.process_pop import ProcessPOPReport

# Criar relatório
report = ProcessPOPReport()

# Gerar HTML
html = report.generate_html(
    company_id=6,
    process_id=123
)

# Salvar ou retornar
with open('relatorio.html', 'w', encoding='utf-8') as f:
    f.write(html)
"""

import sys
import os
import sqlite3
import base64
import mimetypes
from pathlib import Path
from datetime import datetime
from jinja2 import Template, Environment, FileSystemLoader

# Adiciona caminhos para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from relatorios.generators.base import BaseReportGenerator
from config_database import get_db


class ProcessPOPReport(BaseReportGenerator):
    """
    Relatório de Procedimento Operacional Padrão (POP) de um Processo
    
    Inclui:
    - Dados gerais do processo
    - Fluxograma (se disponível)
    - Atividades e etapas detalhadas
    - Rotinas associadas
    - Indicadores
    """
    
    def __init__(self, report_model_id=None):
        """
        Inicializa o gerador de relatório de POP
        
        Args:
            report_model_id: ID do modelo de página (opcional)
                Se None, usa configuração padrão
        """
        super().__init__(report_model_id)
        
        # Configurações específicas deste relatório
        self.include_flow = True
        self.include_activities = True
        self.include_routines = True
        self.include_indicators = False
        
        # Estilos customizados para este relatório
        self._add_custom_styles()
    
    def _add_custom_styles(self):
        """Adiciona estilos específicos deste relatório"""
        # Obter margens do modelo
        margin_top = 5  # Padrão
        margin_bottom = 5  # Padrão
        margin_left = 20  # Padrão
        margin_right = 15  # Padrão
        
        if self.report_model:
            margins = self.report_model.get('margins', {})
            margin_top = margins.get('top', 5)
            margin_bottom = margins.get('bottom', 5)
            margin_left = margins.get('left', 20)
            margin_right = margins.get('right', 15)
        
        # Construir CSS com margens dinâmicas
        css_layout = f"""
        /* Conteúdo principal - SEM offset, usa margens da página */
        .report-content {{
            margin: 0;
            padding: 0;
        }}
        
        /* Utilitários */
        .text-center {{
            text-align: center;
        }}

        /* Rodapé fixo */
        .report-footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 8px {margin_left}mm 8px {margin_left}mm;
            border-top: 2px solid rgba(59, 130, 246, 0.3);
            background: #ffffff;
            font-size: 9pt;
            color: #475569;
        }}

        .footer-grid-2col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            align-items: center;
        }}

        .footer-grid-3col {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
            align-items: center;
        }}

        .footer-left {{
            text-align: left;
            font-weight: 500;
        }}

        .footer-center {{
            text-align: center;
            font-weight: 500;
        }}

        .footer-right {{
            text-align: right;
            font-weight: 500;
        }}

        .footer-single {{
            text-align: center;
            font-weight: 500;
        }}

        /* Espaço para o rodapé fixo */
        body {{
            margin-bottom: {margin_bottom + 12}mm;  /* Margem + altura do rodapé */
        }}

        @media print {{
            .report-footer {{
                position: fixed;
                bottom: 0;
            }}
        }}

        /* Seção especial do Book - Título maior e mais destaque */
        .report-section.book-section {{
            padding: 16px 20px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.06), rgba(129, 140, 248, 0.03));
            border: 2px solid rgba(59, 130, 246, 0.25);
        }}

        .report-section.book-section h1 {{
            font-size: 15pt;
            padding: 10px 18px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(59, 130, 246, 0.10));
            border: 2px solid rgba(59, 130, 246, 0.35);
            text-align: center;
        }}

        .report-section.book-section .section-content {{
            margin-top: 3mm;
        }}

        .book-process-name {{
            text-align: center;
            font-size: 14pt;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 4mm;
            padding: 10px 16px;
            background: rgba(219, 234, 254, 0.4);
            border-radius: 8px;
            border: 1px solid rgba(147, 197, 253, 0.5);
        }}

        .process-info-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2.5mm;  /* Espaço entre subseções (linhas de info) */
        }}

        .process-info-row {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 8px 12px;
            background: rgba(241, 245, 249, 0.6);
            border-radius: 8px;
            border: 1px solid rgba(203, 213, 225, 0.4);
            /* NÃO quebra - mantém linha de informação inteira */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        .process-info-label {{
            min-width: 140px;
            font-size: 10pt;
            font-weight: 700;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .process-info-value {{
            flex: 1;
            font-size: 11pt;
            font-weight: 500;
            color: #0f172a;
        }}

        /* Seções principais - Espaço entre sessões: 5mm */
        .report-section {{
            margin: 0 0 5mm 0;
            padding: 12px 16px;
            background: linear-gradient(180deg, rgba(226, 232, 240, 0.35) 0%, rgba(248, 250, 252, 0.9) 100%);
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 12px;
            box-shadow: 0 4px 12px -8px rgba(15, 23, 42, 0.3);
            /* PERMITE quebra de página dentro da seção - FORÇA com !important */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}

        .report-section h1 {{
            margin: 0;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            font-size: 15pt;
            font-weight: 700;
            color: #0f172a;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.20), rgba(59, 130, 246, 0.06));
            border-radius: 999px;
            border: 1px solid rgba(59, 130, 246, 0.25);
            letter-spacing: 0.05em;
            text-transform: uppercase;
            /* NÃO permite que o título fique sozinho - sempre mantém com conteúdo */
            page-break-after: avoid !important;
            break-after: avoid !important;
        }}

        /* Regra específica para seção de indicadores - evitar título sozinho */
        .report-section:has(h1:contains("Indicadores")) {{
            /* Se a seção tem título de indicadores, garantir que pelo menos uma linha da tabela fique junto */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        /* Fallback para navegadores que não suportam :has() */
        .report-section.indicators-section {{
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        .report-section h1::before {{
            content: "";
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: #3b82f6;
        }}

        .report-section .section-content {{
            margin-top: 2.5mm;  /* Espaço entre título e conteúdo */
            display: flex;
            flex-direction: column;
            gap: 2.5mm;  /* Espaço entre subseções */
            /* Sobrescrever regras do visual_identity.py - PERMITE quebrar */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}

        .report-section .section-content > * {{
            /* Items individuais podem quebrar se necessário */
            page-break-inside: auto;
            break-inside: auto;
        }}

        .activity-list {{
            display: flex;
            flex-direction: column;
            gap: 2.5mm;  /* Espaço entre subseções (cards de atividades) */
            /* Sobrescrever regras do visual_identity.py */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}
        
        .activity-card {{
            background: #ffffff;
            border: 1px solid rgba(203, 213, 225, 0.9);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 12px 28px -26px rgba(15, 23, 42, 0.6);
            /* NÃO quebra - mantém atividade inteira */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .activity-card h3 {{
            margin: 0 0 2.5mm 0;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            font-size: 11pt;
            font-weight: 700;
            color: #0f172a;
            background: rgba(96, 165, 250, 0.16);
            border-radius: 999px;
            border: 1px solid rgba(96, 165, 250, 0.35);
            /* NÃO quebra */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .activity-card h3::before {{
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: #2563eb;
        }}
        
        .activity-meta {{
            margin: 0 0 2.5mm 0;
            display: inline-flex;
            flex-wrap: wrap;
            gap: 6px;
            font-size: 9pt;
            color: #475569;
            /* NÃO quebra */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .activity-meta span {{
            padding: 3px 8px;
            border-radius: 999px;
            background: rgba(191, 219, 254, 0.45);
            border: 1px solid rgba(147, 197, 253, 0.65);
        }}
        
        .activity-description {{
            color: #334155;
            line-height: 1.55;
            margin-bottom: 2.5mm;
            /* NÃO quebra */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .step-list {{
            display: flex;
            flex-direction: column;
            gap: 2.5mm;  /* Espaço entre subseções (passos) */
            /* Permite quebrar entre passos */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}
        
        .step-item {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(226, 232, 240, 0.35);
            border: 1px solid rgba(203, 213, 225, 0.55);
            /* NÃO quebra - mantém passo/etapa inteiro (texto + imagem juntos) */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .step-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 3px 8px;
            border-radius: 999px;
            font-size: 9pt;
            font-weight: 600;
            color: #1d4ed8;
            background: rgba(191, 219, 254, 0.6);
            border: 1px solid rgba(96, 165, 250, 0.45);
        }}
        
        .step-text {{
            flex: 1;
            font-size: 10pt;
            color: #1f2937;
            line-height: 1.5;
            display: flex;
            flex-direction: row;  /* Lado a lado */
            gap: 3mm;
            align-items: flex-start;
        }}
        
        .step-text-content {{
            flex: 1;
            line-height: 1.6;
            min-width: 0;  /* Permite quebra de linha */
        }}

        .step-text .step-image,
        .step-text img {{
            flex-shrink: 0;  /* Não encolher */
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            box-shadow: 0 2px 8px -2px rgba(15, 23, 42, 0.2);
        }}
        
        /* Quando só tem texto (sem imagem) */
        .step-text.text-only {{
            flex-direction: column;
        }}
        
        .step-text.text-only .step-text-content {{
            width: 100%;
        }}
        
        /* Tabela de Rotinas - Nova estrutura compacta */
        .routines-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9.5pt;
            /* A tabela pode quebrar entre linhas se necessário */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}
        
        .routines-table thead {{
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.20), rgba(59, 130, 246, 0.10));
            /* Cabeçalho não quebra */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            page-break-after: avoid !important;
            break-after: avoid !important;
        }}
        
        .routines-table th {{
            border: 1px solid rgba(148, 163, 184, 0.6);
            padding: 10px 12px;
            text-align: left;
            font-weight: 700;
            color: #0f172a;
        }}
        
        .routines-table tbody tr {{
            /* Cada linha NÃO quebra - mantém rotina inteira em uma linha */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .routines-table td {{
            border: 1px solid rgba(203, 213, 225, 0.6);
            padding: 8px 12px;
            text-align: left;
            vertical-align: top;
        }}
        
        .routines-table td.text-center {{
            text-align: center;
        }}
        
        .routines-table tbody tr:nth-child(even) {{
            background: rgba(248, 250, 252, 0.8);
        }}
        
        .routines-table tbody tr:hover {{
            background: rgba(219, 234, 254, 0.3);
        }}
        
        /* Tabela de Indicadores - Similar às rotinas */
        .indicators-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9.5pt;
            /* A tabela pode quebrar entre linhas se necessário */
            page-break-inside: auto !important;
            break-inside: auto !important;
        }}
        
        .indicators-table thead {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.20), rgba(16, 185, 129, 0.10));
            /* Cabeçalho não quebra */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            page-break-after: avoid !important;
            break-after: avoid !important;
        }}
        
        .indicators-table th {{
            border: 1px solid rgba(148, 163, 184, 0.6);
            padding: 10px 12px;
            text-align: left;
            font-weight: 700;
            color: #0f172a;
        }}
        
        .indicators-table tbody tr {{
            /* Cada linha NÃO quebra - mantém indicador inteiro em uma linha */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .indicators-table td {{
            border: 1px solid rgba(203, 213, 225, 0.6);
            padding: 8px 12px;
            text-align: left;
            vertical-align: top;
        }}
        
        .indicators-table td small {{
            color: #64748b;
            font-size: 8.5pt;
        }}
        
        .indicators-table tbody tr:nth-child(even) {{
            background: rgba(248, 250, 252, 0.8);
        }}
        
        .indicators-table tbody tr:hover {{
            background: rgba(209, 250, 229, 0.3);
        }}
        
        .info-callout {{
            border-left: 3px solid #2563eb;
            background: rgba(191, 219, 254, 0.35);
            padding: 10px 12px;
            border-radius: 10px;
            color: #1e293b;
            /* NÃO quebra - mantém callout inteiro */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .warning-callout {{
            border-left: 3px solid #f59e0b;
            background: rgba(254, 243, 199, 0.45);
            padding: 10px 12px;
            border-radius: 10px;
            color: #b45309;
            /* NÃO quebra - mantém callout inteiro */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        
        .flow-box {{
            border: 1px dashed rgba(148, 163, 184, 0.7);
            background: rgba(241, 245, 249, 0.65);
            border-radius: 10px;
            padding: 12px;
            color: #1e293b;
            line-height: 1.55;
        }}

        .flow-figure {{
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2.5mm;
            padding: 12px;
            border-radius: 10px;
            border: 1px dashed rgba(148, 163, 184, 0.6);
            background: rgba(226, 232, 240, 0.35);
            /* NÃO quebra - mantém figura inteira */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        .flow-figure-image {{
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            border: 1px solid rgba(148, 163, 184, 0.4);
            box-shadow: 0 4px 8px -4px rgba(15, 23, 42, 0.4);
        }}

        .flow-figure-caption {{
            font-size: 9pt;
            color: #475569;
            text-align: center;
        }}

        .flow-download {{
            padding: 12px;
            border-radius: 10px;
            border: 1px dashed rgba(148, 163, 184, 0.7);
            background: rgba(248, 250, 252, 0.75);
            color: #1e293b;
            line-height: 1.55;
        }}

        @media print {{
            body {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            .report-section {{
                box-shadow: none;
                background: #f3f4f6 !important;
                border-color: #cbd5e1 !important;
            }}

            .activity-card,
            .routine-card,
            .flow-figure,
            .step-item {{
                box-shadow: none;
                background: #ffffff !important;
            }}

            .flow-figure-image {{
                box-shadow: none;
            }}
        }}
        """
        
        # Adicionar CSS ao gerador
        self.add_custom_style('layout', css_layout)
    
    def get_default_header(self):
        """Cabeçalho desabilitado conforme solicitação do usuário"""
        return ""
    
    def get_default_footer(self):
        """Rodapé personalizado usando configuração do modelo"""
        if not self.report_model:
            return ""
        
        # Buscar conteúdo do rodapé (pode estar em footer.content ou footer_content)
        footer_conf = self.report_model.get('footer', {})
        footer_content = footer_conf.get('content', '') or self.report_model.get('footer_content', '')
        
        if not footer_content:
            return ""
        
        # Substituir variáveis PRIMEIRO (ordem importante: datetime antes de date/time!)
        from datetime import datetime
        now = datetime.now()
        
        # Substituir {{datetime}} ANTES para não conflitar com {{date}} e {{time}}
        footer_content = footer_content.replace('{{datetime}}', now.strftime('%d/%m/%Y às %H:%M'))
        footer_content = footer_content.replace('{{date}}', now.strftime('%d/%m/%Y'))
        footer_content = footer_content.replace('{{time}}', now.strftime('%H:%M'))
        
        # DEPOIS dividir por colunas (separador: ||)
        columns = footer_content.split('||')
        
        # Limpar espaços extras
        columns = [col.strip() for col in columns]
        
        # Montar HTML do rodapé baseado no número de colunas
        if len(columns) == 2:
            footer_html = f"""
            <div class="report-footer">
                <div class="footer-grid-2col">
                    <div class="footer-left">{columns[0]}</div>
                    <div class="footer-right">{columns[1]}</div>
                </div>
            </div>
            """
        elif len(columns) == 3:
            footer_html = f"""
            <div class="report-footer">
                <div class="footer-grid-3col">
                    <div class="footer-left">{columns[0]}</div>
                    <div class="footer-center">{columns[1]}</div>
                    <div class="footer-right">{columns[2]}</div>
                </div>
            </div>
            """
        else:
            footer_html = f"""
            <div class="report-footer">
                <div class="footer-single">{columns[0] if columns else ''}</div>
            </div>
            """
        
        return footer_html
    
    def _build_html_template(self):
        """
        Sobrescreve o método da classe base para usar margens do modelo
        sem adicionar offset de cabeçalho/rodapé
        """
        # Usar margens do modelo ao invés de offsets
        margin_top = 5
        margin_bottom = 5
        margin_left = 20
        margin_right = 15
        
        if self.report_model:
            margins = self.report_model.get('margins', {})
            margin_top = margins.get('top', 5)
            margin_bottom = margins.get('bottom', 5)
            margin_left = margins.get('left', 20)
            margin_right = margins.get('right', 15)
        
        # Importar funções necessárias
        from relatorios.config.visual_identity import (
            COLORS, TYPOGRAPHY, SPACING, BORDERS,
            get_css_variables, generate_section_css, 
            generate_table_css, generate_page_break_css
        )
        
        # CSS base sem offsets de cabeçalho/rodapé
        base_css = f"""
        {self.get_page_css()}
        
        /* Variáveis CSS */
        :root {{
            {get_css_variables()}
        }}
        
        /* Reset e Base */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        @page {{
            size: A4 portrait;
            margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm;
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
        
        /* Conteúdo principal - SEM offset de cabeçalho/rodapé */
        .report-content {{
            margin: 0;
            padding: 0;
        }}
        
        /* Customizações específicas */
        {self.get_custom_styles()}
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
    <div class="report-content">
        {''.join([self._render_section(s) for s in self.sections])}
    </div>
    
    {self.get_footer()}
</body>
</html>
        """
        
        return html
    
    def _render_section(self, section):
        """Renderiza uma seção individual"""
        break_class = ' new-section' if section['break_before'] else ''
        section_class = section['class'].strip()
        
        # Construir classe de forma mais limpa
        classes = ['report-section']
        if section_class:
            classes.append(section_class)
        if section['break_before']:
            classes.append('new-section')
        
        class_attr = ' '.join(classes)
        
        return f"""
    <section class="{class_attr}">
        <h1>{section['title']}</h1>
        <div class="section-content">
            {section['content']}
        </div>
    </section>
        """
    
    # ====================================
    # IMPLEMENTAÇÃO DOS MÉTODOS ABSTRATOS
    # ====================================
    
    def get_report_title(self):
        """Retorna o titulo do relatorio"""
        process = self.data.get('process', {})
        parts = [value for value in (process.get('code'), process.get('name')) if value]
        suffix = ' '.join(parts) if parts else 'Processo'
        return f"Relatório de POP - {suffix}"
    
    def fetch_data(self, **kwargs):
        """
        Busca todos os dados necessários para o relatório
        
        Args:
            company_id: ID da empresa
            process_id: ID do processo
        """
        company_id = kwargs.get('company_id')
        process_id = kwargs.get('process_id')
        
        db = get_db()
        
        # 1. Dados da empresa
        self.data['company'] = db.get_company(company_id) or {}
        
        # 2. Dados do processo
        self.data['process'] = db.get_process(process_id) or {}
        
        # 3. Macroprocesso (se existir)
        macro_id = self.data['process'].get('macro_id')
        if macro_id:
            self.data['macro'] = db.get_macro_process(macro_id) or {}
        
        # 4. Atividades e etapas (se incluído)
        if self.include_activities:
            self.data['activities'] = self._fetch_activities(process_id)
        
        # 5. Rotinas (se incluído)
        if self.include_routines:
            self.data['routines'] = self._fetch_routines(process_id)
        
        # 6. Indicadores (se incluído)
        if self.include_indicators:
            self.data['indicators'] = self._fetch_indicators(process_id)
    
    def _fetch_activities(self, process_id):
        """Busca atividades e suas etapas"""
        db = get_db()
        activities = []
        
        activities_raw = db.list_process_activities(process_id)
        for activity in activities_raw:
            activity_dict = dict(activity)
            
            # Buscar etapas desta atividade
            entries_raw = db.list_process_activity_entries(activity['id'])
            activity_dict['entries'] = [dict(e) for e in entries_raw]
            
            activities.append(activity_dict)
        
        return activities
    
    def _fetch_routines(self, process_id):
        """Busca rotinas com colaboradores"""
        try:
            conn = sqlite3.connect('instance/pevapp22.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar rotinas
            cursor.execute("""
                SELECT r.id, r.name, r.description, r.schedule_type, r.schedule_value,
                       r.deadline_days, r.deadline_hours, r.deadline_date
                FROM routines r
                WHERE r.process_id = ?
                ORDER BY r.created_at DESC
            """, (process_id,))
            
            routines = []
            for routine_row in cursor.fetchall():
                routine = dict(routine_row)
                routine_id = routine['id']
                
                # Buscar colaboradores
                cursor.execute("""
                    SELECT rc.*, e.name as employee_name, e.email as employee_email
                    FROM routine_collaborators rc
                    LEFT JOIN employees e ON rc.employee_id = e.id
                    WHERE rc.routine_id = ?
                    ORDER BY e.name
                """, (routine_id,))
                
                routine['collaborators'] = [dict(row) for row in cursor.fetchall()]
                routine['total_hours'] = sum(c.get('hours_used', 0) for c in routine['collaborators'])
                
                routines.append(routine)
            
            conn.close()
            return routines
            
        except Exception as e:
            print(f"Erro ao buscar rotinas: {e}")
            return []
    
    def _fetch_indicators(self, process_id):
        """Busca indicadores do processo"""
        try:
            conn = sqlite3.connect('instance/pevapp22.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar indicadores
            cursor.execute("""
                SELECT 
                    i.id, i.code, i.name, i.unit, i.formula, 
                    i.polarity, i.data_source, i.notes
                FROM indicators i
                WHERE i.process_id = ?
                ORDER BY i.code
            """, (process_id,))
            
            indicators = [dict(row) for row in cursor.fetchall()]
            
            # Buscar metas de cada indicador
            for indicator in indicators:
                cursor.execute("""
                    SELECT goal_value, goal_date, status
                    FROM indicator_goals
                    WHERE indicator_id = ? AND company_id = (SELECT company_id FROM indicators WHERE id = ?)
                    ORDER BY goal_date DESC
                    LIMIT 1
                """, (indicator['id'], indicator['id']))
                
                goal_row = cursor.fetchone()
                if goal_row:
                    indicator['latest_goal'] = dict(goal_row)
                else:
                    indicator['latest_goal'] = None
            
            conn.close()
            return indicators
            
        except Exception as e:
            print(f"Erro ao buscar indicadores: {e}")
            return []
    
    def _resolve_image_for_inline(self, image_path):
        """
        Resolve caminho de imagem para exibição inline no relatório
        Converte para base64 ou retorna URL acessível
        
        Args:
            image_path: Caminho da imagem
            
        Returns:
            str: Data URL (base64) ou URL HTTP, ou None se não encontrar
        """
        if not image_path:
            return None
        
        # Se já é data URL, retornar direto
        if image_path.startswith('data:image/'):
            return image_path
        
        # Se é URL HTTP, retornar direto
        if image_path.startswith(('http://', 'https://')):
            return image_path
        
        # Tentar encontrar o arquivo localmente
        candidates = [
            Path(image_path),
            Path('uploads') / image_path,
            Path('static') / image_path,
            Path('uploads') / Path(image_path).name,
            Path('static') / Path(image_path).name,
        ]
        
        for candidate in candidates:
            if candidate.is_file():
                # Converter para base64
                ext = candidate.suffix.lower()
                if ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}:
                    mime_type, _ = mimetypes.guess_type(candidate.name)
                    mime_type = mime_type or 'image/png'
                    try:
                        encoded = base64.b64encode(candidate.read_bytes()).decode('ascii')
                        return f"data:{mime_type};base64,{encoded}"
                    except Exception as e:
                        print(f"Erro ao converter imagem {candidate}: {e}")
                        continue
        
        # Se não encontrou, tentar URL relativa
        try:
            from flask import has_request_context, url_for
            if has_request_context():
                try:
                    return url_for('serve_uploaded_file', filename=image_path, _external=False)
                except Exception:
                    pass
        except ImportError:
            pass
        
        # Último recurso: URL relativa simples
        return f"/uploads/{image_path.lstrip('/')}"
    
    def _add_title_and_info_section(self):
        """Adiciona seção de título e informações do processo"""
        process = self.data.get('process', {})
        company = self.data.get('company', {})
        macro = self.data.get('macro', {})
        
        # Título da seção: apenas "Book do Processo"
        section_title = "Book do Processo"
        
        # Nome do processo (vai em uma linha separada no conteúdo)
        process_code = process.get('code', '')
        process_name = process.get('name', 'Processo')
        
        if process_code:
            process_full_name = f"{process_code} - {process_name}"
        else:
            process_full_name = process_name
        
        # Informações do processo
        company_name = company.get('name', 'Não informado')
        
        # Macroprocesso com código
        macro_code = macro.get('code', '')
        macro_name = macro.get('name', 'Não informado')
        macro_owner = macro.get('owner', 'Não informado')
        
        if macro_code:
            macro_full_name = f"{macro_code} - {macro_name}"
        else:
            macro_full_name = macro_name
        
        # Conteúdo: Nome do processo + dados como subsessões
        content_html = f"""
        <div class="book-process-name">{process_full_name}</div>
        <div class="process-info-grid">
            <div class="process-info-row">
                <span class="process-info-label">Empresa:</span>
                <span class="process-info-value">{company_name}</span>
            </div>
            <div class="process-info-row">
                <span class="process-info-label">Macroprocesso:</span>
                <span class="process-info-value">{macro_full_name} | <strong>Dono:</strong> {macro_owner}</span>
            </div>
        </div>
        """
        
        # Adicionar como seção normal com título
        self.add_section(section_title, content_html, section_class='book-section')
    
    def build_sections(self):
        """Constrói todas as seções do relatório"""
        
        # Limpar seções anteriores
        self.clear_sections()
        
        # 0. Seção de Título e Dados do Processo (sempre incluída)
        self._add_title_and_info_section()
        
        # 1. Seção de Fluxo (se incluído)
        if self.include_flow:
            self._add_flow_section()

        # 2. Seção de Atividades (se incluído)
        if self.include_activities:
            self._add_activities_section()

        # 3. Seção de Rotinas (se incluído)
        if self.include_routines:
            self._add_routines_section()

        # 4. Seção de Indicadores (se incluído)
        if self.include_indicators:
            self._add_indicators_section()
    
    # ====================================
    # SEÇÕES ESPECÍFICAS
    # ====================================

    def _add_flow_section(self):
        """Adiciona secao de fluxograma"""
        process = self.data.get('process', {})
        flow_document = (process.get('flow_document') or '').strip()

        def _build_public_url(document_path: str) -> str | None:
            if not document_path:
                return None

            lowered = document_path.lower()
            if lowered.startswith(('http://', 'https://', '/')):
                return document_path

            try:
                from flask import has_request_context, url_for

                if has_request_context():
                    try:
                        return url_for('serve_uploaded_file', filename=document_path, _external=False)
                    except Exception:
                        pass
            except ImportError:
                pass

            return f"/uploads/{document_path.lstrip('/')}"

        def _resolve_image_source(document_path: str) -> tuple[str | None, str | None]:
            if not document_path:
                return (None, None)

            lowered = document_path.lower()

            if lowered.startswith('data:image/'):
                return ('image', document_path)

            if lowered.startswith(('http://', 'https://')):
                ext = Path(document_path).suffix.lower()
                if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}:
                    return ('image', document_path)
                return ('file', document_path)

            candidates = []
            path_obj = Path(document_path)
            if path_obj.is_file():
                candidates.append(path_obj)
            else:
                candidates.extend([
                    Path(document_path.lstrip('/')),
                    Path('static') / document_path.lstrip('/'),
                    Path('uploads') / path_obj.name
                ])

            file_path = next((p for p in candidates if p.is_file()), None)
            if file_path:
                ext = file_path.suffix.lower()
                if ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}:
                    mime_type, _ = mimetypes.guess_type(file_path.name)
                    mime_type = mime_type or 'image/png'
                    try:
                        encoded = base64.b64encode(file_path.read_bytes()).decode('ascii')
                        return ('image', f"data:{mime_type};base64,{encoded}")
                    except OSError:
                        pass
            url = _build_public_url(document_path)
            return ('file', url)

        src_kind, src_value = _resolve_image_source(flow_document)

        # Sempre exibir como imagem inline
        if src_value:
            # Se retornou 'file', usar o URL como src da imagem mesmo assim
            caption = process.get('name') or 'Fluxograma do Processo'
            content = (
                "<figure class='flow-figure'>"
                f"<img src='{src_value}' alt='Fluxograma do processo' class='flow-figure-image'/>"
                f"<figcaption class='flow-figure-caption'>{caption}</figcaption>"
                "</figure>"
            )
        else:
            content = (
                "<div class='warning-callout'>"
                "<strong>Fluxograma não cadastrado:</strong> ainda não há diagrama anexado para este processo."
                "</div>"
            )

        self.add_section('Fluxo do Processo', content)

    def _add_activities_section(self):
        """Adiciona seção de atividades e etapas"""
        activities = self.data.get('activities', [])

        if not activities:
            content = (
                "<div class='info-callout'>"
                "Nenhuma atividade foi cadastrada para este processo até o momento."
                "</div>"
            )
            self.add_section('Procedimento Operacional', content)
            return

        parts = ["<div class='activity-list'>"]
        for index, activity in enumerate(activities, 1):
            entries = activity.get('entries', [])
            meta_badges = []
            if activity.get('responsible'):
                meta_badges.append(f"<span>Responsável: {activity['responsible']}</span>")
            if activity.get('duration'):
                meta_badges.append(f"<span>Duração média: {activity['duration']}</span>")

            block = [
                "<div class='activity-card'>",
                f"<h3>{index}. {activity.get('name') or 'Atividade sem nome'}</h3>",
            ]

            if meta_badges:
                block.append(f"<div class='activity-meta'>{' '.join(meta_badges)}</div>")

            if activity.get('description'):
                block.append(f"<div class='activity-description'>{activity['description']}</div>")

            if entries:
                block.append("<div class='step-list'>")
                for step_index, entry in enumerate(entries, 1):
                    # Pegar texto
                    step_text = entry.get('text_content') or entry.get('content') or entry.get('description') or '-'
                    
                    # Pegar imagem (se existir)
                    image_path = entry.get('image_path', '').strip()
                    image_width = entry.get('image_width', 280)  # Largura configurada
                    
                    # Classe CSS baseada em ter ou não imagem
                    step_class = 'step-text' if image_path else 'step-text text-only'
                    
                    step_html = f"<div class='step-item'><span class='step-badge'>Passo {step_index}</span><div class='{step_class}'>"
                    
                    # Adicionar texto
                    step_html += f"<div class='step-text-content'>{step_text}</div>"
                    
                    # Adicionar imagem se existir (com largura configurada)
                    if image_path:
                        image_src = self._resolve_image_for_inline(image_path)
                        if image_src:
                            step_html += f"<img src='{image_src}' alt='Passo {step_index}' class='step-image' style='width: {image_width}px;'/>"
                    
                    step_html += "</div></div>"
                    block.append(step_html)
                    
                block.append("</div>")
            else:
                block.append("<div class='info-callout'>Etapas ainda não detalhadas.</div>")

            block.append("</div>")
            parts.extend(block)

        parts.append("</div>")
        content = '\n'.join(parts)
        self.add_section('Procedimento Operacional', content)

    def _add_routines_section(self):
        """Adiciona seção de rotinas"""
        routines = self.data.get('routines', [])

        if not routines:
            content = (
                "<div class='info-callout'>"
                "Nenhuma rotina foi vinculada a este processo até o momento."
                "</div>"
            )
            self.add_section('Rotinas Associadas', content)
            return

        # Labels de periodicidade
        schedule_labels = {
            'daily': 'Diário',
            'weekly': 'Semanal',
            'monthly': 'Mensal',
            'quarterly': 'Trimestral',
            'yearly': 'Anual',
            'specific': 'Data específica',
            None: 'Não definido',
            '': 'Não definido'
        }
        
        # Construir tabela única com todas as rotinas
        table_rows = []
        
        for routine in routines:
            # Periodicidade
            periodicidade = schedule_labels.get(routine.get('schedule_type'), 'Não definido')
            
            # Agendamento (exemplo: "Todo dia 05", "Toda segunda", etc)
            schedule_value = routine.get('schedule_value', '')
            if routine.get('schedule_type') == 'monthly' and schedule_value:
                agendamento = f"Todo dia {schedule_value}"
            elif routine.get('schedule_type') == 'weekly' and schedule_value:
                dias_semana = {
                    '1': 'segunda-feira', '2': 'terça-feira', '3': 'quarta-feira',
                    '4': 'quinta-feira', '5': 'sexta-feira', '6': 'sábado', '0': 'domingo'
                }
                agendamento = f"Toda {dias_semana.get(schedule_value, schedule_value)}"
            elif routine.get('schedule_type') == 'specific' and routine.get('deadline_date'):
                agendamento = f"Em {routine.get('deadline_date')}"
            else:
                agendamento = schedule_value or '-'
            
            # Mão de Obra Total
            collaborators = routine.get('collaborators', [])
            total_hours = routine.get('total_hours') or 0
            num_collaborators = len(collaborators)
            
            if num_collaborators > 0:
                mao_obra = f"{total_hours} horas ({num_collaborators:02d} colaborador{'es' if num_collaborators > 1 else ''})"
            else:
                mao_obra = "Não definido"
            
            # Observações (descrição da rotina)
            obs = routine.get('description') or '-'
            
            # Adicionar linha à tabela
            table_rows.append(f"""
                <tr>
                    <td>{periodicidade}</td>
                    <td>{agendamento}</td>
                    <td class="text-center">{mao_obra}</td>
                    <td>{obs}</td>
                </tr>
            """)
        
        # Montar tabela HTML
        content = f"""
        <table class='routines-table'>
            <thead>
                <tr>
                    <th style="width: 15%;">Periodicidade</th>
                    <th style="width: 20%;">Agendamento</th>
                    <th style="width: 25%;">Mão de Obra Total Consumida</th>
                    <th style="width: 40%;">Obs</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
        
        self.add_section('Rotinas Associadas', content)

    def _add_indicators_section(self):
        """Adiciona seção de indicadores"""
        indicators = self.data.get('indicators', [])

        if not indicators:
            content = (
                "<div class='info-callout'>"
                "O acompanhamento de indicadores para este processo ainda não foi configurado."
                "</div>"
            )
            self.add_section('Indicadores de Desempenho', content, section_class='indicators-section')
            return
        
        # Construir tabela com os indicadores
        table_rows = []
        
        for indicator in indicators:
            # Código e Nome
            code = indicator.get('code', '-')
            name = indicator.get('name', 'Sem nome')
            
            # Unidade
            unit = indicator.get('unit', '-')
            
            # Fórmula
            formula = indicator.get('formula', '-')
            
            # Polaridade (traduzir)
            polarity = indicator.get('polarity', '')
            polarity_label = {
                'positive': '↑ Maior melhor',
                'negative': '↓ Menor melhor',
                'neutral': '- Neutro',
                '': '-'
            }.get(polarity, polarity)
            
            # Meta atual
            latest_goal = indicator.get('latest_goal')
            if latest_goal:
                goal_value = latest_goal.get('goal_value', '-')
                goal_date = latest_goal.get('goal_date', '-')
                meta_info = f"{goal_value} {unit} até {goal_date}"
            else:
                meta_info = "Sem meta definida"
            
            # Adicionar linha à tabela
            table_rows.append(f"""
                <tr>
                    <td><strong>{code}</strong><br/><small>{name}</small></td>
                    <td class="text-center">{unit}</td>
                    <td>{formula}</td>
                    <td class="text-center">{polarity_label}</td>
                    <td>{meta_info}</td>
                </tr>
            """)
        
        # Montar tabela HTML
        content = f"""
        <table class='indicators-table'>
            <thead>
                <tr>
                    <th style="width: 25%;">Indicador</th>
                    <th style="width: 10%;">Unidade</th>
                    <th style="width: 25%;">Fórmula</th>
                    <th style="width: 15%;">Polaridade</th>
                    <th style="width: 25%;">Meta Atual</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
        
        self.add_section('Indicadores de Desempenho', content, section_class='indicators-section')

    # ====================================
    # CONFIGURAÇÃO RÁPIDA
    # ====================================
    
    def configure(self, flow=True, activities=True, routines=True, indicators=False):
        """
        Configura quais seções incluir
        
        Args:
            flow: Incluir fluxograma
            activities: Incluir atividades
            routines: Incluir rotinas
            indicators: Incluir indicadores
        """
        self.include_flow = flow
        self.include_activities = activities
        self.include_routines = routines
        self.include_indicators = indicators
    
    def generate_html(self, **kwargs):
        """Gera o HTML completo usando a estrutura base."""
        return super().generate_html(**kwargs)


# ====================================
# FUNÇÃO DE CONVENIÊNCIA
# ====================================

def generate_process_pop_report(
    company_id: int,
    process_id: int,
    *,
    save_path: str | None = None,
    model_id: int | None = 7,
    flow: bool = True,
    activities: bool = True,
    routines: bool = True,
    indicators: bool = False,
) -> str:
    """Gera rapidamente o relatório de POP para um processo."""
    report = ProcessPOPReport(report_model_id=model_id)
    report.configure(
        flow=flow,
        activities=activities,
        routines=routines,
        indicators=indicators,
    )
    html = report.generate_html(company_id=company_id, process_id=process_id)

    if save_path:
        with open(save_path, 'w', encoding='utf-8') as handler:
            handler.write(html)

    return html


# ====================================
# EXEMPLO DE USO (EXECUÇÃO DIRETA)
# ====================================

if __name__ == '__main__':  # pragma: no cover
    print('Gerando exemplos de relatório...')

    html_full = generate_process_pop_report(
        company_id=6,
        process_id=123,
        save_path='relatorio_processo_123.html',
    )
    print(f'Relatório completo gerado ({len(html_full)} caracteres)')

    html_custom = generate_process_pop_report(
        company_id=6,
        process_id=456,
        routines=False,
        save_path='relatorio_processo_456.html',
    )
    print(f'Relatório customizado gerado ({len(html_custom)} caracteres)')
