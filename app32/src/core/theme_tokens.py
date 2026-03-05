"""
Tokens centrais de tema / identidade visual do Gestão Versus.

Objetivo:
- Evitar hardcode de paleta espalhado em serviços/templates.
- Permitir evolução consistente do visual (web, e-mail e relatórios).
"""

from __future__ import annotations

from copy import deepcopy


# Paleta aplicada ao template de resumo diário por e-mail (Sapiens).
SUMMARY_EMAIL_THEME = {
    "page_bg": "#f2faf7",
    "header_gradient": "linear-gradient(135deg,#050505 0%,#0f172a 55%,#0f766e 100%)",
    "card_bg": "#ffffff",
    "card_border": "#cceee4",
    "signature_accent": "#0f766e",
    "text_primary": "#0f172a",
    "text_secondary": "#334155",
    "text_muted": "#64748b",
    "summary_chip_bg": "#ecfdf5",
    "summary_chip_border": "#0f766e",
    "summary_chip_text": "#065f46",
    "company_box_bg": "#f6fffb",
    "company_box_border": "#cceee4",
    "company_box_border_accent": "#0f766e",
    "company_box_label": "#065f46",
    "item_bg_soft": "#f6fffb",
    "warning_bg": "#fffbeb",
    "warning_border": "#f59e0b",
    "warning_text": "#92400e",
}


SUMMARY_EMAIL_SECTION_STYLES = {
    "projetos": {
        "label": "Projetos",
        "color": "#0f766e",
        "bg": "#ecfdf5",
        "icon": "📁",
    },
    "processos": {
        "label": "Processos",
        "color": "#166534",
        "bg": "#f0fdf4",
        "icon": "⚙️",
    },
    "reunioes": {
        "label": "Reuniões",
        "color": "#115e59",
        "bg": "#f0fdfa",
        "icon": "🤝",
    },
}


def get_summary_email_theme() -> dict:
    """Retorna cópia dos tokens de tema do e-mail."""
    return dict(SUMMARY_EMAIL_THEME)


def get_summary_email_section_styles() -> dict:
    """Retorna cópia profunda dos estilos de seção do e-mail."""
    return deepcopy(SUMMARY_EMAIL_SECTION_STYLES)


def get_web_theme_tokens() -> dict:
    """
    Bridge dos tokens para o frontend web (Jinja/CSS vars).
    Mantém o web alinhado à mesma base visual usada no e-mail.
    """
    base = get_summary_email_theme()
    return {
        "page_bg": base["page_bg"],
        "surface_bg": base["card_bg"],
        "border": base["card_border"],
        "accent": base["signature_accent"],
        "accent_dark": base["summary_chip_text"],
        "accent_soft_bg": base["summary_chip_bg"],
        "text_primary": base["text_primary"],
        "text_secondary": base["text_secondary"],
        "text_muted": base["text_muted"],
        "header_gradient": base["header_gradient"],
    }
