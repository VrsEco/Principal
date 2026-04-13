from flask import Blueprint, render_template, jsonify, request, abort, current_app, redirect, url_for
from flask_login import login_required, current_user
from pydantic import ValidationError
from models import db, AIAgent, AgentMessage
from services.ai_configuration_pages_service import AIConfigurationPagesService
from services.ai_capabilities_central_service import AICapabilitiesCentralService
from services.ai_frontend_hub_service import AIFrontendHubService
from services.ai_mcp_console_service import AIMCPConsoleService
from services.tool_first_catalog_service import ToolFirstCatalogService
from schemas.ai_capabilities import (
    AICapabilityAuditLogCreateSchema,
    AICapabilityCompanySettingsUpsertSchema,
    AICapabilityGrantUpsertSchema,
    AICapabilityRolloutUpdateSchema,
)
from utils.permissions import permission_required, has_company_full_access, is_platform_admin

configs_bp = Blueprint('configs', __name__)


def _resolve_active_company():
    from api.routes.main import _resolve_active_company as _main_resolve_active_company

    return _main_resolve_active_company()


def _can_access_ai_mcp_console(company_id=None):
    if is_platform_admin():
        return True
    try:
        return has_company_full_access(company_id)
    except Exception:
        return False


def _require_ai_admin_access(company_id=None):
    if not _can_access_ai_mcp_console(company_id):
        abort(403)


def _build_ai_config_fallback_page(page_key: str) -> dict:
    titles = {
        "mcp": "MCP",
        "tools": "Tools",
        "permissions": "Permissões e Configurações",
        "monitoring": "Monitoramento e Auditoria",
    }
    title = titles.get(page_key, "IA Corporativa")
    return {
        "title": title,
        "eyebrow": "Configurações",
        "search_terms": f"{page_key} ia configuracoes fallback",
        "intro": (
            "A leitura completa desta página falhou, mas a operação foi mantida "
            "disponível em modo degradado para não bloquear o administrador."
        ),
        "hero_metrics": [
            {"label": "Status", "value": "Fallback"},
            {"label": "Página", "value": title},
            {"label": "Ação", "value": "Revisar logs"},
        ],
        "shortcuts": [
            {"label": "Integrações", "href": "/integrations"},
            {"label": "MCP", "href": "/configs/ai/mcp"},
            {"label": "Tools", "href": "/integrations/tools"},
            {"label": "Permissões e Configurações", "href": "/configs/ai/permissions"},
            {"label": "Monitoramento e Auditoria", "href": "/configs/ai/monitoring"},
        ],
        "wizard": {
            "title": "Assistente de recuperação",
            "intro": "Use os atalhos abaixo enquanto finalizamos a leitura completa.",
            "steps": [
                {
                    "step": 1,
                    "question": "O que você precisa fazer agora?",
                    "options": [
                        {
                            "label": "Abrir integrações",
                            "description": "Revisar catálogo, credenciais e ativação das integrações.",
                            "result_title": "Ir para integrações",
                            "result_body": "Abra a área de integrações para revisar o catálogo e a operação externa.",
                            "target_section": "links",
                        },
                        {
                            "label": "Ver auditoria",
                            "description": "Inspecionar trilhas e evidências operacionais.",
                            "result_title": "Ir para auditoria",
                            "result_body": "Abra a auditoria operacional para investigar o incidente.",
                            "target_section": "links",
                        },
                    ],
                }
            ],
        },
        "sections": [
            {
                "id": "links",
                "title": "Atalhos operacionais",
                "summary": "Continue a operação enquanto a página completa é restabelecida.",
                "items": [
                    {
                        "title": "Integrações",
                        "meta": "/integrations",
                        "description": "Revisar catálogo, providers, segredos e saúde das integrações.",
                        "href": "/integrations",
                    },
                    {
                        "title": "Auditoria operacional",
                        "meta": "/operations/audit",
                        "description": "Investigar trilhas MCP, Sapiens, gates humanos e eventos sensíveis.",
                        "href": "/operations/audit",
                    },
                    {
                        "title": "Hub IA Corporativa",
                        "meta": "/configs/ai?section=configuration",
                        "description": "Voltar para a central principal de administração da IA corporativa.",
                        "href": "/configs/ai?section=configuration",
                    },
                ],
            }
        ],
    }


def _render_ai_config_page(page_key: str, active_company):
    try:
        page_state = AIConfigurationPagesService.build_page(page_key, active_company)
    except Exception:
        current_app.logger.exception("Falha ao montar página de configuração IA: %s", page_key)
        page_state = _build_ai_config_fallback_page(page_key)

    return render_template(
        'modules/operations/ai_config_simple_page.html',
        active_company=active_company,
        page=page_state,
    )

