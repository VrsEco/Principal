from __future__ import annotations

from typing import Any

from services.integration_catalog_service import IntegrationCatalogService
from services.ai_mcp_console_service import AIMCPConsoleService
from services.operational_audit_service import OperationalAuditService


class AIConfigurationPagesService:
    """Estado simples das páginas de configuração da IA Corporativa."""

    @classmethod
    def build_page(cls, page_key: str, active_company: Any | None = None) -> dict[str, Any]:
        console = AIMCPConsoleService.build_frontend_state(active_company)
        pages = {
            "mcp": cls._build_mcp_page(console),
            "tools": cls._build_tools_page(console),
            "permissions": cls._build_permissions_page(console),
            "monitoring": cls._build_monitoring_page(console, active_company),
        }
        return pages[page_key]

    @staticmethod
    def _base_shell(title: str, eyebrow: str, search_terms: str) -> dict[str, Any]:
        return {
            "title": title,
            "eyebrow": eyebrow,
            "search_terms": search_terms,
            "shortcuts": [
                {"label": "Configurações de Canais", "href": "/channels"},
                {"label": "API / MCP", "href": "/api-mcp"},
                {"label": "Tools", "href": "/tools"},
                {"label": "Capacidades de IA", "href": "/ai-capabilities"},
                {"label": "Monitoramento e Auditoria", "href": "/ai-monitoring"},
            ],
        }

    @classmethod
    def _build_mcp_page(cls, console: dict[str, Any]) -> dict[str, Any]:
        summary = console.get("summary") or {}
        surfaces = console.get("surfaces") or []
        domains = console.get("domains") or []
        onboarding = (console.get("onboarding") or {}).get("steps") or []
        readiness = console.get("readiness_by_phase") or []
        integration_catalog = IntegrationCatalogService.build_catalog()
        integration_cards = integration_catalog.get("integrations") or []
        integration_summary = integration_catalog.get("summary") or {}

        page = cls._base_shell("API / MCP", "IA Corporativa", "mcp superfícies domínios readiness onboarding")
        page.update(
            {
                "intro": "Organize onde a IA atua e o que está liberado.",
                "hero_metrics": [
                    {"label": "Surfaces", "value": len(surfaces)},
                    {"label": "Domínios", "value": len(domains)},
                    {"label": "Gates", "value": int(summary.get("readiness_gates") or 0)},
                ],
                "wizard": {
                    "title": "Assistente API / MCP",
                    "intro": "Me diga o que você precisa e eu te levo para a seção certa.",
                    "steps": [
                        {
                            "step": 1,
                            "question": "O que você quer fazer em API / MCP?",
                            "options": [
                                {
                                    "label": "Ver estrutura",
                                    "description": "Surfaces e domínios.",
                                    "result_title": "Veja a estrutura",
                                    "result_body": "Abra a seção Estrutura para ver surfaces e domínios liberados.",
                                    "target_section": "structure",
                                },
                                {
                                    "label": "Liberar uso",
                                    "description": "Onboarding e readiness.",
                                    "result_title": "Veja liberação",
                                    "result_body": "Abra a seção Liberação para revisar onboarding e gates.",
                                    "target_section": "release",
                                },
                                {
                                    "label": "API / MCP",
                                    "description": "Catálogo e solicitação assistida.",
                                    "result_title": "Abra API / MCP",
                                    "result_body": "Abra a seção API / MCP para ver o catálogo e solicitar uma nova integração.",
                                    "target_section": "integrations",
                                },
                            ],
                        },
                        {
                            "step": 2,
                            "question": "Qual foco agora?",
                            "options": [
                                {
                                    "label": "Surface",
                                    "description": "Onde a IA opera.",
                                    "result_title": "Foque em surfaces",
                                    "result_body": "Vá para Estrutura e veja as surfaces disponíveis.",
                                    "target_section": "structure",
                                },
                                {
                                    "label": "Domínio",
                                    "description": "Assunto ou área.",
                                    "result_title": "Foque em domínios",
                                    "result_body": "Vá para Estrutura e confira os domínios habilitados.",
                                    "target_section": "structure",
                                },
                                {
                                    "label": "Gate",
                                    "description": "Antes de liberar.",
                                    "result_title": "Foque em gates",
                                    "result_body": "Vá para Liberação e veja os gates obrigatórios.",
                                    "target_section": "release",
                                },
                            ],
                        },
                    ],
                },
                "sections": [
                    {
                        "id": "structure",
                        "title": "Estrutura",
                        "summary": "Surfaces e domínios.",
                        "items": [
                            {
                                "title": surface.get("surface", "Surface"),
                                "meta": f"Escopo: {surface.get('default_scope') or '-'}",
                                "description": surface.get("objective") or "Sem descrição.",
                            }
                            for surface in surfaces[:6]
                        ]
                        + [
                            {
                                "title": domain.get("domain", "Domínio"),
                                "meta": ", ".join(domain.get("allowed_surfaces") or []) or "-",
                                "description": domain.get("objective") or "Sem descrição.",
                            }
                            for domain in domains[:8]
                        ],
                    },
                    {
                        "id": "release",
                        "title": "Liberação",
                        "summary": "Onboarding e gates.",
                        "items": [
                            {
                                "title": step.get("title") or step.get("phase") or "Passo",
                                "meta": step.get("step_id") or "-",
                                "description": step.get("required_evidence") or step.get("instruction") or "-",
                            }
                            for step in onboarding[:6]
                        ]
                        + [
                            {
                                "title": str(phase.get("phase", "")).replace("_", " ").title(),
                                "meta": f"{phase.get('gate_count', 0)} gates",
                                "description": f"{phase.get('required_count', 0)} obrigatórios.",
                            }
                            for phase in readiness[:5]
                        ],
                    },
                    {
                        "id": "integrations",
                        "title": "API / MCP",
                        "summary": "Catálogo consultivo e assistente de novas integrações.",
                        "items": [
                            {
                                "title": "API / MCP",
                                "meta": f"{integration_summary.get('total', 0)} integrações mapeadas",
                                "description": "Abra os cards com descrição, modo de operação e instruções de configuração.",
                                "href": "/api-mcp",
                            },
                            {
                                "title": "Assistente de Nova Integração",
                                "meta": "Backlog automático",
                                "description": "Coleta briefing e cria card em AA.J.31 com solicitante, canal e contexto.",
                                "href": "/api-mcp#new-integration-assistant",
                            },
                        ] + [
                            {
                                "title": item.get("title") or "Integração",
                                "meta": f"{item.get('category') or '-'} · {item.get('technical_channel') or '-'}",
                                "description": item.get("summary") or "-",
                            }
                            for item in integration_cards[:4]
                        ],
                    },
                ],
            }
        )
        return page

    @classmethod
    def _build_monitoring_page(cls, console: dict[str, Any], active_company: Any | None = None) -> dict[str, Any]:
        summary = console.get("summary") or {}
        dashboard = (console.get("dashboard") or {}).get("panels") or []
        readiness = console.get("readiness_by_phase") or []
        freeze = (console.get("freeze") or {}).get("triggers") or []
        company_id = getattr(active_company, "id", None)

        audit_panel = {"summary": {"total": 0, "by_source": {}, "by_status": {}}, "events": [], "filters": {"source": "all", "limit": 12}}
        if company_id:
            audit_panel, _error = OperationalAuditService.build_panel(
                company_id=int(company_id),
                allowed_company_ids=[int(company_id)],
                source=None,
                limit=12,
            )
            audit_panel = audit_panel or {"summary": {"total": 0, "by_source": {}, "by_status": {}}, "events": [], "filters": {"source": "all", "limit": 12}}

        audit_summary = audit_panel.get("summary") or {}
        requests: list[dict[str, Any]] = []

        page = cls._base_shell("Monitoramento e Auditoria", "Governança", "monitoramento auditoria logs readiness alertas evidencias timeline backlog pdf")
        page.update(
            {
                "key": "monitoring",
                "intro": "Veja o que aconteceu, o que exige ação e gere a evidência pronta para auditoria e impressão.",
                "hero_metrics": [
                    {"label": "Eventos", "value": int(audit_summary.get("total") or 0)},
                    {"label": "Gates", "value": int(summary.get("readiness_gates") or 0)},
                    {"label": "Travas", "value": int(summary.get("freeze_triggers") or 0)},
                ],
                "monitoring_dashboard": {
                    "summary_cards": [
                        {
                            "label": "Total monitorado",
                            "value": int(audit_summary.get("total") or 0),
                            "description": "Eventos recentes consolidados na empresa ativa.",
                            "tone": "primary",
                        },
                        {
                            "label": "Revisões humanas",
                            "value": int((audit_summary.get("by_source") or {}).get("human_review") or 0),
                            "description": "Evidências registradas por pessoas na operação.",
                            "tone": "neutral",
                        },
                        {
                            "label": "Sapiens / workflows",
                            "value": int((audit_summary.get("by_source") or {}).get("sapiens_workflow") or 0),
                            "description": "Execuções recentes com orquestração e resposta automatizada.",
                            "tone": "accent",
                        },
                        {
                            "label": "Ações de agentes",
                            "value": int((audit_summary.get("by_source") or {}).get("agent_action") or 0),
                            "description": "Ações MCP e agentes com rastreabilidade operacional.",
                            "tone": "warning",
                        },
                    ],
                    "recent_events": audit_panel.get("events") or [],
                    "recent_requests": requests,
                    "request_endpoint": "/api/ai-monitoring/requests",
                    "requests_endpoint": "/api/ai-monitoring/requests",
                    "panel_endpoint": "/api/ai-monitoring/panel",
                    "pdf_export_url": "/api/ai-monitoring/report.pdf",
                    "default_limit": 12,
                    "default_source": "",
                },
                "wizard": {
                    "title": "Assistente de Monitoramento",
                    "intro": "Escolha a leitura que você precisa agora.",
                    "steps": [
                        {
                            "step": 1,
                            "question": "O que você quer ver?",
                            "options": [
                                {
                                    "label": "Prontidão",
                                    "description": "Gates por fase.",
                                    "result_title": "Veja a prontidão",
                                    "result_body": "Abra a seção Prontidão para revisar os gates.",
                                    "target_section": "readiness",
                                },
                                {
                                    "label": "Alertas",
                                    "description": "Freeze e bloqueios.",
                                    "result_title": "Veja os alertas",
                                    "result_body": "Abra a seção Alertas para ver freeze e bloqueios.",
                                    "target_section": "alerts",
                                },
                                {
                                    "label": "Auditoria",
                                    "description": "Linha do tempo operacional.",
                                    "result_title": "Abra a auditoria",
                                    "result_body": "Use a leitura simples acima ou o atalho da seção Auditoria para aprofundar a análise.",
                                    "target_section": "audit",
                                },
                            ],
                        }
                    ],
                },
                "sections": [
                    {
                        "id": "readiness",
                        "title": "Prontidão",
                        "summary": "Gates por fase.",
                        "items": [
                            {
                                "title": str(phase.get("phase", "")).replace("_", " ").title(),
                                "meta": f"{phase.get('gate_count', 0)} gates",
                                "description": f"{phase.get('required_count', 0)} obrigatórios.",
                            }
                            for phase in readiness[:6]
                        ],
                    },
                    {
                        "id": "alerts",
                        "title": "Alertas",
                        "summary": "Freeze e atenção.",
                        "items": [
                            {
                                "title": trigger.get("trigger") or "Trigger",
                                "meta": trigger.get("severity") or "-",
                                "description": trigger.get("recommended_action") or trigger.get("description") or "-",
                            }
                            for trigger in freeze[:8]
                        ],
                    },
                    {
                        "id": "audit",
                        "title": "Auditoria",
                        "summary": "Abrir a timeline completa ou formalizar uma solicitação no backlog.",
                        "items": [
                            {
                                "title": panel.get("title") or "Painel",
                                "meta": panel.get("default_visualization") or "-",
                                "description": panel.get("objective") or "-",
                            }
                            for panel in dashboard[:6]
                        ] + [
                            {
                                "title": "Abrir auditoria operacional",
                                "meta": "/operations/audit",
                                "description": "Linha do tempo de eventos sensíveis, workflows e revisão humana.",
                                "href": "/operations/audit",
                            },
                            {
                                "title": "Exportar relatório PDF",
                                "meta": "/api/ai-monitoring/report.pdf",
                                "description": "Gera um PDF pronto para impressão com base nos filtros da leitura simples acima.",
                                "href": "/api/ai-monitoring/report.pdf",
                            },
                        ],
                    },
                ],
            }
        )
        return page

    @classmethod
    def _build_tools_page(cls, console: dict[str, Any]) -> dict[str, Any]:
        summary = console.get("summary") or {}
        catalog = console.get("catalog") or {}
        tools = catalog.get("tools") or []
        risk_distribution = catalog.get("risk_distribution") or []
        tool_first_domains = (console.get("tool_first_catalog") or {}).get("domains") or []

        page = cls._base_shell("Tools", "IA Corporativa", "tools risco gate dominio catalogo")
        page.update(
            {
                "intro": "Escolha o que a IA pode usar e com qual cuidado.",
                "hero_metrics": [
                    {"label": "Tools", "value": int(summary.get("catalog_tools") or 0)},
                    {"label": "Com gate", "value": int(summary.get("human_gate_tools") or 0)},
                    {"label": "Críticas", "value": int(summary.get("critical_tools") or 0)},
                ],
                "wizard": {
                    "title": "Assistente de Tools",
                    "intro": "Escolha a dúvida e eu mostro a parte certa.",
                    "steps": [
                        {
                            "step": 1,
                            "question": "O que você quer revisar?",
                            "options": [
                                {
                                    "label": "Risco",
                                    "description": "Baixo, médio ou crítico.",
                                    "result_title": "Revise riscos",
                                    "result_body": "Abra a seção Riscos para ver a distribuição atual.",
                                    "target_section": "risk",
                                },
                                {
                                    "label": "Lista de tools",
                                    "description": "O catálogo disponível.",
                                    "result_title": "Veja o catálogo",
                                    "result_body": "Abra a seção Catálogo para ver as tools principais.",
                                    "target_section": "catalog",
                                },
                                {
                                    "label": "Cobertura por domínio",
                                    "description": "Onde cada tool entra.",
                                    "result_title": "Veja os domínios",
                                    "result_body": "Abra a seção Domínios para ver a cobertura atual.",
                                    "target_section": "domains",
                                },
                            ],
                        }
                    ],
                },
                "sections": [
                    {
                        "id": "risk",
                        "title": "Riscos",
                        "summary": "Visão rápida do risco.",
                        "items": [
                            {
                                "title": f"Risco {item.get('risk', '-').title()}",
                                "meta": f"{item.get('count', 0)} tools",
                                "description": "Distribuição atual do catálogo.",
                            }
                            for item in risk_distribution
                        ],
                    },
                    {
                        "id": "catalog",
                        "title": "Catálogo",
                        "summary": "Tools principais.",
                        "items": [
                            {
                                "title": tool.get("name") or "Tool",
                                "meta": f"{tool.get('domain') or '-'} · {tool.get('risk') or '-'}",
                                "description": tool.get("description") or "Sem descrição.",
                            }
                            for tool in tools[:12]
                        ],
                    },
                    {
                        "id": "domains",
                        "title": "Domínios",
                        "summary": "Cobertura por domínio.",
                        "items": [
                            {
                                "title": domain.get("title") or domain.get("key") or "Domínio",
                                "meta": f"{domain.get('status') or '-'} · {domain.get('surface') or '-'}",
                                "description": domain.get("description") or "Sem descrição.",
                            }
                            for domain in tool_first_domains[:8]
                        ],
                    },
                ],
            }
        )
        return page

    @classmethod
    def _build_permissions_page(cls, console: dict[str, Any]) -> dict[str, Any]:
        profiles = console.get("profiles") or []
        permissions = console.get("permissions") or []
        registration_links = console.get("registration_links") or []
        configuration_links = console.get("configuration_links") or []
        readiness = console.get("readiness") or {}

        page = cls._base_shell("Permissões e Configurações", "IA Corporativa", "permissoes usuarios perfis cadastros parametros liberacoes")
        page.update(
            {
                "intro": "Defina quem pode usar, o que precisa estar pronto e o que pode ser liberado.",
                "hero_metrics": [
                    {"label": "Perfis", "value": len(profiles)},
                    {"label": "Matrizes", "value": len(permissions)},
                    {"label": "Cadastros", "value": len(registration_links)},
                ],
                "wizard": {
                    "title": "Assistente de Permissões",
                    "intro": "Escolha o foco e eu aponto a área certa.",
                    "steps": [
                        {
                            "step": 1,
                            "question": "O que você quer ajustar?",
                            "options": [
                                {
                                    "label": "Usuários e perfis",
                                    "description": "Quem usa o quê.",
                                    "result_title": "Revise acessos",
                                    "result_body": "Abra a seção Acessos para ver usuários, perfis e regras.",
                                    "target_section": "access",
                                },
                                {
                                    "label": "Cadastros-base",
                                    "description": "O que falta preparar.",
                                    "result_title": "Revise cadastros",
                                    "result_body": "Abra a seção Cadastros para ver os atalhos principais.",
                                    "target_section": "registrations",
                                },
                                {
                                    "label": "Liberação",
                                    "description": "O que precisa estar pronto.",
                                    "result_title": "Revise liberação",
                                    "result_body": "Abra a seção Liberação para ver critérios e bloqueios.",
                                    "target_section": "release",
                                },
                            ],
                        }
                    ],
                },
                "sections": [
                    {
                        "id": "access",
                        "title": "Acessos",
                        "summary": "Perfis e permissões.",
                        "items": [
                            {
                                "title": profile.get("profile") or "Perfil",
                                "meta": profile.get("default_surface") or "-",
                                "description": f"Domínios: {', '.join(profile.get('allowed_domains') or []) or '-'}",
                            }
                            for profile in profiles[:6]
                        ]
                        + [
                            {
                                "title": f"{matrix.get('profile') or '-'} / {matrix.get('surface') or '-'}",
                                "meta": matrix.get("default_scope") or "-",
                                "description": matrix.get("summary") or "Sem resumo.",
                            }
                            for matrix in permissions[:6]
                        ],
                    },
                    {
                        "id": "registrations",
                        "title": "Cadastros",
                        "summary": "Atalhos do dia a dia.",
                        "items": [
                            {
                                "title": item.get("title") or "Cadastro",
                                "meta": item.get("href") or "-",
                                "description": item.get("description") or "Sem descrição.",
                                "href": item.get("href"),
                            }
                            for item in registration_links + configuration_links[:1]
                        ],
                    },
                    {
                        "id": "release",
                        "title": "Liberação",
                        "summary": "Critérios e bloqueios.",
                        "items": [
                            {
                                "title": "Critério de abertura",
                                "meta": "Obrigatório",
                                "description": item,
                            }
                            for item in (readiness.get("opening_criteria") or [])[:6]
                        ]
                        + [
                            {
                                "title": "Condição de bloqueio",
                                "meta": "Bloqueia",
                                "description": item,
                            }
                            for item in (readiness.get("blocking_conditions") or [])[:6]
                        ],
                    },
                ],
            }
        )
        return page
