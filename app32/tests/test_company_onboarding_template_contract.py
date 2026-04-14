import html as html_module
import os
import sys
from pathlib import Path

from flask import Flask, render_template_string, url_for as flask_url_for
from werkzeug.routing import BuildError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static')),
    )

    def _safe_url_for(endpoint, **values):
        try:
            return flask_url_for(endpoint, **values)
        except BuildError:
            return f'/{endpoint.replace(".", "/")}'

    app.jinja_env.globals['url_for'] = _safe_url_for
    app.jinja_env.globals['has_permission'] = lambda *args, **kwargs: True
    app.jinja_env.globals['is_platform_admin'] = lambda *args, **kwargs: True
    app.jinja_env.globals['current_user'] = type('User', (), {'is_authenticated': True, 'name': 'Teste'})()
    return app


def _fake_onboarding(mode='create'):
    return {
        'mode': mode,
        'active_tab': 'dados',
        'header': {
            'title': 'Crie uma nova empresa' if mode == 'create' else 'Ajuste a empresa existente',
            'subtitle': 'Wizard guiado para criar ou alterar empresas sem perder o contexto de rotina, estratégia, finanças, Sapiens e API / MCP.',
            'mode_badge': 'Criação guiada' if mode == 'create' else 'Alteração assistida',
        },
        'steps': [
            {'id': 'dados', 'number': 1, 'title': 'Quem é a empresa?', 'description': 'Nome, código, propósito e identidade.', 'status': 'available'},
            {'id': 'economico', 'number': 2, 'title': 'Contexto', 'description': 'CNPJ, segmento, porte e cidade.', 'status': 'after_create' if mode == 'create' else 'available'},
            {'id': 'config', 'number': 7, 'title': 'API / MCP', 'description': 'Logo, ativação e preparo da unidade.', 'status': 'after_create' if mode == 'create' else 'available'},
        ],
        'domain_tracks': [
            {'title': 'Rotina', 'summary': 'Time, cargos, acessos e operação do dia a dia.', 'create_tab': 'cargos', 'update_tab': 'colaboradores'},
            {'title': 'Estratégico', 'summary': 'Missão, visão e leitura executiva.', 'create_tab': 'dados', 'update_tab': 'economico'},
            {'title': 'Financeiro', 'summary': 'Contexto econômico e preparo para análises.', 'create_tab': 'economico', 'update_tab': 'economico'},
            {'title': 'Sapiens / IA / API / MCP', 'summary': 'API / MCP, canais e readiness.', 'create_tab': 'config', 'update_tab': 'config'},
        ],
        'context_panel': {
            'title': 'Quem é a empresa?',
            'body': 'Comece pela identidade antes de seguir para as demais etapas.',
            'items': ['Preencha razão social, código e propósito.', 'Salve antes de abrir API / MCP.'],
        },
        'compact_guidance': {
            'title': 'Faça isso agora',
            'body': 'Preencha identidade e siga para o próximo passo.',
            'primary_label': 'Salvar e continuar',
            'primary_action': 'save',
            'secondary_label': 'Próxima etapa: Contexto',
            'secondary_target': 'economico',
        },
        'focus_lane': {
            'question': 'Você já preencheu quem é a empresa e o código dela?',
            'confirm_label': 'Sim, ir para Contexto',
            'confirm_target': 'economico',
            'skip_label': 'Ainda estou preenchendo',
        },
        'mode_selector': [
            {'id': 'create', 'label': 'Criar nova', 'description': 'Começar do zero.', 'target': 'dados'},
            {'id': 'update', 'label': 'Alterar existente', 'description': 'Ajustar sem se perder.', 'target': 'dados'},
            {'id': 'configure', 'label': 'Configurar API / MCP', 'description': 'Ir direto ao sistema e canais.', 'target': 'config'},
            {'id': 'test', 'label': 'Preparar teste', 'description': 'Fechar o setup para uso controlado.', 'target': 'config'},
        ],
        'compact_guidance': {
            'title': 'Faça isso agora',
            'body': 'Preencha identidade e siga para o próximo passo.',
            'primary_label': 'Salvar e continuar',
            'primary_action': 'save',
            'secondary_label': 'Próxima etapa: Contexto',
            'secondary_target': 'economico',
        },
        'focus_lane': {
            'question': 'Você já preencheu quem é a empresa e o código dela?',
            'confirm_label': 'Sim, ir para Contexto',
            'confirm_target': 'economico',
            'skip_label': 'Ainda estou preenchendo',
        },
        'mode_selector': [
            {'id': 'create', 'label': 'Criar nova', 'description': 'Começar do zero.', 'target': 'dados'},
            {'id': 'update', 'label': 'Alterar existente', 'description': 'Ajustar sem se perder.', 'target': 'dados'},
            {'id': 'configure', 'label': 'Configurar API / MCP', 'description': 'Ir direto ao sistema e canais.', 'target': 'config'},
            {'id': 'test', 'label': 'Preparar teste', 'description': 'Fechar o setup para uso controlado.', 'target': 'config'},
        ],
        'checklist': ['Salvar identidade da empresa.', 'Configurar API / MCP e validar readiness básica.'],
        'quick_links': [
            {'title': 'API / MCP', 'description': 'Governança e readiness.', 'href': '/api-mcp'},
            {'title': 'Sapiens', 'description': 'Runtime conversacional.', 'href': '/sapiens'},
        ],
    }


