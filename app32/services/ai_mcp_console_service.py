from __future__ import annotations

from collections import Counter
from typing import Any

from src.core.mcp_surface_registry import get_surface_manifest
from src.intelligence.mcp_contracts.domain_playbooks import APP32_DOMAIN_PLAYBOOKS_MANIFEST
from src.intelligence.mcp_contracts.external_ai_onboarding import APP32_EXTERNAL_AI_ONBOARDING_MANIFEST
from src.intelligence.mcp_contracts.operational_readiness import APP32_OPERATIONAL_READINESS_MANIFEST
from src.intelligence.mcp_contracts.permission_matrix import APP32_PERMISSION_MATRIX_MANIFEST
from src.intelligence.mcp_contracts.playbooks import APP32_SURFACE_PLAYBOOKS_MANIFEST
from src.intelligence.mcp_contracts.profiles import APP32_PROFILE_CONTRACTS_MANIFEST
from src.intelligence.mcp_contracts.release_checklist import APP32_RELEASE_CHECKLIST_MANIFEST
from src.intelligence.mcp_contracts.tool_freeze import APP32_TOOL_FREEZE_MANIFEST
from src.intelligence.mcp_contracts.usage_dashboard import APP32_USAGE_DASHBOARD_MANIFEST
from src.intelligence.tool_catalog import catalog


