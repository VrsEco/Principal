from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
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
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec
from src.intelligence.tool_catalog import catalog
from services.mcp_connection_snippet_service import MCPConnectionSnippetService
from services.squad_runtime_bootstrap_service import (
    OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS,
    SquadRuntimeBootstrapService,
)
from services.tool_first_catalog_service import ToolFirstCatalogService

try:
    from services.mcp_feature_catalog_service import MCPDocumentationContext, MCPFeatureCatalogService
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com deploy parcial
    @dataclass
    class MCPDocumentationContext:  # type: ignore[override]
        company_id: int | None = None
        user_id: int | None = None
        role: str = "colaborador"
        surface: str = "user"
        client: str = "ai_mcp_console"
        transport: str = "web"

    MCPFeatureCatalogService = None


class AIMCPConsoleService:
    """Monta o estado consultivo do console operacional IA/MCP."""

    SURFACES = ("user", "admin", "analytics", "ops")
    DOCUMENTATION_BOOTSTRAP_SURFACE = "user"
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
        context_counter = Counter(tuple(tool.get("required_context") or ()) for tool in capability_tools)

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
                "title": "API / MCP",
                "href": "/api-mcp",
                "description": "Governança, onboarding, readiness, catálogo e observabilidade em uma única superfície.",
                "kind": "console",
            },
            {
                "title": "Sapiens Factory",
                "href": "/ai/factory",
                "description": "Factory assistida para evoluir Service, Tool, REST/MCP, Workflow e UI/Sapiens com governança.",
                "kind": "console",
            },
            {
                "title": "Visão Geral",
                "href": "/ai",
                "description": "Configurar agentes, parâmetros e monitorar logs de comunicação.",
                "kind": "config",
            },
            {
                "title": "Configurações de Canais",
                "href": "/channels",
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
                "title": "Factory Assistida",
                "href": "/ai/factory",
                "description": "Diagnosticar, planejar e preparar mudanças técnicas com guardrails corporativos.",
            },
            {
                "title": "Mapa de integrações",
                "href": "/channels",
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
                        "label": "Sapiens / API / MCP / Canais",
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
                "analyze": {"label": "Ver surfaces", "href": "/api-mcp"},
            },
            {
                "domain": "processes",
                "label": "Processos",
                "description": "Mapa, instâncias e evolução de processos operacionais.",
                "create": {"label": "Criar / mapear processo", "href": "/processes/map"},
                "update": {"label": "Alterar instância", "href": "/processes/instances"},
                "analyze": {"label": "Revisar domínio", "href": "/api-mcp"},
            },
            {
                "domain": "projects",
                "label": "Projetos",
                "description": "Projetos, tarefas e acompanhamento de execução.",
                "create": {"label": "Criar projeto / tarefa", "href": "/projects"},
                "update": {"label": "Alterar projeto / tarefa", "href": "/projects"},
                "analyze": {"label": "Analisar riscos", "href": "/api-mcp"},
            },
            {
                "domain": "meetings",
                "label": "Reuniões",
                "description": "Agenda, condução, registro e follow-up.",
                "create": {"label": "Criar reunião", "href": "/meetings/manage-v2"},
                "update": {"label": "Alterar reunião", "href": "/meetings/manage-v2"},
                "analyze": {"label": "Revisar regras", "href": "/api-mcp"},
            },
            {
                "domain": "strategy",
                "label": "Estratégico",
                "description": "Planos, indicadores, análises e direcionamento executivo.",
                "create": {"label": "Criar / evoluir plano", "href": "/plans"},
                "update": {"label": "Alterar plano / indicador", "href": "/plans"},
                "analyze": {"label": "Abrir dashboard estratégico", "href": "/api-mcp"},
            },
            {
                "domain": "finance",
                "label": "Financeiro",
                "description": "Operações sensíveis, classificação, cadastros e análise financeira assistida.",
                "create": {"label": "Importar via central / catálogos", "href": "/financial/automation"},
                "update": {"label": "Alterar cadastros financeiros", "href": "/financial/catalogs"},
                "analyze": {"label": "Abrir central financeira IA", "href": "/financial/automation"},
            },
            {
                "domain": "sapiens",
                "label": "Sapiens",
                "description": "Conversação assistida e fluxo oficial do runtime.",
                "create": {"label": "Criar conversa / solicitação", "href": "/sapiens"},
                "update": {"label": "Retomar / alterar contexto", "href": "/sapiens"},
                "analyze": {"label": "Ver catálogo e surfaces", "href": "/api-mcp"},
            },
            {
                "domain": "mcp",
                "label": "API / MCP / Canais",
                "description": "Catálogo de tools, providers, conexões e onboarding técnico.",
                "create": {"label": "Criar integração", "href": "/channels"},
                "update": {"label": "Alterar integração", "href": "/channels"},
                "analyze": {"label": "Ver catálogo MCP", "href": "/api-mcp"},
            },
            {
                "domain": "identity",
                "label": "Identity / Usuários",
                "description": "Perfis, usuários, acessos e contexto operacional.",
                "create": {"label": "Criar / registrar usuário", "href": "/auth/users/page"},
                "update": {"label": "Alterar perfil / usuário", "href": "/auth/profile"},
                "analyze": {"label": "Ver permissões", "href": "/api-mcp"},
            },
            {
                "domain": "governance",
                "label": "Governança / Operação",
                "description": "Release, freeze, readiness, auditoria e abertura controlada.",
                "create": {"label": "Abrir checklist / readiness", "href": "/api-mcp"},
                "update": {"label": "Revisar release / freeze", "href": "/api-mcp"},
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

        assisted_usage = {
            "title": "Modo de Utilização Assistida",
            "objective": "Aumentar autonomia sem cair em paternalismo, combinando onboarding, coprodução e progressão de maturidade.",
            "phases": [
                {
                    "key": "conducao_forte",
                    "title": "Condução forte",
                    "description": "O squad guia o usuário, explica a ferramenta e organiza o próximo passo.",
                    "recommended_for": ["início de implantação", "primeiro uso do APP32", "primeiro uso dos squads"],
                },
                {
                    "key": "coproducao_orientada",
                    "title": "Coprodução orientada",
                    "description": "Humano e squad trabalham juntos; o sistema estrutura, alerta e acelera.",
                    "recommended_for": ["rotina já iniciada", "times em ganho de hábito", "fluxos assistidos recorrentes"],
                },
                {
                    "key": "autonomia_assistida",
                    "title": "Autonomia assistida",
                    "description": "O usuário conduz mais, recebe menos tutoria e opera com apoio contextual sob demanda.",
                    "recommended_for": ["usuários maduros", "consultores experientes", "operações estáveis"],
                },
            ],
            "anti_patterns": [
                "usar o squad como substituto permanente do raciocínio humano",
                "premiar volume de uso em vez de qualidade de uso",
                "manter tutoria máxima para usuários já maduros",
            ],
        }

        maturity_model = {
            "title": "Sinais iniciais de Maturidade Assistida",
            "levels": ["assistido", "orientado", "copiloto", "autonomo", "multiplicador"],
            "signals": {
                "consultor_versus": [
                    "usa discovery antes de operar",
                    "explicita company_id e surface correta",
                    "forma autonomia no cliente sem centralizar tudo",
                ],
                "usuario_cliente": [
                    "formula pedidos com mais clareza",
                    "usa o APP32 sem depender de navegação manual excessiva",
                    "executa com o squad sem tentar contornar guardrails",
                ],
            },
            "rule": "maturidade deve aumentar autonomia com responsabilidade, nunca premiar dependência",
        }

        connection_generator = {
            "title": "Conectar em outro cliente",
            "description": "Cole os dados da conexão e gere o texto pronto para configurar com IA ou copiar a configuração técnica.",
            "defaults": {
                "name": "Sapiens User",
                "default_company": "Sem empresa padrão",
                "url": "https://app.gestaoversus.com.br/mcp/user",
                "auth_type": "bearer",
                "profile": "sapiens_default",
            },
            "profiles": [
                {
                    "key": "sapiens_default",
                    "title": "Sapiens User",
                    "description": "Perfil base para ativação assistida do Sapiens na surface user.",
                    "default_url": "https://app.gestaoversus.com.br/mcp/user",
                    "surface": "user",
                },
                {
                    "key": "squad_versus",
                    "title": "Squad Versus",
                    "description": "Família consultiva da Versus para runtime externo. A entrada recomendada é o Harness Coordenador, com roteamento posterior para estratégia, PMO, operações, finanças e auditoria.",
                    "default_url": "https://app.gestaoversus.com.br/mcp/admin",
                    "surface": "admin",
                    "default_harness_key": "harness_coordenador_versus_v1",
                    "default_harness_label": "Harness Coordenador do Squad Versus",
                    "harnesses": cls._serialize_runtime_harnesses("squad_versus"),
                },
                {
                    "key": "squad_cliente",
                    "title": "Squad Cliente",
                    "description": "Família de copilotos do cliente em runtime externo. A entrada recomendada é o Harness Coordenador, com roteamento posterior para Comercial, Operacional e Adm/Financeiro.",
                    "default_url": "https://app.gestaoversus.com.br/mcp/user",
                    "surface": "user",
                    "default_harness_key": "harness_coordenador_cliente_v1",
                    "default_harness_label": "Harness Coordenador do Squad Cliente",
                    "harnesses": cls._serialize_runtime_harnesses("squad_cliente"),
                    "official_phase_label": "Fase 1 oficial",
                    "official_agents": SquadRuntimeBootstrapService.list_official_squad_cliente_agents(),
                },
                {
                    "key": "engineering",
                    "title": "Squad de Engenharia",
                    "description": "Família técnica da engenharia em runtime externo. A entrada recomendada é o Harness Coordenador, com roteamento posterior para Arquiteto, Frontend, Backend API, Backend Service, AI Engineer, DBA e QA.",
                    "default_url": "https://app.gestaoversus.com.br/mcp/ops",
                    "surface": "ops",
                    "default_harness_key": "harness_coordenador_engenharia_v1",
                    "default_harness_label": "Harness Coordenador do Squad de Engenharia",
                    "harnesses": cls._serialize_runtime_harnesses("engineering"),
                },
            ],
            "modes": [
                {
                    "key": "ai_prompt",
                    "title": "Configurar com IA",
                    "description": "Gera um comando para a outra IA perguntar automático ou manual e já tentar configurar.",
                    "copy_label": "Copiar prompt",
                },
                {
                    "key": "raw_config",
                    "title": "Usar configuração técnica",
                    "description": "Gera o JSON pronto para copiar e colar manualmente.",
                    "copy_label": "Copiar configuração",
                },
            ],
        }

        documentation_bootstrap = cls._build_documentation_bootstrap(active_company)

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
                "tools_user_only": context_counter.get(("user",), 0),
                "tools_company_only": context_counter.get(("company",), 0),
                "tools_user_and_company": context_counter.get(("user", "company"), 0),
            },
            "profiles": profiles,
            "surfaces": surfaces,
            "domains": domains,
            "permissions": permissions,
            "catalog": {
                "manifest_version": capability_manifest.get("version"),
                "tools": capability_tools,
                "context_requirements": {
                    "user_only": context_counter.get(("user",), 0),
                    "company_only": context_counter.get(("company",), 0),
                    "user_and_company": context_counter.get(("user", "company"), 0),
                    "no_explicit_context": context_counter.get((), 0),
                },
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
            "tool_first_catalog": ToolFirstCatalogService.build_catalog(active_company),
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
            "assisted_usage": assisted_usage,
            "maturity_model": maturity_model,
            "governance_telemetry": cls._build_governance_telemetry(active_company),
            "connection_generator": connection_generator,
            "external_runtime_profiles": cls._build_external_runtime_profiles(active_company),
            "documentation_bootstrap": documentation_bootstrap,
            "runtime_context": {
                "required_contract_dimensions": ["user", "company"],
                "resolved": {
                    "company_id": getattr(active_company, "id", None),
                    "company_name": getattr(active_company, "name", None),
                    "company_code": getattr(active_company, "client_code", None),
                },
                "resolution": {
                    "company": "active_company" if getattr(active_company, "id", None) is not None else None,
                },
            },
        }

    @classmethod
    def _build_external_runtime_profiles(cls, active_company: Any | None = None) -> list[dict[str, Any]]:
        company_id = getattr(active_company, "id", None)
        company_name = getattr(active_company, "name", None)
        return [
            {
                "key": "sapiens_default",
                "title": "Sapiens User",
                "owner": "APP32 / front door",
                "surface": "user",
                "default_company_id": company_id,
                "default_company_name": company_name,
                "startup_tools": ["bootstrap_session_context"],
                "primary_goal": "Ativação guiada e uso assistido do Sapiens para operação cotidiana.",
            },
            {
                "key": "squad_versus",
                "title": "Squad Versus",
                "owner": "Família consultiva da Versus em runtime externo",
                "surface": "admin",
                "default_company_id": company_id,
                "default_company_name": company_name,
                "startup_tools": list(MCPConnectionSnippetService.RUNTIME_PROFILES["squad_versus"]["startup_tools"]),
                "primary_goal": "Consultoria, governança e intervenção controlada com entrada pelo coordenador e especialização metodológica por harness.",
                "default_harness_key": "harness_coordenador_versus_v1",
                "default_harness_label": "Harness Coordenador do Squad Versus",
                "harnesses": cls._serialize_runtime_harnesses("squad_versus"),
                "required_contracts": [
                    "profiles",
                    "surface_playbooks",
                    "domain_playbooks",
                    "permission_matrix",
                ],
                "guardrails": [
                    "Usar company_id explícito em surfaces privilegiadas.",
                    "Começar por discovery antes de mutações.",
                    "Tratar Squad Versus como família de harnesses, e não como um agente único.",
                    "Registrar trilha auditável por ator, runtime e capability.",
                ],
            },
            {
                "key": "squad_cliente",
                "title": "Squad Cliente",
                "owner": "Família de copilotos da empresa cliente em runtime externo",
                "surface": "user",
                "default_company_id": company_id,
                "default_company_name": company_name,
                "startup_tools": list(MCPConnectionSnippetService.RUNTIME_PROFILES["squad_cliente"]["startup_tools"]),
                "primary_goal": "Coprodução operacional do cliente com entrada pelo coordenador e especialização por domínio.",
                "default_harness_key": "harness_coordenador_cliente_v1",
                "default_harness_label": "Harness Coordenador do Squad Cliente",
                "harnesses": cls._serialize_runtime_harnesses("squad_cliente"),
                "official_phase_label": "Fase 1 oficial",
                "official_agents": SquadRuntimeBootstrapService.list_official_squad_cliente_agents(),
                "required_contracts": [
                    "surface_playbooks",
                    "profile_contracts",
                ],
                "guardrails": [
                    "Operar com menor privilégio.",
                    "Usar company_id do tenant ativo.",
                    "Não acessar admin, analytics ou ops.",
                    "Tratar Squad Cliente como família de copilotos, e não como um harness único.",
                ],
            },
            {
                "key": "engineering",
                "title": "Squad de Engenharia",
                "owner": "Família técnica de engenharia em runtime externo",
                "surface": "ops",
                "default_company_id": company_id,
                "default_company_name": company_name,
                "startup_tools": list(MCPConnectionSnippetService.RUNTIME_PROFILES["engineering"]["startup_tools"]),
                "primary_goal": "Triagem técnica, diagnóstico e execução disciplinada com entrada pelo coordenador e roteamento para especialidades de engenharia.",
                "default_harness_key": "harness_coordenador_engenharia_v1",
                "default_harness_label": "Harness Coordenador do Squad de Engenharia",
                "harnesses": cls._serialize_runtime_harnesses("engineering"),
                "required_contracts": [
                    "profiles",
                    "surface_playbooks",
                    "domain_playbooks",
                    "permission_matrix",
                ],
                "guardrails": [
                    "Operar somente em surfaces técnicas autorizadas.",
                    "Começar por discovery e evidência antes de intervenção.",
                    "Tratar Squad de Engenharia como família de harnesses, e não como um agente único.",
                    "Registrar trilha auditável por ator, runtime, rollout e validação.",
                ],
            },
        ]

    @staticmethod
    def _serialize_runtime_harnesses(runtime_profile: str) -> list[dict[str, Any]]:
        spec = get_runtime_profile_spec(runtime_profile)
        if spec is None:
            return []
        harnesses = list(spec.harnesses)
        if runtime_profile == "squad_cliente":
            allowed = set(OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS)
            harnesses = [harness for harness in harnesses if harness.key in allowed]
        return [
            {
                "key": harness.key,
                "label": harness.label,
                "business_role": harness.business_role,
            }
            for harness in harnesses
        ]

    @classmethod
    def _build_documentation_bootstrap(cls, active_company: Any | None = None) -> dict[str, Any]:
        company_id = getattr(active_company, "id", None)
        summary = {
            "catalog_version": None,
            "features_total": 0,
            "domains": [],
        }

        if company_id and MCPFeatureCatalogService is not None:
            service = MCPFeatureCatalogService()
            context = MCPDocumentationContext(
                company_id=company_id,
                user_id=None,
                role="colaborador",
                surface=cls.DOCUMENTATION_BOOTSTRAP_SURFACE,
                client="ai_mcp_console",
                transport="web",
            )
            try:
                bootstrap = service.bootstrap_context(context)
                summary = {
                    "catalog_version": bootstrap.get("catalog_version"),
                    "features_total": len(bootstrap.get("features") or []),
                    "domains": list(bootstrap.get("domains") or []),
                    "context_summary": dict(bootstrap.get("context_summary") or {}),
                    "current_context": dict(bootstrap.get("current_context") or {}),
                }
            except Exception:
                summary = {
                    "catalog_version": None,
                    "features_total": 0,
                    "domains": [],
                    "context_summary": {},
                    "current_context": {},
                }

        return {
            "auto_load": True,
            "default_surface": cls.DOCUMENTATION_BOOTSTRAP_SURFACE,
            "endpoint": "/api/configs/ai/mcp/bootstrap-session",
            "summary": summary,
        }

    @classmethod
    def _build_governance_telemetry(cls, active_company: Any | None = None) -> dict[str, Any]:
        company_id = getattr(active_company, "id", None)
        baseline = {
            "enabled": False,
            "company_id": company_id,
            "summary": {"total": 0, "by_source": {}, "by_status": {}},
            "analytics": {
                "by_runtime": {},
                "by_actor_role": {},
                "by_surface": {},
                "by_runtime_profile": {},
                "top_tools": [],
            },
            "required_dimensions": ["company_id", "runtime", "actor_role", "surface", "capability", "status"],
        }
        if not company_id:
            return baseline

        try:
            from services.operational_audit_service import OperationalAuditService

            panel, error = OperationalAuditService.build_panel(
                company_id=int(company_id),
                allowed_company_ids=[int(company_id)],
                source="ai_mcp_runtime",
                limit=50,
            )
            if error or not panel:
                return baseline
            analytics = panel.get("analytics") or {}
            summary = panel.get("summary") or {}
            return {
                "enabled": True,
                "company_id": company_id,
                "summary": summary,
                "analytics": {
                    "by_runtime": dict(analytics.get("by_runtime") or {}),
                    "by_actor_role": dict(analytics.get("by_actor_role") or {}),
                    "by_surface": dict(analytics.get("by_surface") or {}),
                    "by_runtime_profile": dict(analytics.get("by_runtime_profile") or {}),
                    "top_tools": list(analytics.get("top_tools") or []),
                },
                "required_dimensions": ["company_id", "runtime", "actor_role", "surface", "capability", "status"],
            }
        except Exception:
            return baseline