@configs_bp.route('/configs/ai')
@login_required
# @permission_required('admin', 'view') # Maybe restrict to admin?
def ai_settings():
    """Hub arquitetural do frontend de IA."""
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        hub = AIFrontendHubService.build_frontend_state(None)
    except Exception:
        current_app.logger.exception('Falha ao montar central de IA.')
        console = AIMCPConsoleService.build_frontend_state(None)
        hub = {
            "summary": {
                "active_agents": 0,
                "total_agents": 0,
                "integrations_total": 0,
                "mcp_tools_total": int((console.get("summary") or {}).get("catalog_tools") or 0),
                "human_gate_tools": int((console.get("summary") or {}).get("human_gate_tools") or 0),
                "readiness_gates": int((console.get("summary") or {}).get("readiness_gates") or 0),
                "logs_total": 0,
                "audit_total": 0,
                "workflow_recent_total": 0,
                "pending_approvals": 0,
                "workflow_gaps": 0,
            },
            "overview": {
                "window_days": 30,
                "hero_cards": [
                    {
                        "label": "Saúde operacional",
                        "value": "Indisponível",
                        "description": "A visão detalhada sofreu degradação controlada. Use os atalhos operacionais abaixo enquanto finalizamos a leitura completa.",
                        "tone": "warning",
                        "badge": "Fallback ativo",
                    }
                ],
                "stats_cards": [],
                "platform_cards": [],
                "recent_workflows": [],
                "alerts": [
                    {
                        "title": "Visão Geral em fallback seguro",
                        "description": "A montagem completa do dashboard falhou, mas a página foi mantida funcional para não bloquear a operação.",
                        "tone": "warning",
                    }
                ],
                "quick_actions": [
                    {
                        "title": "Abrir MCP",
                        "href": "/configs/ai/mcp",
                        "description": "Surface, domínio e liberação.",
                    },
                    {
                        "title": "Gerir integrações",
                        "href": "/integrations",
                        "description": "Integrações, providers e segredos operacionais.",
                    },
                    {
                        "title": "Abrir Tools",
                        "href": "/integrations/tools",
                        "description": "Catálogo, risco e gate humano.",
                    },
                    {
                        "title": "Abrir monitoramento",
                        "href": "/configs/ai/monitoring",
                        "description": "Regras, saúde e auditoria.",
                    },
                    {
                        "title": "Ver auditoria",
                        "href": "/operations/audit",
                        "description": "Timeline operacional e eventos sensíveis.",
                    },
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
            },
            "agents": [],
            "pillars": [
                {
                    "key": "overview",
                    "title": "Visão Geral",
                    "eyebrow": "Entrada recomendada",
                    "description": "Central para entender operação, cobertura MCP, integrações e pontos críticos reais.",
                    "accent": "primary",
                    "items": [],
                },
                {
                    "key": "configuration",
                    "title": "Configurações",
                    "eyebrow": "Administração",
                    "description": "Integrações, MCP, tools e permissões.",
                    "accent": "blue",
                    "items": [],
                },
                {
                    "key": "monitoring_audit",
                    "title": "Monitoramento e Auditoria",
                    "eyebrow": "Controle e evidência",
                    "description": "Logs, auditoria e uso.",
                    "accent": "amber",
                    "items": [],
                },
            ],
            "console_summary": console.get("summary") or {},
            "audit_summary": {},
        }
    return render_template(
        'configurations_ai.html',
        agents=hub["agents"],
        ai_hub=hub,
        summary=hub["summary"],
        console_summary=hub["console_summary"],
        overview=hub["overview"],
        pillars=hub["pillars"],
        active_company=None,
    )

@configs_bp.route('/configs/system')
@login_required
def system_settings():
    """System Configuration Page"""
    from models.user import User
    
    # User stats for Card 3
    users_count = User.query.filter_by(is_active=True).count()
    users_with_contacts = User.query.filter(
        (User.whatsapp.isnot(None)) | (User.telegram.isnot(None))
    ).count()

    # Dummy data for other cards to prevent template errors
    audit_summary = {
        'total_routes': 42,
        'routes_with_logging': 38,
        'coverage_percentage': 90.5
    }
    log_stats = {
        'total_logs': 1250,
        'actions': ['Login', 'Create', 'Update'],
        'top_users': [1, 2, 3]
    }
    return render_template('configs_system.html', 
                          audit_summary=audit_summary, 
                          log_stats=log_stats,
                          users_count=users_count,
                          users_with_contacts=users_with_contacts)


@configs_bp.route('/configs/ai/mcp')
@login_required
def ai_mcp_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    return _render_ai_config_page("mcp", active_company)


@configs_bp.route('/configs/ai/tools')
@login_required
def ai_tools_page():
    return redirect("/integrations/tools")


@configs_bp.route('/configs/ai/permissions')
@login_required
def ai_permissions_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    try:
        state = AICapabilitiesCentralService.build_frontend_state(active_company)
    except Exception:
        current_app.logger.exception("Falha ao montar a Central de Capacidades de IA.")
        return _render_ai_config_page("permissions", active_company)

    return render_template(
        'modules/operations/ai_capabilities_central.html',
        active_company=active_company,
        state=state,
    )


@configs_bp.route('/configs/ai/monitoring')
@login_required
def ai_monitoring_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    return _render_ai_config_page("monitoring", active_company)


@configs_bp.route('/configs/ai/mcp/console')
@login_required
def ai_mcp_console():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)

    frontend_state = AIMCPConsoleService.build_frontend_state(active_company)
    return render_template(
        'modules/operations/ai_mcp_console.html',
        active_company=active_company,
        console=frontend_state,
    )