class AIMCPConsoleService:
    """Monta o estado consultivo do console operacional IA/MCP."""

    SURFACES = ("user", "admin", "analytics", "ops")

    @classmethod
    def build_frontend_state(cls, active_company: Any | None = None) -> dict[str, Any]:
        profiles = [profile.model_dump(mode="json") for profile in APP32_PROFILE_CONTRACTS_MANIFEST.profiles]
        surfaces = [playbook.model_dump(mode="json") for playbook in APP32_SURFACE_PLAYBOOKS_MANIFEST.playbooks]
        domains = [playbook.model_dump(mode="json") for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks]
        permissions = [matrix.model_dump(mode="json") for matrix in APP32_PERMISSION_MATRIX_MANIFEST.matrices]
        onboarding = APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.model_dump(mode="json")
        release = APP32_RELEASE_CHECKLIST_MANIFEST.model_dump(mode="json")
        freeze = APP32_TOOL_FREEZE_MANIFEST.model_dump(mode="json")
        dashboard = APP32_USAGE_DASHBOARD_MANIFEST.model_dump(mode="json")
        readiness = APP32_OPERATIONAL_READINESS_MANIFEST.model_dump(mode="json")

        capability_manifest = catalog.get_capability_manifest(include_tools=True)
        capability_tools = sorted(
            list(capability_manifest.get("tools", [])),
            key=lambda item: (str(item.get("domain", "")), str(item.get("name", ""))),
        )

        surface_capabilities = []
        for surface in cls.SURFACES:
            manifest = get_surface_manifest(surface, include_tools=True)
            tools = list(manifest.get("tools", []))
            surface_capabilities.append(
                {
                    "surface": surface,
                    "tool_count": len(tools),
                    "domains": sorted({tool.get("domain") for tool in tools if tool.get("domain")}),
                    "human_gate_count": sum(1 for tool in tools if tool.get("human_gate")),
                    "critical_count": sum(1 for tool in tools if tool.get("risk") == "critical"),
                }
            )

        risk_counter = Counter(tool.get("risk") for tool in capability_tools if tool.get("risk"))
        domain_counter = Counter(tool.get("domain") for tool in capability_tools if tool.get("domain"))

        readiness_by_phase = []
        for phase in ("contracts", "release", "onboarding", "operations", "go_live"):
            gates = [gate for gate in readiness["gates"] if gate["phase"] == phase]
            readiness_by_phase.append(
                {
                    "phase": phase,
                    "gate_count": len(gates),
                    "required_count": sum(1 for gate in gates if gate["status"] == "required"),
                    "gates": gates,
                }
            )

        configuration_links = [
            {
                "title": "Console Operacional IA/MCP",
                "href": "/configs/ai/mcp",
                "description": "Governança, onboarding, readiness, catálogo e observabilidade em uma única superfície.",
                "kind": "console",
            },
            {
                "title": "Parâmetros gerais de IA",
                "href": "/configs/ai",
                "description": "Configurar agentes, parâmetros e monitorar logs de comunicação.",
                "kind": "config",
            },
            {
                "title": "Tools / MCP / Integrações",
                "href": "/integrations",
                "description": "Gerenciar provedores, segredos operacionais e conectividade do ecossistema.",
                "kind": "config",
            },
            {
                "title": "Auditoria Operacional",
                "href": "/operations/audit",
                "description": "Conferir trilhas MCP, Sapiens, intervenções humanas e evidências operacionais.",
                "kind": "audit",
            },
        ]

        registration_links = [
            {
                "title": "Usuários do sistema",
                "href": "/auth/users/page",
                "description": "Consultar e revisar usuários aptos a operar as surfaces privilegiadas.",
                "kind": "cadastro",
            },
            {
                "title": "Meu perfil",
                "href": "/auth/profile",
                "description": "Ajustar identidade, contatos e contexto pessoal do operador.",
                "kind": "cadastro",
            },
            {
                "title": "Cadastros-base financeiros",
                "href": "/financial/catalogs",
                "description": "Manter contas, centros de resultado, favorecidos e estruturas que influenciam a IA.",
                "kind": "cadastro",
            },
            {
                "title": "Domínios habilitados",
                "href": "/financial/domain-enablements",
                "description": "Controlar projetos e processos que podem ser cruzados nas automações e análises.",
                "kind": "cadastro",
            },
        ]

        operational_links = [
            {
                "title": "Sapiens",
                "href": "/sapiens",
                "description": "Acesso direto ao runtime conversacional oficial do APP32.",
            },
            {
                "title": "Mapa de integrações",
                "href": "/integrations",
                "description": "Conferir provedores externos, canais e políticas de segredo.",
            },
            {
                "title": "Route audit",
                "href": "/route-audit/",
                "description": "Auditar logging, cobertura e pontos expostos da plataforma.",
            },
        ]

        wizard_steps = [
            {
                "step": 1,
                "id": "profile",
                "title": "Quem vai usar?",
                "question": "Escolha o perfil que mais se aproxima de quem vai operar agora.",
                "options": [
                    {
                        "label": "Colaborador",
                        "description": "Para execução assistida de rotina, projetos, reuniões e autoatendimento.",
                        "target_tab": "profiles",
                        "target_selector": "colaborador",
                    },
                    {
                        "label": "Cliente",
                        "description": "Para consulta, acompanhamento e análises guiadas com menor privilégio.",
                        "target_tab": "profiles",
                        "target_selector": "cliente",
                    },
                    {
                        "label": "Administrador",
                        "description": "Para governança, configuração, onboarding, release e telemetria.",
                        "target_tab": "profiles",
                        "target_selector": "administrador",
                    },
                ],
            },
            {
                "step": 2,
                "id": "action",
                "title": "Você quer criar, alterar, configurar ou analisar?",
                "question": "Escolha a ação principal. O wizard vai sugerir a trilha e a tela mais adequada.",
                "options": [
                    {
                        "label": "Criar",
                        "description": "Abrir uma tela para incluir algo novo no fluxo operacional ou administrativo.",
                        "target_tab": "onboarding",
                        "target_selector": "criar novo cadastro create",
                    },
                    {
                        "label": "Alterar",
                        "description": "Entrar em uma área que normalmente concentra revisão, edição ou ajuste de configuração.",
                        "target_tab": "profiles",
                        "target_selector": "alterar editar update revisão",
                    },
                    {
                        "label": "Configurar",
                        "description": "Ajustar integrações, parâmetros, perfis ou cadastros-base.",
                        "target_tab": "onboarding",
                        "target_selector": "configurar",
                    },
                    {
                        "label": "Operar",
                        "description": "Usar surfaces, descobrir tools e seguir o fluxo de execução.",
                        "target_tab": "surfaces",
                        "target_selector": "operar",
                    },
                    {
                        "label": "Analisar",
                        "description": "Consultar dashboard, readiness, métricas e cruzamentos permitidos.",
                        "target_tab": "dashboard",
                        "target_selector": "analisar",
                    },
                ],
            },
            {
                "step": 3,
                "id": "domain",
                "title": "Qual área você quer atingir?",
                "question": "Escolha o domínio principal. O wizard cobre rotina, estratégico, financeiro, Sapiens e governança.",
                "options": [
                    {
                        "label": "Rotina / Processos / Projetos / Reuniões",
                        "description": "Uso operacional do dia a dia com surface user e playbooks funcionais.",
                        "target_tab": "surfaces",
                        "target_selector": "routine processes projects meetings",
                    },
                    {
                        "label": "Estratégico / Analytics / Workload",
                        "description": "Leitura analítica, planos, indicadores e painéis de capacidade.",
                        "target_tab": "dashboard",
                        "target_selector": "strategy analytics workload",
                    },
                    {
                        "label": "Finanças / Governança / Identity",
                        "description": "Uso sensível com permissões administrativas e gates humanos.",
                        "target_tab": "release",
                        "target_selector": "finance governance identity",
                    },
                    {
                        "label": "Sapiens / MCP / Integrações",
                        "description": "Fluxos conversacionais, catálogo de tools, onboarding técnico e integrações.",
                        "target_tab": "catalog",
                        "target_selector": "sapiens mcp integrations catalog",
                    },
                ],
            },
        ]

        guided_actions = [
            {
                "domain": "routine",
                "label": "Rotina",
                "description": "Fluxos operacionais do dia a dia e acompanhamento de trabalho.",
                "create": {"label": "Criar via Meu Trabalho", "href": "/my-work"},
                "update": {"label": "Alterar via Meu Trabalho", "href": "/my-work"},
                "analyze": {"label": "Ver surfaces", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "processes",
                "label": "Processos",
                "description": "Mapa, instâncias e evolução de processos operacionais.",
                "create": {"label": "Criar / mapear processo", "href": "/processes/map"},
                "update": {"label": "Alterar instância", "href": "/processes/instances"},
                "analyze": {"label": "Revisar domínio", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "projects",
                "label": "Projetos",
                "description": "Projetos, tarefas e acompanhamento de execução.",
                "create": {"label": "Criar projeto / tarefa", "href": "/projects"},
                "update": {"label": "Alterar projeto / tarefa", "href": "/projects"},
                "analyze": {"label": "Analisar riscos", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "meetings",
                "label": "Reuniões",
                "description": "Agenda, condução, registro e follow-up.",
                "create": {"label": "Criar reunião", "href": "/meetings/manage-v2"},
                "update": {"label": "Alterar reunião", "href": "/meetings/manage-v2"},
                "analyze": {"label": "Revisar regras", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "strategy",
                "label": "Estratégico",
                "description": "Planos, indicadores, análises e direcionamento executivo.",
                "create": {"label": "Criar / evoluir plano", "href": "/plans"},
                "update": {"label": "Alterar plano / indicador", "href": "/plans"},
                "analyze": {"label": "Abrir dashboard estratégico", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "finance",
                "label": "Financeiro",
                "description": "Operações sensíveis, classificação, cadastros e análise financeira assistida.",
                "create": {"label": "Criar via prestação / catálogos", "href": "/financial/accountability"},
                "update": {"label": "Alterar cadastros financeiros", "href": "/financial/catalogs"},
                "analyze": {"label": "Abrir dashboard financeiro IA", "href": "/financial/classification-dashboard"},
            },
            {
                "domain": "sapiens",
                "label": "Sapiens",
                "description": "Conversação assistida e fluxo oficial do runtime.",
                "create": {"label": "Criar conversa / solicitação", "href": "/sapiens"},
                "update": {"label": "Retomar / alterar contexto", "href": "/sapiens"},
                "analyze": {"label": "Ver catálogo e surfaces", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "mcp",
                "label": "MCP / Integrações",
                "description": "Catálogo de tools, providers, conexões e onboarding técnico.",
                "create": {"label": "Criar integração", "href": "/integrations"},
                "update": {"label": "Alterar integração", "href": "/integrations"},
                "analyze": {"label": "Ver catálogo MCP", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "identity",
                "label": "Identity / Usuários",
                "description": "Perfis, usuários, acessos e contexto operacional.",
                "create": {"label": "Criar / registrar usuário", "href": "/auth/users/page"},
                "update": {"label": "Alterar perfil / usuário", "href": "/auth/profile"},
                "analyze": {"label": "Ver permissões", "href": "/configs/ai/mcp"},
            },
            {
                "domain": "governance",
                "label": "Governança / Operação",
                "description": "Release, freeze, readiness, auditoria e abertura controlada.",
                "create": {"label": "Abrir checklist / readiness", "href": "/configs/ai/mcp"},
                "update": {"label": "Revisar release / freeze", "href": "/configs/ai/mcp"},
                "analyze": {"label": "Ver auditoria operacional", "href": "/operations/audit"},
            },
        ]

        quick_assistant = [
            {
                "label": "Quero configurar primeiro",
                "description": "Vai para integrações, parâmetros gerais e onboarding guiado.",
                "target_tab": "onboarding",
                "query": "configurar",
            },
            {
                "label": "Quero entender permissões",
                "description": "Mostra perfil, surface e o que é permitido ou bloqueado.",
                "target_tab": "profiles",
                "query": "permissões perfil surface",
            },
            {
                "label": "Quero analisar dados",
                "description": "Leva para dashboard, readiness e blocos analíticos do console.",
                "target_tab": "dashboard",
                "query": "analytics dashboard readiness",
            },
            {
                "label": "Quero liberar uso em produção",
                "description": "Abre release, freeze e critérios de abertura controlada.",
                "target_tab": "release",
                "query": "release freeze go live",
            },
            {
                "label": "Quero criar algo novo",
                "description": "Mostra rapidamente os pontos de criação em rotina, projetos, reuniões, estratégia e financeiro.",
                "target_tab": "onboarding",
                "query": "criar novo cadastro create",
            },
            {
                "label": "Quero alterar algo existente",
                "description": "Direciona para revisão, edição e ajuste dos fluxos já existentes.",
                "target_tab": "profiles",
                "query": "alterar editar update revisão",
            },
        ]

        contextual_help = [
            {
                "title": "Se você está começando agora",
                "body": "Use o wizard no topo. Ele reduz a complexidade e te leva para a seção certa sem exigir que você conheça MCP, surfaces ou contratos.",
            },
            {
                "title": "Se precisa só configurar",
                "body": "Comece por Onboarding & Cadastros. Lá estão integrações, usuários, parâmetros gerais e entradas de configuração do ecossistema.",
            },
            {
                "title": "Se quer apenas usar no dia a dia",
                "body": "Olhe Perfis & Permissões e depois Surfaces & Domínios. Isso responde rapidamente o que pode ou não pode ser feito.",
            },
            {
                "title": "Se quer abrir para teste controlado",
                "body": "Use Dashboard & Readiness e Release & Freeze. Essas áreas mostram os gates obrigatórios antes de ampliar o uso.",
            },
        ]

        return {
            "active_company": {
                "id": getattr(active_company, "id", None),
                "name": getattr(active_company, "name", None),
                "client_code": getattr(active_company, "client_code", None),
            },
            "summary": {
                "profiles": len(profiles),
                "surfaces": len(surfaces),
                "domains": len(domains),
                "permission_matrices": len(permissions),
                "catalog_tools": len(capability_tools),
                "human_gate_tools": sum(1 for tool in capability_tools if tool.get("human_gate")),
                "critical_tools": risk_counter.get("critical", 0),
                "release_checks": len(release["checklist"]),
                "release_smokes": len(release["smokes"]),
                "freeze_triggers": len(freeze["triggers"]),
                "onboarding_steps": len(onboarding["steps"]),
                "readiness_gates": len(readiness["gates"]),
                "dashboard_panels": len(dashboard["panels"]),
            },
            "profiles": profiles,
            "surfaces": surfaces,
            "domains": domains,
            "permissions": permissions,
            "catalog": {
                "manifest_version": capability_manifest.get("version"),
                "tools": capability_tools,
                "domain_distribution": [
                    {"domain": domain, "count": count}
                    for domain, count in sorted(domain_counter.items(), key=lambda item: (-item[1], item[0]))
                ],
                "risk_distribution": [
                    {"risk": risk, "count": count}
                    for risk, count in sorted(risk_counter.items(), key=lambda item: item[0])
                ],
                "surfaces": surface_capabilities,
            },
            "onboarding": onboarding,
            "release": release,
            "freeze": freeze,
            "dashboard": dashboard,
            "readiness": readiness,
            "readiness_by_phase": readiness_by_phase,
            "configuration_links": configuration_links,
            "registration_links": registration_links,
            "operational_links": operational_links,
            "wizard_steps": wizard_steps,
            "guided_actions": guided_actions,
            "quick_assistant": quick_assistant,
            "contextual_help": contextual_help,
        }
