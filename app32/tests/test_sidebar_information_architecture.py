import html as html_module
import os

from flask import Flask, render_template_string, session
from werkzeug.routing import BuildError


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.secret_key = "test"

    def _safe_url_for(endpoint, **values):
        try:
            from flask import url_for as flask_url_for

            return flask_url_for(endpoint, **values)
        except BuildError:
            return f"/{endpoint.replace('.', '/')}"

    app.jinja_env.globals["url_for"] = _safe_url_for
    app.jinja_env.globals["has_permission"] = lambda *args, **kwargs: True
    app.jinja_env.globals["is_platform_admin"] = lambda *args, **kwargs: True
    app.jinja_env.globals["current_user"] = type(
        "User", (), {"is_authenticated": True, "name": "Teste"}
    )()
    return app


def _render(path="/portal"):
    app = _build_app()
    with app.test_request_context(path):
        session["active_company_id"] = 9
        return html_module.unescape(
            render_template_string('{% include "partials/sidebar_standard.html" %}')
        )


def test_sidebar_preserves_quick_access_and_applies_approved_macro_order():
    rendered = _render()

    quick_access = rendered.index("Acesso Rápido")
    consultive = rendered.index("Consultivo", quick_access)
    planning = rendered.index("Planejamento Estratégico", consultive)
    strategic = rendered.index("Gestão Estratégica", planning)
    commercial = rendered.index("Gestão Comercial", strategic)
    financial = rendered.index("Gestão Financeira", commercial)
    sapiens = rendered.index("Sapiens", financial)
    system = rendered.index("Sistema", sapiens)
    profile = rendered.index("Meu Perfil", system)

    assert quick_access < consultive < planning < strategic < commercial < financial < sapiens < system < profile
    for expected in [
        "Portal",
        "Meu Trabalho",
        "Calendário",
        "Portal de Processos",
        "Painel de Gestão Estratégica",
    ]:
        assert expected in rendered[:planning]


def test_sidebar_preserves_consultive_submenus():
    rendered = _render("/consultive/cockpit")

    assert "Cockpit do Consultor" in rendered
    assert 'href="/consultive/cockpit"' in rendered
    assert "Jornada do Cliente" in rendered
    assert 'href="/structuring-journey/client"' in rendered
    assert "Protocolos Consultivos" in rendered
    assert 'href="/consultive/protocols"' in rendered


def test_sidebar_visually_separates_quick_access_from_remaining_menus():
    rendered = _render()

    quick_access_end = rendered.index("Painel de Gestão Estratégica")
    separator = rendered.index('class="sidebar-menu-separator"', quick_access_end)
    consultive = rendered.index("Consultivo", separator)

    assert quick_access_end < separator < consultive
    assert 'role="separator"' in rendered
    assert 'aria-label="Demais menus"' in rendered
    assert "<span>Menus</span>" in rendered


def test_sidebar_defines_responsive_widths_and_mobile_touch_targets():
    rendered = _render()

    assert "@media (max-width: 768px)" in rendered
    assert "width: min(320px, calc(100vw - 2.5rem));" in rendered
    assert "min-height: 44px;" in rendered
    assert "@media (max-width: 520px)" in rendered
    assert "width: min(var(--sidebar-width), calc(100vw - 2rem));" in rendered
    assert "overflow-wrap: anywhere;" in rendered


def test_sidebar_planning_and_strategic_groups_expose_approved_entries():
    rendered = _render("/companies/9/identity?section=organograma")

    for expected in [
        "Identidade Organizacional",
        "Organograma",
        "Planos Estratégicos",
        "Gestão de Processos",
        "Gestão de Projetos",
        "Gestão de Reuniões",
        "Gestão de Ocorrências",
        "Calendário e Jornadas",
        "Gestão de Indicadores",
        "Gestão de Incentivos",
        "Teia de Conexões",
        "Auditoria Interna",
    ]:
        assert expected in rendered

    assert 'href="/companies/9/identity"' in rendered
    assert 'href="/companies/9/identity?section=organograma#organograma"' in rendered
    assert "Execução" in rendered
    assert "Desempenho" in rendered
    assert "Governança" in rendered


def test_discontinued_real_estate_auctions_are_not_exposed():
    rendered = _render("/portal")

    assert "Leilões Imobiliários" not in rendered
    assert "/real-estate-auctions" not in rendered