# API Endpoints

@configs_bp.route('/api/configs/ai/agents', methods=['GET'])
@login_required
def get_agents_config():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    agents = AIAgent.query.all()
    return jsonify({"success": True, "agents": [a.to_dict() for a in agents]})

@configs_bp.route('/api/configs/ai/agents/<string:agent_id>', methods=['PUT'])
@login_required
def update_agent_config(agent_id):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    data = request.get_json(silent=True) or {}
    agent = AIAgent.query.get_or_404(agent_id)
    
    # Update fields
    if 'status' in data:
        agent.status = data['status']
    if 'prompt_template' in data:
        agent.prompt_template = data['prompt_template']
    if 'advanced_settings' in data:
        adv = data['advanced_settings']
        if 'timeout' in adv: agent.timeout = adv['timeout']
        if 'execution_mode' in adv: agent.execution_mode = adv['execution_mode']
        
    db.session.commit()
    return jsonify({"success": True, "message": f"Agente {agent.name} atualizado."})

@configs_bp.route('/api/configs/ai/logs', methods=['GET'])
@login_required
def get_agent_logs():
    """Retrieve communication logs"""
    active_company = _resolve_active_company()
    company_id = getattr(active_company, "id", None)
    _require_ai_admin_access(company_id)
    limit = request.args.get('limit', 50, type=int)
    logs_query = AgentMessage.query.order_by(AgentMessage.created_at.desc())
    if company_id:
        logs_query = logs_query.filter(AgentMessage.company_id == company_id)
    logs = logs_query.limit(limit).all()
    
    return jsonify({
        "success": True, 
        "logs": [l.to_dict() for l in logs]
    })


@configs_bp.route('/api/configs/ai/mcp/frontend-state', methods=['GET'])
@login_required
def get_ai_mcp_frontend_state():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao console operacional IA/MCP."}), 403

    return jsonify({
        "success": True,
        "console": AIMCPConsoleService.build_frontend_state(active_company),
    })


@configs_bp.route('/api/configs/ai/mcp/tool-first-catalog', methods=['GET'])
@login_required
def get_tool_first_catalog():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao catálogo tool-first IA/MCP."}), 403

    domain = request.args.getlist('domain')
    status = request.args.getlist('status')
    surface = request.args.getlist('surface')
    if not domain:
        domain = request.args.get('domain')
    if not status:
        status = request.args.get('status')
    if not surface:
        surface = request.args.get('surface')
    include_backlog = (request.args.get('include_backlog', 'true') or 'true').strip().lower() != 'false'

    return jsonify({
        "success": True,
        "catalog": ToolFirstCatalogService.build_catalog(
            active_company,
            domain=domain,
            status=status,
            surface=surface,
            include_backlog=include_backlog,
        ),
    })


@configs_bp.route('/api/configs/ai/capabilities/frontend-state', methods=['GET'])
@login_required
def get_ai_capabilities_frontend_state():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    return jsonify({
        "success": True,
        "state": AICapabilitiesCentralService.build_frontend_state(active_company),
    })


@configs_bp.route('/api/configs/ai/capabilities/grants', methods=['POST'])
@login_required
def upsert_ai_capability_grant():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = AICapabilityGrantUpsertSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        grant = AICapabilitiesCentralService.upsert_grant(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "grant": grant.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/capabilities/company-settings', methods=['POST'])
@login_required
def upsert_ai_capability_company_settings():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = AICapabilityCompanySettingsUpsertSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        record = AICapabilitiesCentralService.upsert_company_settings(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "company_settings": record.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/capabilities/rollout', methods=['POST'])
@login_required
def update_ai_capability_rollout():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = AICapabilityRolloutUpdateSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        capability = AICapabilitiesCentralService.update_rollout(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "capability": capability.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/capabilities/audit-log', methods=['POST'])
@login_required
def create_ai_capability_audit_log():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = AICapabilityAuditLogCreateSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        log = AICapabilitiesCentralService.record_audit_event(
            capability_key=payload["capability_key"],
            event_type=payload["event_type"],
            result=payload["result"],
            company_id=payload.get("company_id"),
            user_id=payload.get("user_id"),
            actor_user_id=current_user.id,
            channel=payload.get("channel"),
            surface=payload.get("surface"),
            detail=payload.get("detail"),
            payload=payload.get("payload") or {},
        )
        return jsonify({"success": True, "audit_log": log.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
