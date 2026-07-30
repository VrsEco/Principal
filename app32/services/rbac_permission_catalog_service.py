from __future__ import annotations

from copy import deepcopy
from typing import Any


def _node(
    key: str,
    label: str,
    description: str,
    actions: list[str],
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "key": key,
        "label": label,
        "description": description,
        "actions": actions,
    }
    if children:
        payload["children"] = children
    return payload


def _screen(key: str, label: str, description: str) -> dict[str, Any]:
    return _node(key, label, description, ["view", "export"])


def _feature(
    key: str,
    label: str,
    description: str,
    actions: list[str] | None = None,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _node(
        key,
        label,
        description,
        actions or ["view", "create", "edit", "delete"],
        children,
    )


def _api_group(
    key: str,
    label: str,
    description: str,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    return _node(
        key,
        label,
        description,
        actions or ["view", "create", "edit", "delete", "export"],
    )


def _tool(
    key: str,
    label: str,
    description: str,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    return _node(
        key,
        label,
        description,
        actions or ["view", "execute", "configure", "audit"],
    )


class RbacPermissionCatalogService:
    SCHEMA_VERSION = 3
    CATALOG_VERSION = "2026.05-systemic"
    META_KEYS = {"__schema_version__", "__catalog_version__"}

    ACTIONS = [
        {"key": "view", "label": "Visualizar", "short_label": "Ver"},
        {"key": "create", "label": "Incluir", "short_label": "Inc"},
        {"key": "edit", "label": "Alterar", "short_label": "Alt"},
        {"key": "delete", "label": "Excluir", "short_label": "Exc"},
        {"key": "approve", "label": "Aprovar", "short_label": "Apr"},
        {"key": "reject", "label": "Reprovar", "short_label": "Rep"},
        {"key": "assign", "label": "Atribuir", "short_label": "Atr"},
        {"key": "change_status", "label": "Alterar status", "short_label": "Status"},
        {"key": "replan", "label": "Replanejar prazo", "short_label": "Prazo"},
        {"key": "close", "label": "Encerrar", "short_label": "Enc"},
        {"key": "reopen", "label": "Reabrir", "short_label": "Reab"},
        {"key": "export", "label": "Exportar", "short_label": "Exp"},
        {"key": "configure", "label": "Configurar", "short_label": "Cfg"},
        {"key": "execute", "label": "Executar", "short_label": "Exe"},
        {"key": "grant", "label": "Conceder", "short_label": "Grant"},
        {"key": "audit", "label": "Auditar", "short_label": "Audit"},
        {"key": "triage", "label": "Triar", "short_label": "Tri"},
        {"key": "manage_financial_sheet", "label": "Gerir ficha financeira", "short_label": "Fin"},
        {"key": "generate_pdf", "label": "Gerar PDF", "short_label": "PDF"},
        {"key": "manage_sources", "label": "Gerir fontes", "short_label": "Fontes"},
    ]

    PRESETS = [
        {
            "key": "colaborador_operacional",
            "label": "Colaborador Operacional",
            "description": "Acesso de execução do dia a dia com foco em leitura, atualização operacional e tarefas próprias/equipe.",
            "grants": {
                "auth.profile": ["view", "edit"],
                "auth.password": ["view", "edit"],
                "projects.screens.board": ["view"],
                "projects.screens.detail": ["view"],
                "projects.tasks": ["view", "create", "edit", "assign", "change_status"],
                "projects.tasks.board": ["view", "edit", "change_status"],
                "projects.tasks.list": ["view", "edit", "change_status"],
                "projects.tasks.comments": ["view", "create", "edit"],
                "projects.hours": ["view", "create", "edit"],
                "real_estate_auctions": ["view", "create", "edit", "triage", "export"],
                "my_work.activities": ["view", "create", "edit", "change_status"],
                "my_work.comments": ["view", "create", "edit"],
                "my_work.work_logs": ["view", "create", "edit"],
            },
        },
        {
            "key": "gestor_unidade",
            "label": "Gestor da Unidade",
            "description": "Gestão ampla da empresa, equipe, projetos, planos e leitura operacional.",
            "grants": {
                "companies": ["view", "edit", "configure", "export"],
                "companies.structure": ["view", "create", "edit", "assign", "configure"],
                "companies.structure.roles": ["view", "create", "edit", "configure"],
                "companies.structure.employees": ["view", "create", "edit", "assign", "export"],
                "companies.structure.user_access": ["view", "create", "edit", "assign", "configure"],
                "projects": ["view", "create", "edit", "approve", "change_status", "replan", "close", "reopen", "export"],
                "projects.tasks": ["view", "create", "edit", "assign", "change_status", "replan"],
                "projects.team": ["view", "create", "edit", "assign", "export"],
                "projects.hours": ["view", "approve", "reject", "export"],
                "plans": ["view", "create", "edit", "approve", "export"],
                "indicators": ["view", "create", "edit", "approve", "export"],
                "okrs": ["view", "create", "edit", "approve", "export"],
                "real_estate_auctions": ["view", "create", "edit", "delete", "triage", "manage_financial_sheet", "generate_pdf", "manage_sources", "export", "configure"],
                "operations.audit": ["view", "export", "audit"],
            },
        },
        {
            "key": "financeiro",
            "label": "Financeiro",
            "description": "Perfil orientado a lançamentos, conciliação, orçamento e relatórios financeiros.",
            "grants": {
                "financial": ["view", "create", "edit", "approve", "reject", "export"],
                "financial.entries": ["view", "create", "edit", "approve", "reject", "export"],
                "financial.settlements": ["view", "create", "edit", "approve", "reject"],
                "financial.schedules": ["view", "create", "edit", "approve", "export"],
                "financial.catalogs": ["view", "create", "edit", "configure", "export"],
                "financial.reports": ["view", "export"],
                "financial.reconciliation": ["view", "edit", "approve", "reject", "execute"],
                "financial.imports": ["view", "create", "edit", "approve", "execute"],
                "financial.budget": ["view", "create", "edit", "approve", "export", "configure"],
                "financial.automation": ["view", "edit", "approve", "execute", "audit"],
                "financial.mcp": ["view", "execute", "audit"],
                "real_estate_auctions": ["view", "create", "edit", "triage", "manage_financial_sheet", "generate_pdf", "export"],
            },
        },
        {
            "key": "pmo_projetos",
            "label": "PMO / Projetos",
            "description": "Coordenação de portfólio, planejamento, riscos, indicadores e relatórios.",
            "grants": {
                "projects": ["view", "create", "edit", "approve", "change_status", "replan", "close", "reopen", "export"],
                "projects.portfolio": ["view", "create", "edit", "change_status", "export"],
                "projects.planning": ["view", "create", "edit", "approve", "replan", "export"],
                "projects.phases": ["view", "create", "edit", "change_status", "replan"],
                "projects.tasks": ["view", "create", "edit", "assign", "change_status", "replan"],
                "projects.risks": ["view", "create", "edit", "approve", "change_status", "export"],
                "projects.reports": ["view", "export"],
                "plans": ["view", "create", "edit", "approve", "export"],
                "indicators": ["view", "create", "edit", "approve", "export"],
                "okrs": ["view", "create", "edit", "approve", "export"],
                "real_estate_auctions": ["view", "create", "edit", "triage", "manage_financial_sheet", "generate_pdf", "export"],
            },
        },
        {
            "key": "admin_unidade",
            "label": "Administrador da Unidade",
            "description": "Administrador completo do tenant, incluindo operations, integrações e superfícies MCP locais.",
            "grants": {
                "companies": ["view", "create", "edit", "delete", "configure", "export"],
                "projects": ["view", "create", "edit", "delete", "approve", "change_status", "replan", "close", "reopen", "export"],
                "processes": ["view", "create", "edit", "delete", "approve", "export", "configure", "execute"],
                "plans": ["view", "create", "edit", "delete", "approve", "export", "configure"],
                "indicators": ["view", "create", "edit", "delete", "approve", "export"],
                "okrs": ["view", "create", "edit", "delete", "approve", "export"],
                "my_work": ["view", "create", "edit", "delete", "approve", "export", "change_status"],
                "contracts": ["view", "create", "edit", "delete", "approve", "export", "configure"],
                "financial": ["view", "create", "edit", "delete", "approve", "reject", "export", "configure", "execute"],
                "real_estate_auctions": ["view", "create", "edit", "delete", "triage", "manage_financial_sheet", "generate_pdf", "manage_sources", "export", "configure", "audit"],
                "incentives": ["view", "create", "edit", "delete", "approve", "export", "configure"],
                "operations": ["view", "create", "edit", "delete", "approve", "export", "configure", "grant", "audit", "execute"],
                "agents": ["view", "create", "edit", "approve", "reject", "execute", "configure", "audit"],
                "mcp": ["view", "execute", "configure", "grant", "audit", "export"],
                "integrations": ["view", "create", "edit", "delete", "configure", "execute", "audit"],
            },
        },
        {
            "key": "auditor_leitura",
            "label": "Auditor / Leitura",
            "description": "Leitura ampla, exportação e trilha de auditoria sem mutação operacional.",
            "grants": {
                "companies": ["view", "export"],
                "projects": ["view", "export"],
                "processes": ["view", "export", "audit"],
                "plans": ["view", "export"],
                "indicators": ["view", "export"],
                "okrs": ["view", "export"],
                "my_work": ["view", "export"],
                "contracts": ["view", "export"],
                "financial": ["view", "export", "audit"],
                "real_estate_auctions": ["view", "export", "audit"],
                "incentives": ["view", "export", "audit"],
                "operations": ["view", "export", "audit"],
                "agents": ["view", "audit"],
                "mcp": ["view", "audit", "export"],
                "integrations": ["view", "audit"],
            },
        },
    ]

    CATALOG = [
        _node(
            "auth",
            "Autenticação e Perfil",
            "Login, perfil do usuário, senha e token MCP pessoal.",
            ["view", "edit", "configure"],
            [
                _screen("auth.screens.login", "Tela de Login", "Acesso à tela de autenticação."),
                _screen("auth.screens.profile", "Tela de Perfil", "Perfil do usuário autenticado."),
                _feature(
                    "auth.profile",
                    "Dados de Perfil",
                    "Alteração de nome, email, foto e preferências do próprio usuário.",
                    ["view", "edit", "configure"],
                ),
                _feature(
                    "auth.password",
                    "Senha",
                    "Alteração segura da senha do próprio usuário.",
                    ["view", "edit", "configure"],
                ),
                _feature(
                    "auth.mcp_token",
                    "Token MCP Pessoal",
                    "Geração, renovação e revogação do token MCP do usuário.",
                    ["view", "create", "edit", "delete", "configure"],
                ),
                _api_group(
                    "auth.api.profile",
                    "API de Perfil",
                    "Endpoints de leitura e atualização do próprio perfil.",
                    ["view", "edit", "configure"],
                ),
                _api_group(
                    "auth.api.mcp_token",
                    "API de Token MCP",
                    "Status, configuração, geração, renovação e revogação do token MCP pessoal.",
                    ["view", "create", "edit", "delete", "configure"],
                ),
            ],
        ),
        _node(
            "companies",
            "Empresas",
            "Cadastro e configuração da unidade, onboarding e governança do tenant.",
            ["view", "create", "edit", "delete", "configure", "export"],
            [
                _node(
                    "companies.screens",
                    "Telas",
                    "Navegação visual do módulo de empresas.",
                    ["view", "export"],
                    [
                        _screen("companies.screens.list", "Lista de Empresas", "Tela de listagem das empresas."),
                        _screen("companies.screens.form", "Formulário de Empresa", "Wizard de cadastro/edição da empresa."),
                    ],
                ),
                _node(
                    "companies.structure",
                    "Estrutura",
                    "Cargos, colaboradores, acessos e base organizacional.",
                    ["view", "create", "edit", "delete", "assign", "configure", "export"],
                    [
                        _feature(
                            "companies.structure.roles",
                            "Cargos e Funções",
                            "Estrutura de cargos com matriz RBAC em árvore.",
                            ["view", "create", "edit", "delete", "configure", "export"],
                        ),
                        _feature(
                            "companies.structure.employees",
                            "Colaboradores",
                            "Cadastro e manutenção dos colaboradores da unidade.",
                            ["view", "create", "edit", "delete", "assign", "export"],
                        ),
                        _feature(
                            "companies.structure.user_access",
                            "Acessos de Usuário",
                            "Vínculo entre colaboradores e usuários do sistema.",
                            ["view", "create", "edit", "delete", "assign", "configure"],
                        ),
                    ],
                ),
                _feature(
                    "companies.identity",
                    "Identidade da Empresa",
                    "Dados cadastrais, missão, visão, valores e identificação legal.",
                    ["view", "create", "edit", "delete", "configure"],
                ),
                _feature(
                    "companies.economic",
                    "Dados Econômicos",
                    "Porte, segmento, localização e contexto econômico da unidade.",
                    ["view", "create", "edit", "configure", "export"],
                ),
                _feature(
                    "companies.performance_settings",
                    "Pontuação e Regras de Avaliação",
                    "Critérios de prazo, penalidades e políticas de adiamento.",
                    ["view", "edit", "configure"],
                ),
                _feature(
                    "companies.branding",
                    "Branding e Logo",
                    "Logo institucional e ativos de identidade visual da unidade.",
                    ["view", "create", "edit", "delete", "configure"],
                ),
                _feature(
                    "companies.api_mcp",
                    "API / MCP da Unidade",
                    "Preparação da empresa para integrações, IA e MCP.",
                    ["view", "configure", "export"],
                ),
                _node(
                    "companies.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de empresas.",
                    ["view", "create", "edit", "delete", "export", "configure"],
                    [
                        _api_group("companies.api.companies", "Empresas", "CRUD principal das empresas."),
                        _api_group("companies.api.roles", "Cargos", "CRUD e leitura dos cargos da empresa.", ["view", "create", "edit", "delete", "configure"]),
                        _api_group("companies.api.employees", "Colaboradores", "CRUD e listagem de colaboradores.", ["view", "create", "edit", "delete", "assign", "export"]),
                        _api_group("companies.api.users", "Usuários Vinculados", "Vínculo, desligamento e reativação de acessos.", ["view", "create", "edit", "delete", "assign", "configure"]),
                        _api_group("companies.api.performance", "Pontuação", "Leitura e manutenção das regras de avaliação.", ["view", "edit", "configure"]),
                    ],
                ),
            ],
        ),
        _node(
            "projects",
            "Projetos",
            "Gestão macro de projetos, pipeline, execução e governança.",
            ["view", "create", "edit", "delete", "approve", "change_status", "replan", "close", "reopen", "export"],
            [
                _node(
                    "projects.screens",
                    "Telas",
                    "Telas web do módulo de projetos.",
                    ["view", "export"],
                    [
                        _screen("projects.screens.dashboard", "Dashboard", "Cockpit do módulo de projetos."),
                        _screen("projects.screens.portfolio", "Portfólio", "Lista e filtros de projetos."),
                        _screen("projects.screens.board", "Board / Kanban", "Execução visual das tarefas."),
                        _screen("projects.screens.detail", "Detalhe do Projeto", "Visão detalhada do projeto."),
                    ],
                ),
                _feature(
                    "projects.portfolio",
                    "Portfólio",
                    "Lista, filtros, priorização e ativação de projetos.",
                    ["view", "create", "edit", "change_status", "export"],
                ),
                _feature(
                    "projects.planning",
                    "Planejamento",
                    "Escopo, baseline, marcos e cronograma executivo.",
                    ["view", "create", "edit", "approve", "replan", "export"],
                ),
                _feature(
                    "projects.phases",
                    "Etapas / Fases",
                    "Quebra do projeto por entregas, marcos e fases.",
                    ["view", "create", "edit", "delete", "change_status", "replan"],
                ),
                _feature(
                    "projects.tasks",
                    "Tarefas",
                    "Backlog operacional, responsáveis, execuções e filas internas.",
                    ["view", "create", "edit", "delete", "assign", "change_status", "replan"],
                    [
                        _feature("projects.tasks.board", "Quadro Kanban", "Gestão visual do fluxo de trabalho.", ["view", "edit", "assign", "change_status"]),
                        _feature("projects.tasks.list", "Lista de Tarefas", "Operação tabular, filtros e visão analítica.", ["view", "create", "edit", "delete", "assign", "change_status"]),
                        _feature("projects.tasks.subtasks", "Subtarefas", "Quebra fina de execução operacional.", ["view", "create", "edit", "delete", "change_status"]),
                        _feature("projects.tasks.comments", "Comentários", "Troca operacional e contexto nas tarefas.", ["view", "create", "edit", "delete"]),
                        _feature("projects.tasks.dependencies", "Dependências", "Dependências e precedências entre tarefas.", ["view", "create", "edit", "delete"]),
                        _feature("projects.tasks.transfer", "Transferência de Tarefas", "Transferência de responsabilidade entre colaboradores.", ["view", "edit", "assign"]),
                        _feature("projects.tasks.backlog_actions", "Backlog Actions", "Ações operacionais acionadas a partir do backlog.", ["view", "execute", "edit", "approve"]),
                    ],
                ),
                _feature("projects.team", "Equipe", "Alocação de colaboradores e papéis no projeto.", ["view", "create", "edit", "delete", "assign", "export"]),
                _feature("projects.hours", "Apontamentos de Horas", "Registro, validação e aprovação de horas.", ["view", "create", "edit", "delete", "approve", "reject", "export"]),
                _feature("projects.documents", "Documentos", "Anexos, evidências e artefatos do projeto.", ["view", "create", "edit", "delete", "export"]),
                _feature("projects.risks", "Riscos / Impedimentos", "Mapeamento e tratamento de riscos do projeto.", ["view", "create", "edit", "delete", "approve", "change_status", "export"]),
                _feature("projects.reports", "Relatórios", "Relatórios gerenciais, executivos e operacionais.", ["view", "export"]),
                _node(
                    "projects.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de projetos.",
                    ["view", "create", "edit", "delete", "assign", "change_status", "replan", "export", "execute"],
                    [
                        _api_group("projects.api.projects", "Projetos", "CRUD principal e ativação dos projetos.", ["view", "create", "edit", "delete", "change_status", "export"]),
                        _api_group("projects.api.tasks", "Tarefas", "CRUD das tarefas do projeto.", ["view", "create", "edit", "delete", "assign", "change_status", "replan"]),
                        _api_group("projects.api.task_collaborators", "Colaboradores da Tarefa", "Vínculo de colaboradores por tarefa.", ["view", "create", "edit", "delete", "assign"]),
                        _api_group("projects.api.task_dependencies", "Dependências", "Dependências entre tarefas.", ["view", "create", "edit", "delete"]),
                        _api_group("projects.api.task_hours", "Horas", "Resumo e medição de horas por tarefa.", ["view", "export"]),
                        _api_group("projects.api.task_transfer", "Transferência", "Transferência operacional de tarefas.", ["view", "edit", "assign"]),
                        _api_group("projects.api.backlog_actions", "Backlog Actions", "Execução de ações operacionais ligadas a backlog.", ["view", "execute", "approve"]),
                    ],
                ),
            ],
        ),
        _node(
            "processes",
            "Processos",
            "Arquitetura processual, BPMN, contratos de execução e instâncias.",
            ["view", "create", "edit", "delete", "approve", "export", "configure", "execute"],
            [
                _node(
                    "processes.screens",
                    "Telas",
                    "Telas do modelador e da operação processual.",
                    ["view", "export"],
                    [
                        _screen("processes.screens.catalog", "Catálogo de Processos", "Lista de áreas, macroprocessos e processos."),
                        _screen("processes.screens.modeler", "Modelador BPMN", "Editor visual BPMN e assistente de IA."),
                        _screen("processes.screens.instances", "Instâncias", "Execução e acompanhamento das instâncias."),
                        _screen("processes.screens.runtime", "Runtime", "Timeline, overlay e execuções da instância."),
                    ],
                ),
                _feature("processes.areas", "Áreas de Processo", "Gestão das áreas de processo.", ["view", "create", "edit", "delete"]),
                _feature("processes.macros", "Macroprocessos", "Agrupadores de processos por domínio.", ["view", "create", "edit", "delete"]),
                _feature("processes.catalog", "Processos", "Cadastro principal de processos.", ["view", "create", "edit", "delete", "approve", "export"]),
                _feature("processes.bpmn", "Diagramas BPMN", "Diagramas, exportação e governança de modelagem.", ["view", "create", "edit", "delete", "export", "configure"]),
                _feature("processes.ai_assistant", "Assistente BPMN IA", "Apoio automatizado à modelagem do processo.", ["view", "execute", "configure", "audit"]),
                _feature("processes.execution_contracts", "Contratos de Execução", "Configuração REST/MCP/automatic de atividades.", ["view", "create", "edit", "delete", "configure"]),
                _feature("processes.routines", "Rotinas Vinculadas", "Rotinas derivadas e ligadas ao processo.", ["view", "create", "edit", "delete", "approve"]),
                _feature("processes.instances", "Instâncias de Processo", "Criação e gestão das execuções do processo.", ["view", "create", "edit", "delete", "execute", "change_status"]),
                _feature("processes.executions", "Execuções da Instância", "Passos executados, work logs, pause/resume e histórico.", ["view", "create", "edit", "execute", "change_status", "audit"]),
                _node(
                    "processes.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de processos.",
                    ["view", "create", "edit", "delete", "export", "execute", "configure", "audit"],
                    [
                        _api_group("processes.api.areas", "Áreas", "CRUD de áreas de processo."),
                        _api_group("processes.api.macros", "Macroprocessos", "CRUD de macroprocessos."),
                        _api_group("processes.api.processes", "Processos", "CRUD de processos."),
                        _api_group("processes.api.bpmn", "BPMN", "Diagrama, exportação e bindings BPMN.", ["view", "create", "edit", "delete", "export", "configure"]),
                        _api_group("processes.api.execution_contracts", "Contratos de Execução", "CRUD dos contratos REST/MCP/automatic.", ["view", "create", "edit", "delete", "configure"]),
                        _api_group("processes.api.instances", "Instâncias", "CRUD das instâncias do processo.", ["view", "create", "edit", "delete", "execute", "change_status"]),
                        _api_group("processes.api.instance_runtime", "Runtime", "Timeline, runtime, overlay, pause/resume e execuções.", ["view", "edit", "execute", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "plans",
            "Planos",
            "Planejamento, implantação e participação estratégica.",
            ["view", "create", "edit", "delete", "approve", "export", "configure"],
            [
                _node(
                    "plans.screens",
                    "Telas",
                    "Telas dos planos estratégicos e implantação.",
                    ["view", "export"],
                    [
                        _screen("plans.screens.list", "Lista de Planos", "Lista de planos da empresa."),
                        _screen("plans.screens.detail", "Detalhe do Plano", "Visão detalhada do plano."),
                        _screen("plans.screens.implantation", "Implantação", "Seções e acompanhamento da implantação."),
                    ],
                ),
                _feature("plans.catalog", "Planos", "CRUD principal dos planos.", ["view", "create", "edit", "delete", "approve", "export"]),
                _feature("plans.drivers", "Drivers", "Drivers e direcionadores do plano.", ["view", "create", "edit", "delete"]),
                _feature("plans.participants", "Participantes", "Participantes e responsáveis do plano.", ["view", "create", "edit", "delete", "assign"]),
                _feature("plans.implantation", "Implantação", "Implantação por seção do plano.", ["view", "create", "edit", "approve", "export"]),
                _feature("plans.section_status", "Status por Seção", "Status e fechamento das seções do plano.", ["view", "edit", "change_status", "approve"]),
                _node(
                    "plans.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de planos.",
                    ["view", "create", "edit", "delete", "approve", "export", "assign"],
                    [
                        _api_group("plans.api.plans", "Planos", "CRUD principal dos planos."),
                        _api_group("plans.api.drivers", "Drivers", "CRUD de drivers do plano."),
                        _api_group("plans.api.participants", "Participantes", "CRUD de participantes do plano.", ["view", "create", "edit", "delete", "assign"]),
                        _api_group("plans.api.implantation", "Implantação", "Endpoints de implantação por seção.", ["view", "create", "edit", "approve", "export"]),
                        _api_group("plans.api.section_status", "Status de Seção", "Status de execução e fechamento das seções.", ["view", "edit", "change_status", "approve"]),
                    ],
                ),
            ],
        ),
        _node(
            "indicators",
            "Indicadores",
            "Indicadores, grupos, metas e dados coletados.",
            ["view", "create", "edit", "delete", "approve", "export"],
            [
                _screen("indicators.screens.dashboard", "Dashboard de Indicadores", "Leitura e navegação dos indicadores."),
                _feature("indicators.catalog", "Indicadores", "CRUD dos indicadores.", ["view", "create", "edit", "delete", "approve"]),
                _feature("indicators.groups", "Grupos", "Agrupadores de indicadores.", ["view", "create", "edit", "delete"]),
                _feature("indicators.goals", "Metas", "Metas vinculadas aos indicadores.", ["view", "create", "edit", "delete", "approve"]),
                _feature("indicators.data", "Dados de Indicadores", "Lançamento e carga em lote de dados.", ["view", "create", "edit", "delete", "export"]),
                _node(
                    "indicators.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de indicadores.",
                    ["view", "create", "edit", "delete", "approve", "export"],
                    [
                        _api_group("indicators.api.indicators", "Indicadores", "CRUD de indicadores."),
                        _api_group("indicators.api.groups", "Grupos", "CRUD de grupos."),
                        _api_group("indicators.api.goals", "Metas", "CRUD de metas."),
                        _api_group("indicators.api.data", "Dados", "CRUD e batch de dados de indicadores.", ["view", "create", "edit", "delete", "export"]),
                    ],
                ),
            ],
        ),
        _node(
            "okrs",
            "OKRs",
            "OKRs globais e por área, com key results e desdobramentos.",
            ["view", "create", "edit", "delete", "approve", "export"],
            [
                _screen("okrs.screens.global", "OKRs Globais", "Gestão dos OKRs globais."),
                _screen("okrs.screens.area", "OKRs por Área", "Gestão dos OKRs de área."),
                _feature("okrs.global", "OKRs Globais", "CRUD dos OKRs globais.", ["view", "create", "edit", "delete", "approve"]),
                _feature("okrs.area", "OKRs por Área", "CRUD dos OKRs por área.", ["view", "create", "edit", "delete", "approve"]),
                _feature("okrs.key_results", "Key Results", "Gestão dos key results globais e de área.", ["view", "create", "edit", "delete", "approve"]),
                _node(
                    "okrs.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de OKRs.",
                    ["view", "create", "edit", "delete", "approve", "export"],
                    [
                        _api_group("okrs.api.global", "OKRs Globais", "CRUD de OKRs globais."),
                        _api_group("okrs.api.area", "OKRs por Área", "CRUD de OKRs por área."),
                        _api_group("okrs.api.key_results", "Key Results", "CRUD de key results."),
                    ],
                ),
            ],
        ),
        _node(
            "my_work",
            "My Work",
            "Agenda operacional, atividades pessoais, equipe e empresa.",
            ["view", "create", "edit", "delete", "approve", "export", "change_status"],
            [
                _screen("my_work.screens.dashboard", "Painel My Work", "Painel principal do trabalho diário."),
                _feature("my_work.activities", "Atividades", "Atividades próprias, da equipe e da empresa.", ["view", "create", "edit", "delete", "change_status", "export"]),
                _feature("my_work.comments", "Comentários", "Comentários e interações operacionais.", ["view", "create", "edit", "delete"]),
                _feature("my_work.work_logs", "Work Logs", "Apontamentos e logs operacionais.", ["view", "create", "edit", "delete", "export"]),
                _feature("my_work.filters", "Filtros e Escopos", "Filtros por empresa, colaborador, processo e projeto.", ["view", "configure"]),
                _node(
                    "my_work.api",
                    "APIs REST",
                    "Famílias de endpoints do My Work.",
                    ["view", "create", "edit", "delete", "change_status", "export"],
                    [
                        _api_group("my_work.api.activities", "Atividades", "Consultas e mutações das atividades."),
                        _api_group("my_work.api.comments", "Comentários", "Comentários de atividades.", ["view", "create", "edit", "delete"]),
                        _api_group("my_work.api.work_logs", "Work Logs", "Lançamento e edição de logs operacionais.", ["view", "create", "edit", "delete", "export"]),
                    ],
                ),
            ],
        ),
        _node(
            "contracts",
            "Contratos",
            "Gestão contratual, documentos, partes, itens e termos.",
            ["view", "create", "edit", "delete", "approve", "export", "configure"],
            [
                _screen("contracts.screens.catalog", "Catálogo de Contratos", "Lista e navegação de contratos."),
                _screen("contracts.screens.detail", "Detalhe do Contrato", "Visão detalhada do contrato."),
                _feature("contracts.catalog", "Contratos", "CRUD principal dos contratos.", ["view", "create", "edit", "delete", "approve", "export"]),
                _feature("contracts.parties", "Partes", "Gestão das partes do contrato.", ["view", "create", "edit", "delete"]),
                _feature("contracts.items", "Itens Contratuais", "Itens, billing e componentes financeiros.", ["view", "create", "edit", "delete", "approve"]),
                _feature("contracts.documents", "Documentos", "Documentos e anexos contratuais.", ["view", "create", "edit", "delete", "export"]),
                _feature("contracts.terms", "Termos", "Termos fiscais, financeiros, retenções e gatilhos.", ["view", "create", "edit", "delete", "configure"]),
                _node(
                    "contracts.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo de contratos.",
                    ["view", "create", "edit", "delete", "approve", "export", "configure"],
                    [
                        _api_group("contracts.api.contracts", "Contratos", "CRUD de contratos."),
                        _api_group("contracts.api.documents", "Documentos", "CRUD de documentos contratuais.", ["view", "create", "edit", "delete", "export"]),
                        _api_group("contracts.api.items", "Itens", "CRUD de itens e billing.", ["view", "create", "edit", "delete", "approve"]),
                    ],
                ),
            ],
        ),
        _node(
            "real_estate_auctions",
            "Leilões Imobiliários",
            "Pipeline multi-tenant para triagem, arrematação, diligência e comercialização de imóveis.",
            ["view", "create", "edit", "delete", "triage", "manage_financial_sheet", "generate_pdf", "manage_sources", "export", "configure", "audit"],
            [
                _node(
                    "real_estate_auctions.screens",
                    "Telas",
                    "Telas web do módulo de leilões imobiliários.",
                    ["view", "export"],
                    [
                        _screen("real_estate_auctions.screens.workspace", "Workspace", "Cockpit e pipeline de oportunidades."),
                        _screen("real_estate_auctions.screens.property_detail", "Detalhe do Imóvel", "Visão detalhada de imóvel, diligência e histórico."),
                        _screen("real_estate_auctions.screens.property_form", "Formulário de Imóvel", "Cadastro e edição de oportunidade imobiliária."),
                    ],
                ),
                _feature(
                    "real_estate_auctions.properties",
                    "Imóveis",
                    "CRUD operacional de oportunidades imobiliárias.",
                    ["view", "create", "edit", "delete", "triage", "export"],
                ),
                _feature(
                    "real_estate_auctions.financial_sheets",
                    "Ficha Financeira",
                    "Premissas econômicas, custos, margem e simulação determinística por imóvel.",
                    ["view", "edit", "manage_financial_sheet", "export"],
                ),
                _feature(
                    "real_estate_auctions.sources",
                    "Fontes de Leilão",
                    "Cadastro, governança e importação assistida de fontes.",
                    ["view", "create", "edit", "delete", "manage_sources", "execute", "audit"],
                ),
                _feature(
                    "real_estate_auctions.documents",
                    "Documentos e PDF",
                    "Anexos, edital, matrícula, laudos e relatório executivo.",
                    ["view", "create", "edit", "delete", "generate_pdf", "export"],
                ),
                _node(
                    "real_estate_auctions.api",
                    "APIs REST",
                    "Endpoints tenant-safe do módulo de leilões imobiliários.",
                    ["view", "create", "edit", "delete", "triage", "manage_financial_sheet", "manage_sources", "export", "configure", "audit"],
                    [
                        _api_group("real_estate_auctions.api.properties", "Imóveis", "Listagem, detalhe, criação, atualização e arquivamento.", ["view", "create", "edit", "delete", "triage", "export"]),
                        _api_group("real_estate_auctions.api.settings", "Configurações", "Habilitação e customização por tenant.", ["view", "edit", "configure", "audit"]),
                        _api_group("real_estate_auctions.api.sources", "Fontes", "Fontes e jobs de importação assistida.", ["view", "create", "edit", "delete", "manage_sources", "execute", "audit"]),
                    ],
                ),
                _node(
                    "real_estate_auctions.mcp",
                    "Tools MCP de Leilões",
                    "Tools MCP para leitura operacional, triagem e mutações governadas.",
                    ["view", "execute", "configure", "audit"],
                    [
                        _tool("real_estate_auctions.mcp.read", "Leitura Operacional", "Workspace, listagem e detalhe de imóveis.", ["view", "execute", "audit"]),
                        _tool("real_estate_auctions.mcp.write", "Mutações Governadas", "Criação, atualização e arquivamento com gate humano quando aplicável.", ["view", "execute", "configure", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "financial",
            "Financeiro",
            "Operação financeira, orçamento, importação, relatórios e automações.",
            ["view", "create", "edit", "delete", "approve", "reject", "export", "configure", "execute"],
            [
                _node(
                    "financial.screens",
                    "Telas",
                    "Telas operacionais do financeiro.",
                    ["view", "export"],
                    [
                        _screen("financial.screens.dashboard", "Dashboard Financeiro", "Cockpit financeiro."),
                        _screen("financial.screens.entries", "Lançamentos", "Lista e manutenção de títulos."),
                        _screen("financial.screens.entry_manage", "Gestão de Lançamento", "Manutenção detalhada do lançamento."),
                        _screen("financial.screens.schedules", "Títulos / Schedules", "Lista e manutenção de títulos."),
                        _screen("financial.screens.reports", "Relatórios", "Relatórios financeiros."),
                        _screen("financial.screens.catalogs", "Catálogos", "Catálogos financeiros."),
                        _screen("financial.screens.reconciliation", "Conciliação", "Conciliação e matching."),
                        _screen("financial.screens.imports", "Importações", "Lotes e classificações importadas."),
                        _screen("financial.screens.budget", "Orçamento", "Workspace e matriz orçamentária."),
                        _screen("financial.screens.domain_enablements", "Habilitações de Domínio", "Ligação de domínios financeiros."),
                    ],
                ),
                _feature("financial.entries", "Lançamentos", "Contas a pagar/receber, títulos e liquidações.", ["view", "create", "edit", "delete", "approve", "reject", "export"]),
                _feature("financial.settlements", "Liquidações", "Liquidações e componentes financeiros.", ["view", "create", "edit", "delete", "approve", "reject"]),
                _feature("financial.schedules", "Schedules / Títulos", "Títulos financeiros recorrentes e eventuais.", ["view", "create", "edit", "delete", "approve", "export"]),
                _feature("financial.catalogs", "Catálogos", "Plano de contas, contas bancárias, centros de custo, métodos de pagamento e domínios.", ["view", "create", "edit", "delete", "configure", "export"]),
                _feature("financial.reports", "Relatórios", "Relatórios de fluxo, DRE, razão, extratos e derivados.", ["view", "export"]),
                _feature("financial.reconciliation", "Conciliação", "Conciliação bancária e matching operacional.", ["view", "create", "edit", "approve", "reject", "execute"]),
                _feature("financial.imports", "Importações", "Importação, classificação e processamento de lotes.", ["view", "create", "edit", "delete", "approve", "execute"]),
                _feature("financial.domain_enablements", "Habilitação de Domínios", "Mapeamento manual e automático de domínios financeiros.", ["view", "create", "edit", "delete", "configure"]),
                _feature("financial.budget", "Orçamento", "Versões, linhas, valores, contratos e documentos orçamentários.", ["view", "create", "edit", "delete", "approve", "export", "configure"]),
                _feature("financial.automation", "Automação Financeira", "Regras, execuções e documentos automatizados.", ["view", "create", "edit", "delete", "approve", "execute", "audit"]),
                _node(
                    "financial.api",
                    "APIs REST",
                    "Famílias de endpoints do módulo financeiro.",
                    ["view", "create", "edit", "delete", "approve", "reject", "export", "configure", "execute"],
                    [
                        _api_group("financial.api.entries", "Lançamentos", "CRUD de entries, settlements e anexos.", ["view", "create", "edit", "delete", "approve", "reject", "export"]),
                        _api_group("financial.api.schedules", "Schedules", "CRUD de schedules financeiros.", ["view", "create", "edit", "delete", "approve", "export"]),
                        _api_group("financial.api.catalogs", "Catálogos", "Catálogos financeiros e toggles de ativação.", ["view", "create", "edit", "delete", "configure", "export"]),
                        _api_group("financial.api.reports", "Relatórios", "Geração e exportação de relatórios.", ["view", "export"]),
                        _api_group("financial.api.imports", "Importações", "Lotes, classificação, IA ranking e reconciliação.", ["view", "create", "edit", "delete", "approve", "execute"]),
                        _api_group("financial.api.reconciliation", "Conciliação", "Matching, revisão e aprovação.", ["view", "edit", "approve", "reject", "execute"]),
                        _api_group("financial.api.budget", "Orçamento", "Workspace, versões, linhas, documentos e schedules orçamentários.", ["view", "create", "edit", "delete", "approve", "export", "configure"]),
                    ],
                ),
                _node(
                    "financial.mcp",
                    "Tools MCP Financeiras",
                    "Famílias de tools MCP do financeiro.",
                    ["view", "execute", "configure", "audit"],
                    [
                        _tool("financial.mcp.entries", "Entries / Ledger", "Tools MCP para lançamento e leitura financeira.", ["view", "execute", "audit"]),
                        _tool("financial.mcp.reports", "Relatórios", "Tools MCP de geração de relatórios financeiros.", ["view", "execute", "export"]),
                        _tool("financial.mcp.catalogs", "Catálogos", "Tools MCP de catálogos financeiros.", ["view", "execute", "configure"]),
                        _tool("financial.mcp.budget", "Orçamento", "Tools MCP para orçamento matricial.", ["view", "execute", "configure", "audit"]),
                        _tool("financial.mcp.reconciliation", "Conciliação", "Tools MCP para conciliação e classificação.", ["view", "execute", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "incentives",
            "Incentivos",
            "Regras de incentivo, cálculos, participantes e governabilidade.",
            ["view", "create", "edit", "delete", "approve", "export", "configure"],
            [
                _screen("incentives.screens.dashboard", "Painel de Incentivos", "Gestão do módulo de incentivos."),
                _feature("incentives.rulesets", "Rule Sets", "Conjuntos e regras de incentivo.", ["view", "create", "edit", "delete", "approve", "configure"]),
                _feature("incentives.governability", "Matriz de Governabilidade", "Matriz de governabilidade e elegibilidade.", ["view", "create", "edit", "delete", "approve"]),
                _feature("incentives.calculations", "Cálculos", "Cálculo e evidência dos incentivos.", ["view", "create", "edit", "approve", "export"]),
                _feature("incentives.participants", "Participantes", "Participantes e vínculos de incentivo.", ["view", "create", "edit", "delete", "assign"]),
                _node(
                    "incentives.mcp",
                    "Tools MCP de Incentivo",
                    "Tools MCP do domínio de incentivos.",
                    ["view", "execute", "configure", "audit"],
                    [
                        _tool("incentives.mcp.rules", "Rules / Governability", "Tools MCP para regras e governabilidade.", ["view", "execute", "configure"]),
                        _tool("incentives.mcp.calculations", "Calculations", "Tools MCP para cálculo e leitura de incentivos.", ["view", "execute", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "knowledge",
            "Conhecimento Corporativo",
            "Busca citada, manual interativo e fontes autorizadas por empresa.",
            ["view", "execute", "configure", "audit"],
            [
                _feature(
                    "knowledge.search",
                    "Busca e Respostas",
                    "Consulta tenant-safe com abstenção, claims e citações.",
                    ["view", "execute", "audit"],
                ),
                _tool(
                    "knowledge.mcp.answers",
                    "Tools MCP de Conhecimento",
                    "Ajuda do produto e respostas organizacionais citadas.",
                    ["view", "execute", "audit"],
                ),
            ],
        ),
        _node(
            "operations",
            "Operations / IA / MCP Console",
            "Console operacional, monitoramento, auditoria e capabilities.",
            ["view", "create", "edit", "delete", "approve", "export", "configure", "grant", "audit", "execute"],
            [
                _node(
                    "operations.screens",
                    "Telas",
                    "Telas do cockpit operacional IA/MCP e auditoria.",
                    ["view", "export"],
                    [
                        _screen("operations.screens.ai_overview", "Visão Geral IA", "Entrada do hub de IA e MCP."),
                        _screen("operations.screens.ai_tools_catalog", "Catálogo de Tools", "Catálogo tool-first de IA/MCP."),
                        _screen("operations.screens.ai_permissions", "Permissões IA", "Página de permissões e acessos IA."),
                        _screen("operations.screens.ai_monitoring", "AI Monitoring", "Painel de monitoramento operacional IA."),
                        _screen("operations.screens.ai_mcp_console", "Console IA / MCP", "Console operacional de capabilities e MCP."),
                        _screen("operations.screens.audit", "Audit", "Auditoria operacional do sistema."),
                    ],
                ),
                _feature("operations.capabilities", "Capabilities IA", "Catálogo, grants, company settings e rollout das capabilities.", ["view", "create", "edit", "delete", "configure", "grant", "audit"]),
                _feature("operations.monitoring", "Monitoring", "Requests operacionais, painel, export PDF e fila de monitoramento.", ["view", "create", "edit", "delete", "export", "audit"]),
                _feature("operations.mcp_console", "Console MCP", "Frontend state, bootstrap session, snippets e catálogo tool-first.", ["view", "configure", "export", "audit"]),
                _feature("operations.audit", "Auditoria Operacional", "Leitura de auditoria operacional e logs governados.", ["view", "export", "audit"]),
                _node(
                    "operations.api",
                    "APIs REST",
                    "Famílias de endpoints das operações IA/MCP.",
                    ["view", "create", "edit", "delete", "export", "configure", "grant", "audit"],
                    [
                        _api_group("operations.api.monitoring", "AI Monitoring", "Painel, requests e relatório PDF.", ["view", "create", "edit", "delete", "export", "audit"]),
                        _api_group("operations.api.capabilities", "Capabilities", "Frontend state, grants, company settings, rollout e audit log.", ["view", "create", "edit", "delete", "configure", "grant", "audit"]),
                        _api_group("operations.api.mcp_console", "MCP Console", "Bootstrap session, frontend state, snippets e catálogo.", ["view", "configure", "export", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "agents",
            "Agents / Sapiens Web",
            "Painéis dos agentes, chat, histórico, diagnósticos e cadastro assistido.",
            ["view", "create", "edit", "delete", "approve", "reject", "execute", "configure", "audit"],
            [
                _node(
                    "agents.screens",
                    "Telas",
                    "Telas dos agentes e squads conversacionais.",
                    ["view", "export"],
                    [
                        _screen("agents.screens.sapiens", "Sapiens", "Entrada web do Sapiens."),
                        _screen("agents.screens.board", "Agents Board", "Board operacional dos agentes."),
                        _screen("agents.screens.logs", "Agents Logs", "Logs conversacionais e de execução."),
                        _screen("agents.screens.engineering", "Agents Engineering", "Superfície de engenharia."),
                        _screen("agents.screens.planejamento", "Agent Planejamento", "Squad de planejamento."),
                        _screen("agents.screens.processos", "Agent Processos", "Squad de processos."),
                        _screen("agents.screens.rotina", "Agent Rotina", "Squad de rotina."),
                        _screen("agents.screens.performance", "Agent Performance", "Squad de performance."),
                        _screen("agents.screens.estrategico", "Agent Estratégico", "Squad estratégico."),
                        _screen("agents.screens.cadastro", "Agent Cadastro", "Cadastro assistido."),
                    ],
                ),
                _feature("agents.chat", "Chat de Agentes", "Troca conversacional com os agentes.", ["view", "create", "execute", "audit"]),
                _feature("agents.diagnostics", "Diagnósticos", "Diagnóstico e health operacional dos agentes.", ["view", "execute", "audit"]),
                _feature("agents.actions", "Ações Pendentes / Aprovações", "Ações pendentes, aprovações e rollback.", ["view", "approve", "reject", "execute", "audit"]),
                _feature("agents.history", "Histórico e Contatos", "Histórico conversacional e agenda de contatos.", ["view", "export", "audit"]),
                _feature("agents.cadastro_company", "Cadastro Assistido de Empresa", "Fluxo iniciar/processar/finalizar do onboarding assistido.", ["view", "create", "edit", "execute", "approve"]),
                _node(
                    "agents.api",
                    "APIs REST",
                    "Famílias de endpoints dos agents web.",
                    ["view", "create", "edit", "delete", "approve", "reject", "execute", "audit"],
                    [
                        _api_group("agents.api.chat", "Chat", "Endpoint de chat dos agentes.", ["view", "create", "execute", "audit"]),
                        _api_group("agents.api.diagnostics", "Diagnósticos", "Health e diagnósticos.", ["view", "execute", "audit"]),
                        _api_group("agents.api.actions", "Ações Pendentes", "Pending actions, approvals e rollback.", ["view", "approve", "reject", "execute", "audit"]),
                        _api_group("agents.api.history", "Histórico", "Histórico conversacional e contatos.", ["view", "export", "audit"]),
                        _api_group("agents.api.cadastro_company", "Cadastro Assistido", "Iniciar, processar e finalizar cadastro assistido.", ["view", "create", "edit", "execute", "approve"]),
                    ],
                ),
            ],
        ),
        _node(
            "mcp",
            "Tools MCP Sistêmicas",
            "Superfícies MCP user/admin/analytics/ops e tools publicadas por domínio.",
            ["view", "execute", "configure", "grant", "audit", "export"],
            [
                _node(
                    "mcp.surfaces",
                    "Surfaces",
                    "Servidores MCP por superfície.",
                    ["view", "execute", "configure", "audit"],
                    [
                        _tool("mcp.surfaces.user", "User MCP", "Surface user do APP32.", ["view", "execute", "audit"]),
                        _tool("mcp.surfaces.admin", "Admin MCP", "Surface admin do APP32.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.surfaces.analytics", "Analytics MCP", "Surface analytics do APP32.", ["view", "execute", "audit", "export"]),
                        _tool("mcp.surfaces.ops", "Ops MCP", "Surface ops do APP32.", ["view", "execute", "configure", "audit"]),
                    ],
                ),
                _node(
                    "mcp.catalog",
                    "Catálogo de Tools",
                    "Tools MCP canônicas já identificadas no sistema.",
                    ["view", "execute", "configure", "grant", "audit", "export"],
                    [
                        _tool("mcp.catalog.permission_matrix", "Permission Matrix", "Describe permission matrix por perfil/surface.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.profile_contracts", "Profile Contracts", "Describe contratos de perfil.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.feature_catalog", "Feature Catalog", "Catálogo de features publicadas.", ["view", "execute", "audit", "export"]),
                        _tool("mcp.catalog.operational_readiness", "Operational Readiness", "Readiness operacional MCP/IA.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.release_checklist", "Release Checklist", "Checklist de release MCP.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.usage_dashboard", "Usage Dashboard", "Métricas e usage analytics.", ["view", "execute", "audit", "export"]),
                        _tool("mcp.catalog.session_company", "Session Company", "Scope de empresa da sessão MCP.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.catalog.sapiens_activation", "Sapiens Activation", "Ativação de squads Sapiens.", ["view", "execute", "configure"]),
                        _tool("mcp.catalog.sapiens_factory", "Sapiens Factory", "Assessment e tracing de capabilities.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.catalog.surface_playbook", "Surface Playbook", "Playbooks por surface MCP.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.tool_freeze", "Tool Freeze", "Procedimento de freeze de tools.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.integration_request", "Integration Request", "Requests de integração.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.catalog.instruction_registry", "Instruction Registry", "Registry de instruções do runtime.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.catalog.analysis_catalog", "Analysis Catalog", "Catálogo analítico e discovery.", ["view", "execute", "audit", "export"]),
                        _tool("mcp.catalog.crud_contracts", "CRUD Contracts", "Contracts CRUD/MCP publicados.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.domain_playbooks", "Domain Playbooks", "Playbooks por domínio.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.external_ai_onboarding", "External AI Onboarding", "Onboarding de IA externa.", ["view", "execute", "configure"]),
                        _tool("mcp.catalog.external_llm_factory", "External LLM Factory", "Factory de LLMs externos.", ["view", "execute", "configure", "audit"]),
                        _tool("mcp.catalog.squad_runtime", "Squad Runtime", "Runtime de squads e manifestos.", ["view", "execute", "audit"]),
                        _tool("mcp.catalog.work_journey", "Work Journey", "Tools MCP de work journey.", ["view", "execute", "configure", "audit"]),
                    ],
                ),
            ],
        ),
        _node(
            "integrations",
            "Integrações e Webhooks",
            "Tokens operacionais, webhooks e requests de integração.",
            ["view", "create", "edit", "delete", "configure", "execute", "audit"],
            [
                _feature("integrations.requests", "Integration Requests", "Solicitações de integração e trilha operacional.", ["view", "create", "edit", "delete", "configure", "audit"]),
                _feature("integrations.user_mcp_tokens", "User MCP Tokens", "Tokens MCP administrativos e runtime.", ["view", "create", "edit", "delete", "configure", "audit"]),
                _feature("integrations.webhooks.telegram", "Webhook Telegram", "Recepção e execução do webhook Telegram.", ["view", "execute", "configure", "audit"]),
                _feature("integrations.mcp_http", "MCP HTTP Runtime", "Runtime HTTP do MCP exposto ao exterior.", ["view", "execute", "configure", "audit"]),
            ],
        ),
    ]

    @classmethod
    def _decorate_presets(
        cls,
        presets: list[dict[str, Any]] | None,
        *,
        source: str,
        is_system: bool,
    ) -> list[dict[str, Any]]:
        items = []
        for preset in presets or []:
            payload = deepcopy(preset)
            payload.setdefault("source", source)
            payload.setdefault("is_system", is_system)
            payload.setdefault("label", payload.get("name") or payload.get("label"))
            payload.setdefault("key", payload.get("preset_key") or payload.get("key"))
            items.append(payload)
        return items

    @classmethod
    def get_catalog(
        cls,
        *,
        company_presets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        system_presets = cls._decorate_presets(cls.PRESETS, source="system", is_system=True)
        tenant_presets = cls._decorate_presets(
            company_presets,
            source="company",
            is_system=False,
        )
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "catalog_version": cls.CATALOG_VERSION,
            "actions": deepcopy(cls.ACTIONS),
            "presets": system_presets + tenant_presets,
            "preset_groups": {
                "system": system_presets,
                "company": tenant_presets,
            },
            "roots": deepcopy(cls.CATALOG),
        }

    @classmethod
    def action_keys(cls) -> set[str]:
        return {item["key"] for item in cls.ACTIONS}

    @classmethod
    def _iter_nodes(cls, nodes: list[dict[str, Any]]):
        for node in nodes or []:
            yield node
            yield from cls._iter_nodes(node.get("children") or [])

    @classmethod
    def node_map(cls) -> dict[str, dict[str, Any]]:
        if not hasattr(cls, "_node_map_cache"):
            cls._node_map_cache = {
                node["key"]: node for node in cls._iter_nodes(cls.CATALOG)
            }
        return cls._node_map_cache

    @classmethod
    def _normalize_actions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        elif isinstance(value, dict):
            raw_items = [key for key, enabled in value.items() if enabled]
        else:
            return []

        allowed = cls.action_keys()
        normalized: list[str] = []
        for item in raw_items:
            key = str(item or "").strip().lower()
            if key and key in allowed and key not in normalized:
                normalized.append(key)
        return normalized

    @classmethod
    def normalize_payload(cls, payload: Any) -> dict[str, Any]:
        raw = payload if isinstance(payload, dict) else {}
        normalized: dict[str, Any] = {
            "__schema_version__": cls.SCHEMA_VERSION,
            "__catalog_version__": cls.CATALOG_VERSION,
        }

        flat_source = raw.get("permission_flat") if isinstance(raw.get("permission_flat"), dict) else None
        if flat_source:
            raw_items = flat_source.items()
        else:
            raw_items = raw.items()

        for resource_key, actions in raw_items:
            if resource_key in cls.META_KEYS or str(resource_key).startswith("__"):
                continue
            normalized_actions = cls._normalize_actions(actions)
            if normalized_actions:
                normalized[str(resource_key)] = normalized_actions

        return normalized

    @classmethod
    def permission_flat_map(cls, payload: Any) -> dict[str, list[str]]:
        normalized = cls.normalize_payload(payload)
        return {
            key: list(value)
            for key, value in normalized.items()
            if key not in cls.META_KEYS and not str(key).startswith("__")
        }

    @classmethod
    def summarize_permissions(cls, payload: Any) -> dict[str, Any]:
        flat = cls.permission_flat_map(payload)
        resource_count = sum(1 for _, actions in flat.items() if actions)
        granted_actions = sum(len(actions) for actions in flat.values())
        known_labels = []
        node_map = cls.node_map()
        for key in flat.keys():
            node = node_map.get(key)
            if node and node["label"] not in known_labels:
                known_labels.append(node["label"])
        return {
            "resources": resource_count,
            "actions": granted_actions,
            "highlights": known_labels[:6],
        }

    @classmethod
    def has_permission(cls, payload: Any, resource: str, action: str) -> bool:
        resource_key = str(resource or "").strip()
        action_key = str(action or "").strip().lower()
        if not resource_key or not action_key:
            return False
        flat = cls.permission_flat_map(payload)
        return action_key in flat.get(resource_key, [])

    @classmethod
    def tree_for_payload(cls, payload: Any) -> list[dict[str, Any]]:
        flat = cls.permission_flat_map(payload)

        def build(node: dict[str, Any]) -> dict[str, Any]:
            current_actions = flat.get(node["key"], [])
            children = [build(child) for child in node.get("children") or []]
            granted_count = len(current_actions)
            for child in children:
                granted_count += child["granted_count"]

            available_count = len(node.get("actions") or [])
            for child in children:
                available_count += child["available_count"]

            return {
                "key": node["key"],
                "label": node["label"],
                "description": node.get("description"),
                "actions": node.get("actions") or [],
                "selected_actions": current_actions,
                "granted_count": granted_count,
                "available_count": available_count,
                "children": children,
            }

        return [build(root) for root in cls.CATALOG]

    @classmethod
    def serialize_role(cls, role, *, include_tree: bool = False) -> dict[str, Any]:
        payload = role.to_dict()
        payload["permission_flat"] = cls.permission_flat_map(role.permissions)
        payload["permission_summary"] = cls.summarize_permissions(role.permissions)
        payload["permission_catalog_version"] = cls.CATALOG_VERSION
        if include_tree:
            payload["permission_tree"] = cls.tree_for_payload(role.permissions)
        return payload
