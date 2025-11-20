#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identidade Visual Padrão para Relatórios
Sistema PEVAPP22

Este arquivo define as cores, fontes, espaçamentos e estilos padrão
que serão aplicados em todos os relatórios, a menos que sejam
sobrescritos em um gerador específico.
"""

# ===============================================
# CORES PADRÃO
# ===============================================

COLORS = {
    # Cores primárias
    "primary": "#1a76ff",  # Azul principal
    "secondary": "#6366f1",  # Roxo secundário
    "accent": "#f59e0b",  # Laranja destaque
    # Cores de texto
    "text_dark": "#0f172a",  # Texto escuro
    "text_medium": "#475569",  # Texto médio
    "text_light": "#64748b",  # Texto claro
    "text_muted": "#94a3b8",  # Texto esmaecido
    # Cores de fundo
    "bg_white": "#ffffff",
    "bg_light": "#f8fafc",
    "bg_medium": "#f1f5f9",
    "bg_dark": "#e2e8f0",
    # Cores de borda
    "border_light": "#e2e8f0",
    "border_medium": "#cbd5e1",
    "border_dark": "#94a3b8",
    # Cores de status
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
    # Cores para gráficos
    "chart_1": "#3b82f6",
    "chart_2": "#8b5cf6",
    "chart_3": "#ec4899",
    "chart_4": "#f59e0b",
    "chart_5": "#10b981",
    "chart_6": "#06b6d4",
}

# ===============================================
# TIPOGRAFIA
# ===============================================

TYPOGRAPHY = {
    # Famílias de fonte
    "font_family_primary": "Arial, Helvetica, sans-serif",
    "font_family_secondary": '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    "font_family_mono": 'Consolas, "Courier New", monospace',
    # Tamanhos de fonte (em pt para impressão)
    "font_size_h1": "18pt",
    "font_size_h2": "15pt",
    "font_size_h3": "13pt",
    "font_size_h4": "11pt",
    "font_size_body": "10pt",
    "font_size_small": "9pt",
    "font_size_tiny": "8pt",
    # Pesos de fonte
    "font_weight_normal": "400",
    "font_weight_medium": "500",
    "font_weight_semibold": "600",
    "font_weight_bold": "700",
    # Altura de linha
    "line_height_tight": "1.25",
    "line_height_normal": "1.5",
    "line_height_relaxed": "1.75",
}

# ===============================================
# ESPAÇAMENTOS (em mm)
# ===============================================

SPACING = {
    # Margens de página padrão
    "page_margin_top": 25,
    "page_margin_right": 20,
    "page_margin_bottom": 20,
    "page_margin_left": 20,
    # Alturas de cabeçalho e rodapé
    "header_height": 25,
    "footer_height": 15,
    # Espaçamentos entre elementos
    "space_xs": "4mm",
    "space_sm": "8mm",
    "space_md": "12mm",
    "space_lg": "16mm",
    "space_xl": "24mm",
    # Padding interno
    "padding_xs": "2mm",
    "padding_sm": "4mm",
    "padding_md": "6mm",
    "padding_lg": "8mm",
}

# ===============================================
# BORDAS E ARREDONDAMENTOS
# ===============================================

BORDERS = {
    "radius_sm": "4px",
    "radius_md": "6px",
    "radius_lg": "8px",
    "radius_xl": "12px",
    "width_thin": "1px",
    "width_medium": "2px",
    "width_thick": "3px",
}

# ===============================================
# CONFIGURAÇÕES DE TABELAS
# ===============================================

TABLE_STYLES = {
    "header_bg": COLORS["primary"],
    "header_color": COLORS["bg_white"],
    "row_even_bg": COLORS["bg_white"],
    "row_odd_bg": COLORS["bg_light"],
    "border_color": COLORS["border_medium"],
    "padding": "6px 10px",
    "font_size": TYPOGRAPHY["font_size_small"],
}

# ===============================================
# CONFIGURAÇÕES DE SEÇÕES
# ===============================================

SECTION_STYLES = {
    # Título de seção principal
    "h1": {
        "font_size": TYPOGRAPHY["font_size_h1"],
        "font_weight": TYPOGRAPHY["font_weight_bold"],
        "color": COLORS["text_dark"],
        "margin_top": SPACING["space_lg"],
        "margin_bottom": "5mm",  # Espaçamento otimizado para 5mm
        "border_bottom": f"{BORDERS['width_medium']} solid {COLORS['primary']}",
        "padding_bottom": SPACING["padding_sm"],
    },
    # Título de subseção
    "h2": {
        "font_size": TYPOGRAPHY["font_size_h2"],
        "font_weight": TYPOGRAPHY["font_weight_semibold"],
        "color": COLORS["text_dark"],
        "margin_top": SPACING["space_md"],
        "margin_bottom": SPACING["space_sm"],
    },
    # Título de sub-subseção
    "h3": {
        "font_size": TYPOGRAPHY["font_size_h3"],
        "font_weight": TYPOGRAPHY["font_weight_medium"],
        "color": COLORS["text_medium"],
        "margin_top": SPACING["space_sm"],
        "margin_bottom": SPACING["padding_md"],
    },
}

# ===============================================
# REGRAS DE QUEBRA DE PÁGINA
# ===============================================

PAGE_BREAK_RULES = {
    "avoid_break_inside": [
        ".section-content",
        ".table-row",
        ".activity-block",
        ".routine-item",
        ".chart-container",
    ],
    "force_break_before": [
        # Removido '.new-section' - não queremos forçar quebra antes de novas seções
        # Isso permite que seções continuem naturalmente na mesma página
    ],
    "keep_with_next": [
        "h1",
        "h2",
        "h3",
    ],
}

# ===============================================
# CONFIGURAÇÕES DE IMPRESSÃO
# ===============================================

PRINT_CONFIG = {
    "paper_size": "A4",
    "orientation": "portrait",  # 'portrait' ou 'landscape'
    "print_background": True,
    "print_colors": True,
}

# ===============================================
# FUNÇÕES AUXILIARES
# ===============================================


def get_css_variables():
    """
    Retorna todas as variáveis CSS para uso nos templates
    """
    css_vars = []

    # Cores
    for key, value in COLORS.items():
        css_vars.append(f"--color-{key.replace('_', '-')}: {value};")

    # Tipografia
    for key, value in TYPOGRAPHY.items():
        css_vars.append(f"--{key.replace('_', '-')}: {value};")

    # Espaçamentos
    for key, value in SPACING.items():
        if isinstance(value, (int, float)):
            css_vars.append(f"--{key.replace('_', '-')}: {value}mm;")
        else:
            css_vars.append(f"--{key.replace('_', '-')}: {value};")

    # Bordas
    for key, value in BORDERS.items():
        css_vars.append(f"--border-{key.replace('_', '-')}: {value};")

    return "\n    ".join(css_vars)


def generate_page_style(model=None):
    """
    Gera o estilo @page baseado no modelo ou configuração padrão

    Args:
        model: Dicionário com configurações do modelo (opcional)

    Returns:
        str: CSS da regra @page
    """
    if model:
        # Extrair margens do modelo (campos separados)
        margin_top = model.get("margin_top", PRINT_CONFIG.get("margin_top", 20))
        margin_right = model.get("margin_right", PRINT_CONFIG.get("margin_right", 15))
        margin_bottom = model.get(
            "margin_bottom", PRINT_CONFIG.get("margin_bottom", 15)
        )
        margin_left = model.get("margin_left", PRINT_CONFIG.get("margin_left", 20))

        return f"""
    @page {{
        size: {model.get('paper_size', PRINT_CONFIG['paper_size'])};
        {f"size: {model['paper_size']} landscape;" if model.get('orientation') == 'Paisagem' else ''}
        margin: {margin_top}mm 
                {margin_right}mm 
                {margin_bottom}mm 
                {margin_left}mm;
    }}
    """
    else:
        return f"""
    @page {{
        size: {PRINT_CONFIG['paper_size']};
        margin: {SPACING['page_margin_top']}mm 
                {SPACING['page_margin_right']}mm 
                {SPACING['page_margin_bottom']}mm 
                {SPACING['page_margin_left']}mm;
    }}
    """


def generate_section_css():
    """
    Gera CSS para títulos de seção
    """
    css = []
    for tag, styles in SECTION_STYLES.items():
        rules = [f"{k.replace('_', '-')}: {v}" for k, v in styles.items()]
        css.append(f"{tag} {{ {'; '.join(rules)}; }}")

    return "\n    ".join(css)


def generate_table_css():
    """
    Gera CSS para tabelas
    """
    return f"""
    table.data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: {TABLE_STYLES['font_size']};
        margin: {SPACING['space_sm']} 0;
    }}
    
    table.data-table th {{
        background: {TABLE_STYLES['header_bg']};
        color: {TABLE_STYLES['header_color']};
        padding: {TABLE_STYLES['padding']};
        text-align: left;
        font-weight: {TYPOGRAPHY['font_weight_semibold']};
        border: {BORDERS['width_thin']} solid {TABLE_STYLES['border_color']};
    }}
    
    table.data-table td {{
        padding: {TABLE_STYLES['padding']};
        border: {BORDERS['width_thin']} solid {TABLE_STYLES['border_color']};
    }}
    
    table.data-table tr:nth-child(even) {{
        background: {TABLE_STYLES['row_even_bg']};
    }}
    
    table.data-table tr:nth-child(odd) {{
        background: {TABLE_STYLES['row_odd_bg']};
    }}
    """


def generate_page_break_css():
    """
    Gera CSS para regras de quebra de página
    """
    css = []

    # Evitar quebra dentro destes elementos
    for selector in PAGE_BREAK_RULES["avoid_break_inside"]:
        css.append(f"{selector} {{ page-break-inside: avoid; }}")

    # Forçar quebra antes destes elementos
    for selector in PAGE_BREAK_RULES["force_break_before"]:
        css.append(f"{selector} {{ page-break-before: always; }}")

    # Manter junto com próximo elemento
    for selector in PAGE_BREAK_RULES["keep_with_next"]:
        css.append(f"{selector} {{ page-break-after: avoid; }}")

    # Regras específicas para manter título e conteúdo juntos
    css.append(
        "h1 + * { page-break-before: avoid !important; break-before: avoid !important; }"
    )
    css.append(
        ".report-section { page-break-inside: avoid !important; break-inside: avoid !important; }"
    )
    css.append(
        "h1 { orphans: 3; widows: 3; page-break-after: avoid !important; break-after: avoid !important; }"
    )
    css.append(
        ".section-content { orphans: 2; widows: 2; page-break-before: avoid !important; break-before: avoid !important; }"
    )
    css.append(
        ".report-section h1 + .section-content { page-break-before: avoid !important; break-before: avoid !important; }"
    )

    return "\n    ".join(css)


# ===============================================
# EXPORTAR TUDO
# ===============================================

__all__ = [
    "COLORS",
    "TYPOGRAPHY",
    "SPACING",
    "BORDERS",
    "TABLE_STYLES",
    "SECTION_STYLES",
    "PAGE_BREAK_RULES",
    "PRINT_CONFIG",
    "get_css_variables",
    "generate_page_style",
    "generate_section_css",
    "generate_table_css",
    "generate_page_break_css",
]
