from __future__ import annotations

from typing import Any


class CompanyOnboardingService:
    """Monta o estado guiado do onboarding de empresas para criação e alteração."""

    TABS = (
        "dados",
        "economico",
        "cargos",
        "colaboradores",
        "usuarios",
        "pontuacao",
        "config",
    )

    HELP_BY_TAB = {
        "dados": {
            "title": "Quem é a empresa?",
            "body": "Comece pela identidade. Este bloco organiza nome, código e propósito antes de qualquer configuração mais sensível.",
            "items": [
                "Preencha razão social, código e propósito.",
                "Se estiver criando, salve aqui antes de seguir para as demais etapas.",
                "Missão, visão e valores ajudam IA/MCP e o Sapiens a contextualizar a empresa.",
            ],
        },
        "economico": {
            "title": "Contexto operacional e econômico",
            "body": "Defina o cenário em que a empresa opera para facilitar filtros, relatórios, cadastros e leitura estratégica.",
            "items": [
                "Informe CNPJ, segmento, porte e localização.",
                "Use este bloco para separar o que é contexto de operação do que é regra de execução.",
                "Sem esse contexto, análises e cadastros futuros tendem a ficar mais confusos.",
            ],
        },
        "cargos": {
            "title": "Estrutura organizacional",
            "body": "Cadastre a espinha dorsal da operação antes de carregar colaboradores e acessos.",
            "items": [
                "Crie cargos e departamentos principais.",
                "Use nomes consistentes para facilitar projetos, processos e reuniões.",
                "Evite puxar o time antes de desenhar a estrutura mínima.",
            ],
        },
        "colaboradores": {
            "title": "Time e execução",
            "body": "Aqui entram as pessoas que executam a rotina e alimentam o contexto operacional da empresa.",
            "items": [
                "Cadastre colaboradores após estruturar cargos.",
                "Revise status e dados do vínculo com a unidade.",
                "Esse bloco prepara o terreno para acessos, workload e leitura de operação.",
            ],
        },
        "usuarios": {
            "title": "Acessos e perfis",
            "body": "Associe pessoas da empresa aos usuários do sistema para liberar uso controlado com perfil correto.",
            "items": [
                "Vincule colaboradores aos usuários existentes do sistema.",
                "Confirme quem pode operar, consultar ou administrar.",
                "Perfis errados aqui geram ruído depois em IA/MCP e Sapiens.",
            ],
        },
        "pontuacao": {
            "title": "Regras e critérios",
            "body": "Use esta etapa para formalizar regras de prazo, atraso e medição que sustentam a operação.",
            "items": [
                "Ajuste pontuações e penalidades com clareza.",
                "Revise se as regras combinam com a cultura operacional da empresa.",
                "Essas definições impactam dashboards e leituras futuras.",
            ],
        },
        "config": {
            "title": "IA, MCP, Sapiens e sistema",
            "body": "Finalize deixando a unidade pronta para operar no ecossistema de IA, com logo, ativação e atalhos de configuração.",
            "items": [
                "Revise se a empresa está ativa para o portal.",
                "Configure logo e use os atalhos para console IA/MCP, integrações e Sapiens.",
                "Só avance para testes depois de concluir identidade, equipe e acessos.",
            ],
        },
    }

    @classmethod
    def build_view_model(cls, company_id: int | None = None, active_tab: str = "dados") -> dict[str, Any]:
        mode = "edit" if company_id else "create"
        active_tab = active_tab if active_tab in cls.TABS else "dados"

        steps = [
            {
                "id": "dados",
                "number": 1,
                "title": "Quem é a empresa?",
                "description": "Nome, código, propósito e identidade.",
                "status": "available",
            },
            {
                "id": "economico",
                "number": 2,
                "title": "Contexto",
                "description": "CNPJ, segmento, porte e cidade.",
                "status": "available" if company_id else "after_create",
            },
            {
                "id": "cargos",
                "number": 3,
                "title": "Estrutura",
                "description": "Cargos, funções e desenho organizacional.",
                "status": "available" if company_id else "after_create",
            },
            {
                "id": "colaboradores",
                "number": 4,
                "title": "Time",
                "description": "Colaboradores que executam a operação.",
                "status": "available" if company_id else "after_create",
            },
            {
                "id": "usuarios",
                "number": 5,
                "title": "Acessos",
                "description": "Usuários que entram no sistema.",
                "status": "available" if company_id else "after_create",
            },
            {
                "id": "pontuacao",
                "number": 6,
                "title": "Regras",
                "description": "Critérios de avaliação e atraso.",
                "status": "available" if company_id else "after_create",
            },
            {
                "id": "config",
                "number": 7,
                "title": "IA/MCP",
                "description": "Logo, ativação e preparo da unidade.",
                "status": "available" if company_id else "after_create",
            },
        ]

        wizard_actions = [
            {
                "id": "create",
                "label": "Criar",
                "description": "Começar uma empresa nova e seguir a trilha guiada até o ponto de teste.",
                "recommended_tab": "dados",
            },
            {
                "id": "update",
                "label": "Alterar",
                "description": "Ajustar empresa existente sem se perder entre cadastros, acessos e IA/MCP.",
                "recommended_tab": active_tab if company_id else "dados",
            },
            {
                "id": "configure",
                "label": "Configurar",
                "description": "Ir para sistema, logo, readiness operacional e superfícies IA/MCP.",
                "recommended_tab": "config" if company_id else "dados",
            },
            {
                "id": "validate",
                "label": "Validar",
                "description": "Revisar checklist antes de liberar a unidade para uso controlado.",
                "recommended_tab": "config" if company_id else "dados",
            },
        ]

        domain_tracks = [
            {
                "id": "routine",
                "title": "Rotina",
                "summary": "Time, cargos, acessos e operação do dia a dia.",
                "create_tab": "cargos" if company_id else "dados",
                "update_tab": "colaboradores" if company_id else "dados",
                "links": [
                    {"label": "Meu Trabalho", "href": "/my-work"},
                    {"label": "Projetos", "href": "/projects"},
                    {"label": "Reuniões", "href": "/meetings"},
                ],
            },
            {
                "id": "strategy",
                "title": "Estratégico",
                "summary": "Missão, visão, descrição e leituras executivas da unidade.",
                "create_tab": "dados",
                "update_tab": "economico" if company_id else "dados",
                "links": [
                    {"label": "Operações Inteligentes", "href": "/operations"},
                    {"label": "Dashboard IA/MCP", "href": "/configs/ai/mcp"},
                ],
            },
            {
                "id": "finance",
                "title": "Financeiro",
                "summary": "Contexto econômico, cadastros-base e preparo para análises e controles.",
                "create_tab": "economico" if company_id else "dados",
                "update_tab": "economico" if company_id else "dados",
                "links": [
                    {"label": "Catálogos Financeiros", "href": "/financial/catalogs"},
                    {"label": "Habilitações de Domínio", "href": "/financial/domain-enablements"},
                ],
            },
            {
                "id": "sapiens",
                "title": "Sapiens / IA / MCP",
                "summary": "Console, integrações, superfícies e readiness para agentes e assistentes.",
                "create_tab": "config" if company_id else "dados",
                "update_tab": "config" if company_id else "dados",
                "links": [
                    {"label": "Console IA/MCP", "href": "/configs/ai/mcp"},
                    {"label": "Integrações", "href": "/integrations"},
                    {"label": "Sapiens", "href": "/sapiens"},
                ],
            },
        ]

        quick_links = [
            {
                "title": "Console Operacional IA/MCP",
                "description": "Perfis, surfaces, release, freeze, readiness e onboarding técnico.",
                "href": "/configs/ai/mcp",
            },
            {
                "title": "Integrações",
                "description": "Conectividade, provedores e segredos operacionais do ecossistema.",
                "href": "/integrations",
            },
            {
                "title": "Sapiens",
                "description": "Runtime conversacional oficial para operação assistida.",
                "href": "/sapiens",
            },
            {
                "title": "Auditoria Operacional",
                "description": "Trilhas, evidências e conferência de operação em produção.",
                "href": "/operations/audit",
            },
        ]

        checklists = {
            "create": [
                "Salvar identidade da empresa.",
                "Preencher contexto econômico mínimo.",
                "Estruturar cargos antes de cadastrar o time.",
                "Vincular acessos dos responsáveis.",
                "Configurar IA/MCP e validar readiness básica.",
            ],
            "edit": [
                "Revisar o que mudou de identidade e contexto.",
                "Atualizar estrutura, equipe e acessos impactados.",
                "Conferir regras e parâmetros da unidade.",
                "Revalidar IA/MCP, integrações e status ativo.",
                "Executar smoke funcional antes de liberar para teste.",
            ],
        }

        return {
            "mode": mode,
            "active_tab": active_tab,
            "header": {
                "title": "Ajuste a empresa existente" if company_id else "Crie uma nova empresa",
                "subtitle": "Wizard guiado para criar ou alterar empresas sem perder o contexto de rotina, estratégia, finanças, Sapiens e IA/MCP.",
                "mode_badge": "Alteração assistida" if company_id else "Criação guiada",
            },
            "steps": steps,
            "wizard_actions": wizard_actions,
            "domain_tracks": domain_tracks,
            "quick_links": quick_links,
            "context_panel": cls.HELP_BY_TAB.get(active_tab, cls.HELP_BY_TAB["dados"]),
            "checklist": checklists[mode],
        }