def test_company_onboarding_template_renders_guided_wizard_and_new_spectrum():
    app = _build_app()
    app.secret_key = 'test'

    with app.test_request_context('/companies/new'):
        rendered_html = render_template_string(
            '{% extends "modules/companies/company_form_v2.html" %}{% block sidebar_left %}{% endblock %}',
            company_id=None,
            active_tab='dados',
            onboarding=_fake_onboarding('create'),
        )

    html = html_module.unescape(rendered_html)

    for expected in [
        'Onboarding guiado de empresas',
        'Crie uma nova empresa',
        'Criação guiada',
        'Quem é a empresa?',
        'Contexto',
            'API / MCP',
        'Criar empresa e continuar',
        'Começar pelo básico',
            'Ir para API / MCP',
        'Escolha rápida',
        'Criar nova',
        'Alterar existente',
            'Configurar API / MCP',
        'Preparar teste',
        'Modo assistido',
        'Você já preencheu quem é a empresa e o código dela?',
        'Ainda estou preenchendo',
        'Mostrar opções avançadas',
        'Próximo passo',
        'Salvar e continuar',
        'Próxima etapa: Contexto',
        'Checklist do modo atual',
        'Espectro coberto',
        'Rotina',
        'Estratégico',
        'Financeiro',
            'Sapiens / IA / API / MCP',
            'API / MCP',
        'Sapiens',
        'Vincular Novo',
        'Salvar Configurações do Sistema',
    ]:
        assert expected in html

    assert 'data-onboarding-step="dados"' in html
    assert 'data-onboarding-step="config"' in html
    assert 'data-status="after_create"' in html
    assert 'data-wizard-goto="config"' in html
    assert 'id="companyAdvancedActions"' in html
    assert 'id="companyAdvancedSide"' in html
    assert '/api-mcp' in html


def test_company_onboarding_template_renders_edit_mode_language():
    app = _build_app()
    app.secret_key = 'test'

    with app.test_request_context('/companies/31/edit?tab=config'):
        rendered_html = render_template_string(
            '{% extends "modules/companies/company_form_v2.html" %}{% block sidebar_left %}{% endblock %}',
            company_id=31,
            active_tab='config',
            onboarding=_fake_onboarding('edit'),
        )

    html = html_module.unescape(rendered_html)

    for expected in [
        'Ajuste a empresa existente',
        'Alteração assistida',
        'Configurações da Unidade',
            'API / MCP e Sistema',
        'Salvar alterações',
        'Configurações de Instância',
            'API / MCP',
    ]:
        assert expected in html

    assert 'data-company-id="31"' in html
    assert 'data-onboarding-mode="edit"' in html
