from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from database.postgresql_db import list_integrations
from models import AIAgent, AgentAction, AgentMessage, WorkflowExecutionLog, WorkflowGapCandidate, User
from services.ai_mcp_console_service import AIMCPConsoleService
from services.operational_audit_service import OperationalAuditService
from services.workflow_gap_service import build_workflow_gap_metrics
from services.workflow_usage_service import build_workflow_usage_metrics


class AIFrontendHubService:
    """Monta o estado do frontend de IA do APP32 sem criar superfícies artificiais."""

    RECENT_WINDOW_DAYS = 30
    HERO_WINDOW_DAYS = 7

    @classmethod
    def build_frontend_state(cls, active_company: Any | None = None) -> dict[str, Any]:
        company_id = getattr(active_company, "id", None)
        agents = AIAgent.query.order_by(AIAgent.name.asc()).all()
        integrations = list_integrations(company_id=company_id) or []
        console = AIMCPConsoleService.build_frontend_state(active_company)
        overview = cls._build_overview(
            company_id=company_id,
            agents=agents,
            integrations=integrations,
            console_summary=console["summary"],
        )

        summary = {
            "active_agents": sum(1 for agent in agents if agent.status == "active"),
            "total_agents": len(agents),
            "integrations_total": len(integrations),
            "mcp_tools_total": int(console["summary"]["catalog_tools"]),
            "human_gate_tools": int(console["summary"]["human_gate_tools"]),
            "readiness_gates": int(console["summary"]["readiness_gates"]),
            "logs_total": int((overview.get("communication") or {}).get("total_logs") or 0),
            "audit_total": int((overview.get("audit") or {}).get("recent_total") or 0),
            "workflow_recent_total": int((overview.get("executive") or {}).get("recent_executions") or 0),
            "pending_approvals": int((overview.get("executive") or {}).get("pending_approvals") or 0),
            "workflow_gaps": int((overview.get("executive") or {}).get("workflow_gaps_recent") or 0),
        }

        pillars = [
            {
                "key": "overview",
                "title": "Visão Geral",
                "eyebrow": "Entrada recomendada",
                "description": "Central para entender operação, cobertura MCP, governança e pontos críticos reais.",
                "accent": "primary",
                "items": [
                    cls._item(
                        "API / MCP",
                        "Hub já existente para catálogo, surfaces, readiness, onboarding e governança MCP.",
                        "/api-mcp",
                        status="existente",
                        badge=f"{summary['mcp_tools_total']} tools",
                    ),
                    cls._item(
                        "Mapa de integrações",
                        "Superfície atual para provedores, credenciais e conectividade externa.",
                        "/channels",
                        status="existente",
                        badge=f"{summary['integrations_total']} integrações",
                    ),
                    cls._item(
                        "Auditoria operacional",
                        "Linha do tempo de workflows, revisões humanas e ações de agentes com escopo tenant-safe.",
                        "/operations/audit",
                        status="existente",
                        badge=f"{summary['audit_total']} eventos recentes",
                    ),
                ],
            },
            {
                "key": "configuration",
                "title": "Configuração",
                "eyebrow": "Administração",
                "description": "Concentra parâmetros, conexões, agentes e padrões operacionais sem misturar execução.",
                "accent": "blue",
                "items": [
                    cls._item(
                        "Conexões",
                        "Reaproveita a tela atual de integrações para credenciais, providers e webhooks.",
                        "/channels",
                        status="existente",
                    ),
                    cls._item(
                        "Sapiens e superfícies IA",
                        "Centraliza Sapiens, wrappers de domínio e onboarding assistido sem proliferar agentes de tela.",
                        "/sapiens",
                        status="existente",
                        badge=f"{summary['total_agents']} agentes",
                    ),
                    cls._item(
                        "Modelos e políticas",
                        "Hoje concentrado no console IA/MCP; futura extração deve virar tela dedicada sem duplicação.",
                        "/api-mcp",
                        status="consolidado",
                    ),
                    cls._item(
                        "Inventário de capabilities",
                        "Mapa unificado de capabilities, integrações, workflows e automações governadas.",
                        "/ai-capability-inventory",
                        status="existente",
                    ),
                ],
            },
            {
                "key": "integrations",
                "title": "Interoperabilidade",
                "eyebrow": "Interoperabilidade",
                "description": "Separa claramente MCP, API REST, tools e provedores externos.",
                "accent": "violet",
                "items": [
                    cls._item(
                        "API / MCP",
                        "Catálogo operacional, surfaces, permissões e readiness do ecossistema MCP.",
                        "/api-mcp",
                        status="existente",
                    ),
                    cls._item(
                        "Tools",
                        "Descoberta atual de capabilities via console MCP e gestão de providers pela tela de integrações.",
                        "/tools",
                        status="consolidado",
                        badge=f"{summary['human_gate_tools']} com gate",
                    ),
                    cls._item(
                        "API REST",
                        "A camada REST ainda está distribuída por domínio; manter visível no hub evita criar tela vazia agora.",
                        None,
                        status="planejado",
                    ),
                    cls._item(
                        "Webhooks e provedores",
                        "Cadastro operacional já existente para IA, e-mail, WhatsApp, Telegram e Instagram.",
                        "/channels",
                        status="existente",
                    ),
                ],
            },
            {
                "key": "orchestration",
                "title": "Orquestração",
                "eyebrow": "Execução",
                "description": "Agrupa agentes, automações, execuções e workflows como camada operacional de IA.",
                "accent": "emerald",
                "items": [
                    cls._item(
                        "Sapiens",
                        "Hub principal de IA do APP32, de onde partem as jornadas e o uso de tools por domínio.",
                        "/sapiens",
                        status="existente",
                    ),
                    cls._item(
                        "Automações",
                        "Malha consolidada de jobs, rotinas e automações event-driven já acessível pela IA Corporativa.",
                        "/ai-automation-mesh",
                        status="existente",
                    ),
                    cls._item(
                        "Execuções",
                        "Workflows, ações e trilhas operacionais já podem ser observados sem nova tela fake.",
                        "/operations/audit",
                        status="consolidado",
                    ),
                    cls._item(
                        "Workflows",
                        "Sapiens e console MCP já cobrem parte relevante da execução assistida.",
                        "/sapiens",
                        status="consolidado",
                    ),
                ],
            },
            {
                "key": "governance",
                "title": "Governança",
                "eyebrow": "Controle e evidência",
                "description": "Logs, auditoria, permissões e uso precisam ser visíveis como disciplina operacional, não como detalhe técnico.",
                "accent": "amber",
                "items": [
                    cls._item(
                        "Logs de comunicação",
                        "Permanece no hub para consulta rápida e futura expansão com filtros e retenção.",
                        "#governance-logs",
                        status="existente",
                        local=True,
                        badge=f"{summary['logs_total']} registros",
                    ),
                    cls._item(
                        "Auditoria operacional",
                        "Tela dedicada já pronta para timeline de eventos sensíveis.",
                        "/operations/audit",
                        status="existente",
                    ),
                    cls._item(
                        "Custos e uso",
                        "Hoje agregado no console MCP/readiness; extração dedicada deve vir só quando houver métrica consolidada suficiente.",
                        "/api-mcp",
                        status="consolidado",
                    ),
                    cls._item(
                        "Permissões",
                        "Perfis, surfaces e gates humanos já estão modelados no console operacional.",
                        "/api-mcp",
                        status="existente",
                    ),
                ],
            },
        ]

        return {
            "summary": summary,
            "overview": overview,
            "agents": [agent.to_dict() for agent in agents],
            "pillars": pillars,
            "console_summary": console["summary"],
            "audit_summary": (overview.get("audit") or {}).get("summary") or {},
        }

    @classmethod
    def _build_overview(
        cls,
        *,
        company_id: int | None,
        agents: list[Any],
        integrations: list[Any],
        console_summary: dict[str, Any],
    ) -> dict[str, Any]:
        if not company_id:
            return cls._empty_overview(agents=agents, integrations=integrations, console_summary=console_summary)

        now = datetime.utcnow()
        recent_since = now - timedelta(days=cls.RECENT_WINDOW_DAYS)
        hero_since = now - timedelta(days=cls.HERO_WINDOW_DAYS)

        workflow_recent_items = (
            WorkflowExecutionLog.query
            .filter(
                WorkflowExecutionLog.company_id == company_id,
                WorkflowExecutionLog.created_at >= recent_since,
            )
            .order_by(WorkflowExecutionLog.created_at.desc(), WorkflowExecutionLog.id.desc())
            .limit(120)
            .all()
        )
        latest_workflows = (
            WorkflowExecutionLog.query
            .filter(WorkflowExecutionLog.company_id == company_id)
            .order_by(WorkflowExecutionLog.created_at.desc(), WorkflowExecutionLog.id.desc())
            .limit(6)
            .all()
        )
        workflow_last_7d = (
            WorkflowExecutionLog.query
            .filter(
                WorkflowExecutionLog.company_id == company_id,
                WorkflowExecutionLog.created_at >= hero_since,
            )
            .count()
        )
        workflow_metrics = build_workflow_usage_metrics(workflow_recent_items)
        status_counter = Counter(
            str(item.get("status") or "unknown").strip().lower()
            for item in (workflow_metrics.get("by_status") or [])
            for _ in range(int(item.get("count") or 0))
        )
        failed_executions = int(status_counter.get("failed", 0))
        pending_approvals = (
            AgentAction.query
            .filter(
                AgentAction.company_id == company_id,
                AgentAction.status == "pending",
            )
            .count()
        )
        recent_approvals = (
            AgentAction.query
            .filter(AgentAction.company_id == company_id)
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc())
            .limit(5)
            .all()
        )

        gap_recent_items = (
            WorkflowGapCandidate.query
            .filter(
                WorkflowGapCandidate.company_id == company_id,
                WorkflowGapCandidate.created_at >= recent_since,
            )
            .order_by(WorkflowGapCandidate.created_at.desc(), WorkflowGapCandidate.id.desc())
            .limit(120)
            .all()
        )
        gap_metrics = build_workflow_gap_metrics(gap_recent_items)
        recent_gap_total = int(gap_metrics.get("total") or 0)
        open_gap_total = (
            WorkflowGapCandidate.query
            .filter(
                WorkflowGapCandidate.company_id == company_id,
                WorkflowGapCandidate.status != "resolved",
            )
            .count()
        )

        logs_query = AgentMessage.query.filter(AgentMessage.company_id == company_id)
        total_logs = logs_query.count()
        recent_logs = logs_query.filter(AgentMessage.created_at >= recent_since).count()

        audit_panel = cls._safe_build_audit_panel(company_id=company_id, limit=8)
        audit_events = list(audit_panel.get("events") or [])
        audit_summary = dict(audit_panel.get("summary") or {})

        health = cls._health_status(
            workflow_last_7d=workflow_last_7d,
            failed_executions=failed_executions,
            pending_approvals=pending_approvals,
            open_gap_total=open_gap_total,
        )

        hero_cards = [
            {
                "label": "Saúde operacional",
                "value": health["label"],
                "description": health["description"],
                "tone": health["tone"],
                "badge": health["badge"],
            },
            {
                "label": "Execuções recentes",
                "value": workflow_last_7d,
                "description": f"últimos {cls.HERO_WINDOW_DAYS} dias na empresa ativa",
                "tone": "primary",
                "badge": "Workflows",
            },
            {
                "label": "Approvals pendentes",
                "value": pending_approvals,
                "description": "ações aguardando revisão humana",
                "tone": "warning" if pending_approvals else "success",
                "badge": "Human gate",
            },
            {
                "label": "Workflow gaps",
                "value": recent_gap_total,
                "description": f"detecções nos últimos {cls.RECENT_WINDOW_DAYS} dias",
                "tone": "danger" if recent_gap_total else "success",
                "badge": f"{open_gap_total} abertos",
            },
        ]

        stats_cards = [
            cls._metric_card("Integrações corporativas", len(integrations), "cadastros comuns a todas as empresas", "neutral"),
            cls._metric_card("Tools MCP", int(console_summary.get("catalog_tools") or 0), "catálogo corporativo", "neutral"),
            cls._metric_card("Human gates", int(console_summary.get("human_gate_tools") or 0), "tools com revisão humana", "warning"),
            cls._metric_card("Logs da empresa ativa", int(total_logs), f"{recent_logs} no recorte recente", "neutral"),
            cls._metric_card("Readiness gates", int(console_summary.get("readiness_gates") or 0), "contratos e abertura controlada", "primary"),
        ]

        top_channels = list(workflow_metrics.get("by_channel") or [])[:3]
        top_status = list(workflow_metrics.get("by_status") or [])[:3]
        duplicate_clusters = list(gap_metrics.get("duplicate_clusters") or [])[:3]

        platform_cards = [
            {
                "title": "Operação da empresa ativa",
                "tone": health["tone"],
                "status_label": health["badge"],
                "headline": f"{workflow_metrics.get('total', 0)} execuções no recorte operacional",
                "items": [
                    f"Canal mais usado: {cls._top_label(top_channels, 'channel')}",
                    f"Status dominante: {cls._top_label(top_status, 'status')}",
                    f"Logs de comunicação: {recent_logs} recentes / {total_logs} acumulados",
                ],
            },
            {
                "title": "Governança e revisão humana",
                "tone": "warning" if pending_approvals else "success",
                "status_label": "Revisão humana",
                "headline": f"{pending_approvals} approvals pendentes",
                "items": [
                    f"Eventos recentes de auditoria: {len(audit_events)}",
                    f"Fonte dominante: {cls._top_dict_label(audit_summary.get('by_source') or {})}",
                    f"Status dominante: {cls._top_dict_label(audit_summary.get('by_status') or {})}",
                ],
            },
            {
                "title": "Workflow gaps e exceções",
                "tone": "danger" if recent_gap_total else "success",
                "status_label": "Cobertura de fluxo",
                "headline": f"{recent_gap_total} gaps no recorte + {failed_executions} falhas",
                "items": [
                    f"Abertos no backlog: {open_gap_total}",
                    f"Clusters repetidos: {gap_metrics.get('duplicate_cluster_count', 0)}",
                    f"Canal dominante dos gaps: {cls._top_dict_label(gap_metrics.get('by_channel') or {})}",
                ],
            },
            {
                "title": "Capacidade da plataforma",
                "tone": "primary",
                "status_label": "Corporativo",
                "headline": f"{len(integrations)} integrações e {int(console_summary.get('catalog_tools') or 0)} tools",
                "items": [
                    f"Tools críticas: {int(console_summary.get('critical_tools') or 0)}",
                    f"Painéis de dashboard: {int(console_summary.get('dashboard_panels') or 0)}",
                    f"Matrizes de permissão: {int(console_summary.get('permission_matrices') or 0)}",
                ],
            },
        ]

        user_ids = sorted({item.user_id for item in latest_workflows if getattr(item, "user_id", None)})
        user_map = {}
        if user_ids:
            user_map = {
                user.id: user.name
                for user in User.query.filter(User.id.in_(user_ids)).all()
            }

        recent_workflows_payload = [
            {
                "title": (getattr(item.workflow_option, "title", None) or item.action_key or item.workflow_code or "Execução registrada"),
                "description": cls._truncate(item.request_text or item.response_text or "Execução operacional registrada."),
                "user_label": (user_map.get(item.user_id) or f"ID {item.user_id}") if item.user_id else "Sistema",
                "channel_label": item.channel or "web",
                "tool_label": getattr(item.workflow_option, "title", None) or item.action_key or item.workflow_code or "-",
                "result_label": "Sucesso" if str(item.status or "").lower() in {"completed", "executed", "approved"} else "Falha" if str(item.status or "").lower() in {"failed", "error"} else "Em andamento",
                "meta": [
                    f"Usuário: {user_map.get(item.user_id) or f'ID {item.user_id}' if item.user_id else 'Sistema'}",
                    f"Canal: {item.channel or 'web'}",
                    f"Tool/Menu: {getattr(item.workflow_option, 'title', None) or item.action_key or item.workflow_code or '-'}",
                    f"Resultado: {'Sucesso' if str(item.status or '').lower() in {'completed', 'executed', 'approved'} else 'Falha' if str(item.status or '').lower() in {'failed', 'error'} else 'Em andamento'}",
                ],
                "timestamp": cls._format_dt(item.created_at),
                "tone": cls._status_tone(item.status),
            }
            for item in latest_workflows
        ]

        alerts = cls._build_alerts(
            workflow_last_7d=workflow_last_7d,
            failed_executions=failed_executions,
            pending_approvals=pending_approvals,
            recent_gap_total=recent_gap_total,
            open_gap_total=open_gap_total,
            recent_logs=recent_logs,
            duplicate_clusters=duplicate_clusters,
        )

        quick_actions = [
            cls._action_card("Abrir API / MCP", "/api-mcp", "Catálogo, surfaces, readiness e governança técnica."),
            cls._action_card("Gerir integrações", "/channels", "Conexões, providers, segredos e webhooks corporativos."),
            cls._action_card("Inventário IA", "/ai-capability-inventory", "Mapa canônico de capabilities, workflows, integrações e automações."),
            cls._action_card("Malha de automações", "/ai-automation-mesh", "Scheduler, rotinas, automações financeiras e observabilidade básica."),
            cls._action_card("Abrir Sapiens", "/sapiens", "Hub principal de IA para operar jornadas e superfícies do APP32."),
            cls._action_card("Ver auditoria", "/operations/audit", "Timeline de eventos sensíveis, workflows e revisões humanas."),
        ]

        return {
            "window_days": cls.RECENT_WINDOW_DAYS,
            "hero_cards": hero_cards,
            "stats_cards": stats_cards,
            "platform_cards": platform_cards,
            "recent_workflows": recent_workflows_payload,
            "alerts": alerts,
            "quick_actions": quick_actions,
            "duplicate_clusters": duplicate_clusters,
            "approvals_recent": [
                {
                    "title": item.title,
                    "status": item.status,
                    "description": cls._truncate(item.description),
                    "timestamp": cls._format_dt(item.created_at),
                }
                for item in recent_approvals
            ],
            "executive": {
                "recent_executions": workflow_last_7d,
                "pending_approvals": pending_approvals,
                "workflow_gaps_recent": recent_gap_total,
                "failed_executions": failed_executions,
            },
            "communication": {
                "total_logs": total_logs,
                "recent_logs": recent_logs,
            },
            "audit": {
                "recent_total": len(audit_events),
                "summary": audit_summary,
                "events": audit_events,
            },
            "workflow_metrics": workflow_metrics,
            "gap_metrics": gap_metrics,
        }

    @classmethod
    def _safe_build_audit_panel(cls, *, company_id: int, limit: int) -> dict[str, Any]:
        try:
            panel, _ = OperationalAuditService.build_panel(
                company_id=company_id,
                allowed_company_ids=[company_id],
                limit=limit,
            )
            return panel or {"summary": {}, "events": []}
        except Exception:
            return {"summary": {}, "events": []}

    @classmethod
    def _empty_overview(
        cls,
        *,
        agents: list[Any],
        integrations: list[Any],
        console_summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "window_days": cls.RECENT_WINDOW_DAYS,
            "hero_cards": [],
            "stats_cards": [
                cls._metric_card("Integrações corporativas", len(integrations), "cadastros comuns a todas as empresas", "neutral"),
                cls._metric_card("Tools MCP", int(console_summary.get("catalog_tools") or 0), "catálogo corporativo", "neutral"),
                cls._metric_card("Human gates", int(console_summary.get("human_gate_tools") or 0), "tools com revisão humana", "warning"),
            ],
            "platform_cards": [],
            "recent_workflows": [],
            "alerts": [],
            "quick_actions": [
                cls._action_card("Abrir API / MCP", "/api-mcp", "Catálogo, surfaces, readiness e governança técnica."),
                cls._action_card("Gerir integrações", "/channels", "Conexões, providers, segredos e webhooks corporativos."),
            ],
            "duplicate_clusters": [],
            "approvals_recent": [],
            "executive": {
                "recent_executions": 0,
                "pending_approvals": 0,
                "workflow_gaps_recent": 0,
                "failed_executions": 0,
            },
            "communication": {"total_logs": 0, "recent_logs": 0},
            "audit": {"recent_total": 0, "summary": {}, "events": []},
            "workflow_metrics": {"by_status": [], "by_channel": [], "total": 0},
            "gap_metrics": {"duplicate_clusters": [], "total": 0},
        }

    @staticmethod
    def _metric_card(label: str, value: Any, detail: str, tone: str) -> dict[str, Any]:
        return {"label": label, "value": value, "detail": detail, "tone": tone}

    @staticmethod
    def _action_card(title: str, href: str, description: str) -> dict[str, Any]:
        return {"title": title, "href": href, "description": description}

    @staticmethod
    def _top_label(rows: list[dict[str, Any]], key: str) -> str:
        if not rows:
            return "sem leitura"
        first = rows[0]
        return f"{first.get(key) or 'sem dado'} ({int(first.get('count') or 0)})"

    @staticmethod
    def _top_dict_label(values: dict[str, Any]) -> str:
        if not values:
            return "sem leitura"
        label, count = sorted(values.items(), key=lambda item: (-int(item[1] or 0), str(item[0])))[0]
        return f"{label} ({int(count or 0)})"

    @staticmethod
    def _truncate(value: str, size: int = 150) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= size:
            return text
        return f"{text[: size - 1]}…"

    @staticmethod
    def _format_dt(value: Any) -> str:
        if not value:
            return "-"
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)

    @staticmethod
    def _status_tone(status: Any) -> str:
        normalized = str(status or "").strip().lower()
        if normalized == "failed":
            return "danger"
        if normalized == "approval_pending":
            return "warning"
        if normalized in {"completed", "executed", "approved"}:
            return "success"
        return "neutral"

    @classmethod
    def _health_status(
        cls,
        *,
        workflow_last_7d: int,
        failed_executions: int,
        pending_approvals: int,
        open_gap_total: int,
    ) -> dict[str, str]:
        if failed_executions >= 3 or pending_approvals >= 5:
            return {
                "label": "Crítica",
                "description": "Há acúmulo relevante de falhas ou approvals pendentes exigindo intervenção imediata.",
                "tone": "danger",
                "badge": "Ação imediata",
            }
        if failed_executions > 0 or pending_approvals > 0 or open_gap_total > 0:
            return {
                "label": "Atenção",
                "description": "A plataforma está operando, mas existem pendências de revisão humana, gaps ou falhas recentes.",
                "tone": "warning",
                "badge": "Monitorar",
            }
        if workflow_last_7d > 0:
            return {
                "label": "Saudável",
                "description": "Há operação recente sem sinais fortes de falha, backlog humano ou lacunas críticas de fluxo.",
                "tone": "success",
                "badge": "Em operação",
            }
        return {
            "label": "Baixa atividade",
            "description": "Não há execução recente suficiente para afirmar saúde operacional da empresa ativa.",
            "tone": "neutral",
            "badge": "Sem atividade",
        }

    @classmethod
    def _build_alerts(
        cls,
        *,
        workflow_last_7d: int,
        failed_executions: int,
        pending_approvals: int,
        recent_gap_total: int,
        open_gap_total: int,
        recent_logs: int,
        duplicate_clusters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        if failed_executions:
            alerts.append(
                {
                    "title": "Falhas recentes de workflow",
                    "description": f"Foram registradas {failed_executions} execuções com status failed no recorte operacional.",
                    "tone": "danger",
                }
            )
        if pending_approvals:
            alerts.append(
                {
                    "title": "Approvals aguardando decisão",
                    "description": f"Há {pending_approvals} ações pendentes de aprovação humana na empresa ativa.",
                    "tone": "warning",
                }
            )
        if recent_gap_total:
            alerts.append(
                {
                    "title": "Workflow gaps detectados",
                    "description": f"{recent_gap_total} gaps foram capturados no recorte recente; {open_gap_total} seguem abertos.",
                    "tone": "warning",
                }
            )
        if duplicate_clusters:
            cluster = duplicate_clusters[0]
            alerts.append(
                {
                    "title": "Cluster repetido de gap",
                    "description": f"O padrão '{cluster.get('normalized_intent') or 'sem intenção'}' apareceu {cluster.get('count') or 0} vezes e merece consolidação de fluxo.",
                    "tone": "neutral",
                }
            )
        if workflow_last_7d == 0:
            alerts.append(
                {
                    "title": "Baixa atividade operacional",
                    "description": "Nenhuma execução foi registrada nos últimos 7 dias para a empresa ativa.",
                    "tone": "neutral",
                }
            )
        if recent_logs == 0:
            alerts.append(
                {
                    "title": "Sem logs recentes de comunicação",
                    "description": "Não foram encontrados logs de comunicação no recorte operacional recente.",
                    "tone": "neutral",
                }
            )

        if alerts:
            return alerts[:6]

        return [
            {
                "title": "Operação sem alertas fortes",
                "description": "Não foram encontrados sinais relevantes de falha, backlog humano ou gaps recorrentes no recorte operacional.",
                "tone": "success",
            }
        ]

    @staticmethod
    def _item(
        title: str,
        description: str,
        href: str | None,
        *,
        status: str,
        badge: str | None = None,
        local: bool = False,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "href": href,
            "status": status,
            "badge": badge,
            "local": local,
            "available": bool(href),
        }
