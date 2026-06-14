from io import BytesIO

from flask import Blueprint, render_template, jsonify, request, abort, current_app, redirect, url_for, send_file
from flask_login import login_required, current_user
from pydantic import ValidationError
from models import db, AIAgent, AgentMessage
from services.ai_configuration_pages_service import AIConfigurationPagesService
from services.ai_capability_backlog_service import AICapabilityBacklogService
from services.ai_capability_blueprint_service import AICapabilityBlueprintService
from services.ai_capability_inventory_service import AICapabilityInventoryService
from services.ai_capabilities_central_service import AICapabilitiesCentralService
from services.ai_frontend_hub_service import AIFrontendHubService
from services.ai_mcp_console_service import AIMCPConsoleService
from services.ai_automation_registry_service import AIAutomationRegistryService
from services.automation_registry_service import AutomationRegistryService
from services.instruction_registry_service import InstructionRegistryService
from services.mcp_connection_snippet_service import MCPConnectionSnippetService
from services.ai_monitoring_pdf_service import generate_ai_monitoring_report_pdf
from services.agent_backlog_service import create_backlog_task
from services.e2e_operations_center_service import E2EOperationsCenterService
from services.robot_tests_center_service import RobotTestsCenterService
try:
    from app32.tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService
except ModuleNotFoundError:  # pragma: no cover - compatibilidade de import local
    from tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService
from services.external_llm_factory_service import ExternalLLMFactoryService
from services.monitoring_audit_request_service import MonitoringAuditRequestService
from services.sapiens_factory_registry_service import SapiensFactoryRegistryService
from services.sapiens_factory_schema import FactoryActorContext, SapiensFactoryChangeRequest
from services.sapiens_factory_service import SapiensFactoryService
from services.operational_audit_service import OperationalAuditService
from services.tool_first_catalog_service import ToolFirstCatalogService
from schemas.ai_capabilities import (
    AICapabilityAuditLogCreateSchema,
    AICapabilityCompanySettingsUpsertSchema,
    AICapabilityGrantUpsertSchema,
    AICapabilityRolloutUpdateSchema,
)
from schemas.instruction_registry_admin import (
    InstructionRegistryEntryUpsertSchema,
    InstructionRegistryInvalidateSchema,
    InstructionRegistryPromoteSchema,
)
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required, has_company_full_access, is_platform_admin

try:
    from services.mcp_feature_catalog_service import MCPDocumentationContext, MCPFeatureCatalogService
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com deploy parcial
    MCPDocumentationContext = None
    MCPFeatureCatalogService = None

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


def _build_factory_actor_context(active_company) -> FactoryActorContext:
    company_id = getattr(active_company, "id", None)
    accessible_company_ids = list(get_accessible_company_ids() or [])
    if company_id and company_id not in accessible_company_ids:
        accessible_company_ids.append(company_id)
    return FactoryActorContext(
        user_id=getattr(current_user, "id", None),
        role=getattr(current_user, "role", None),
        channel="web",
        company_id=company_id,
        accessible_company_ids=accessible_company_ids,
    )


def _build_ai_config_fallback_page(page_key: str) -> dict:
    titles = {
        "mcp": "API / MCP",
        "tools": "Tools",
        "permissions": "Capacidades de IA",
        "inventory": "Inventário de Capabilities",
        "automation_mesh": "Malha de Automações",
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
            {"label": "Configurações de Canais", "href": "/channels"},
            {"label": "API / MCP", "href": "/api-mcp"},
            {"label": "Tools", "href": "/tools"},
            {"label": "Capacidades de IA", "href": "/ai-capabilities"},
            {"label": "Inventário de Capabilities", "href": "/ai-capability-inventory"},
            {"label": "Malha de Automações", "href": "/ai-automation-mesh"},
            {"label": "Monitoramento e Auditoria", "href": "/ai-monitoring"},
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
                            "label": "Abrir API / MCP",
                            "description": "Revisar catálogo, contratos e ativação operacional.",
                            "result_title": "Ir para API / MCP",
                            "result_body": "Abra a área API / MCP para revisar o catálogo e a operação externa.",
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
                        "title": "API / MCP",
                        "meta": "/api-mcp",
                        "description": "Revisar catálogo, contratos e saúde operacional das integrações de negócio.",
                        "href": "/api-mcp",
                    },
                    {
                        "title": "Auditoria operacional",
                        "meta": "/operations/audit",
                        "description": "Investigar trilhas MCP, Sapiens, gates humanos e eventos sensíveis.",
                        "href": "/operations/audit",
                    },
                    {
                        "title": "Hub IA Corporativa",
                        "meta": "/ai",
                        "description": "Voltar para a central principal de administração da IA corporativa.",
                        "href": "/ai",
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


@configs_bp.route('/qa/e2e')
@login_required
def e2e_operations_center():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    state = E2EOperationsCenterService.build_frontend_state(active_company)
    return render_template(
        'modules/operations/e2e_center.html',
        active_company=active_company,
        state=state,
    )


@configs_bp.route('/api/configs/qa/e2e/frontend-state')
@login_required
def e2e_operations_center_frontend_state():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    state = E2EOperationsCenterService.build_frontend_state(active_company)
    return jsonify({"success": True, "state": state})


@configs_bp.route('/api/configs/qa/e2e/executions', methods=['GET'])
@login_required
def e2e_supervised_execution_list():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    return jsonify({"success": True, "executions": E2ESupervisedExecutionService.list_executions()})


@configs_bp.route('/api/configs/qa/e2e/executions', methods=['POST'])
@login_required
def e2e_supervised_execution_create():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    payload = request.get_json(silent=True) or {}
    suite_id = str(payload.get('suite_id') or '').strip()
    environment = str(payload.get('environment') or '').strip().upper()
    if not suite_id or not environment:
        return jsonify({"success": False, "error": "suite_id e environment são obrigatórios."}), 400
    try:
        execution = E2ESupervisedExecutionService.start_execution(suite_id=suite_id, environment=environment)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "execution": execution}), 201


@configs_bp.route('/api/configs/qa/e2e/executions/<string:execution_id>', methods=['GET'])
@login_required
def e2e_supervised_execution_detail(execution_id: str):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        execution = E2ESupervisedExecutionService.get_execution(execution_id)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Execução não encontrada."}), 404
    return jsonify({"success": True, "execution": execution})


@configs_bp.route('/api/configs/qa/e2e/runs/<string:run_id>', methods=['GET'])
@login_required
def e2e_run_detail(run_id: str):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        detail = E2EOperationsCenterService.get_run_detail(run_id)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Run não encontrado."}), 404
    return jsonify({"success": True, "run": detail})


@configs_bp.route('/api/configs/qa/e2e/runs/<string:run_id>/manifest', methods=['GET'])
@login_required
def e2e_run_manifest_download(run_id: str):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        file_path = E2EOperationsCenterService.resolve_run_file(run_id, 'manifest')
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Manifesto não encontrado."}), 404
    return send_file(file_path, as_attachment=True, download_name=f'{run_id}-manifest.json', mimetype='application/json')


@configs_bp.route('/api/configs/qa/e2e/runs/<string:run_id>/backlog-candidates', methods=['GET'])
@login_required
def e2e_run_backlog_candidates_download(run_id: str):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        file_path = E2EOperationsCenterService.resolve_run_file(run_id, 'backlog_candidates')
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Backlog candidates não encontrado."}), 404
    return send_file(file_path, as_attachment=True, download_name=f'{run_id}-backlog-candidates.json', mimetype='application/json')


@configs_bp.route('/api/configs/qa/e2e/runs/<string:run_id>/artifacts/<int:artifact_index>', methods=['GET'])
@login_required
def e2e_run_artifact_download(run_id: str, artifact_index: int):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        file_path = E2EOperationsCenterService.resolve_run_file(run_id, 'artifact', artifact_index=artifact_index)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Artefato não encontrado."}), 404
    return send_file(file_path, as_attachment=True, download_name=file_path.name)


@configs_bp.route('/api/configs/qa/e2e/runs/<string:run_id>/backlog-sync', methods=['POST'])
@login_required
def e2e_run_backlog_sync(run_id: str):
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        result = E2EOperationsCenterService.sync_backlog_candidates(
            run_id,
            user_id=getattr(current_user, 'id', None),
            company_id=getattr(active_company, 'id', None),
            create_task_fn=create_backlog_task,
        )
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Run não encontrado."}), 404
    status_code = 201 if result.get('created') else 200
    return jsonify({"success": True, "result": result}), status_code


def _resolve_robot_tests_company_id(active_company):
    active_company_id = getattr(active_company, "id", None)
    requested_company_id = request.args.get("company_id") or (request.get_json(silent=True) or {}).get("company_id")
    company_id = int(requested_company_id or active_company_id or 0)
    if not company_id:
        abort(400, description="company_id é obrigatório para a Central do Robô de Testes.")
    if active_company_id and int(company_id) != int(active_company_id) and not is_platform_admin():
        abort(403)
    return company_id


@configs_bp.route('/qa/robot-tests')
@login_required
def robot_tests_center():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, "id", None)
    _require_ai_admin_access(company_id)
    state = RobotTestsCenterService.build_overview_state(active_company=active_company, company_id=int(company_id or 0))
    return render_template(
        'modules/operations/robot_tests_center.html',
        active_company=active_company,
        state=state,
    )


@configs_bp.route('/api/qa/robot-tests/overview', methods=['GET'])
@login_required
def robot_tests_overview():
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    state = RobotTestsCenterService.build_overview_state(active_company=active_company, company_id=company_id)
    return jsonify({"success": True, "state": state})


@configs_bp.route('/api/qa/robot-tests/areas/latest', methods=['GET'])
@login_required
def robot_tests_areas_latest():
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    return jsonify({"success": True, "areas": RobotTestsCenterService.list_area_latest(company_id=company_id)})


@configs_bp.route('/api/qa/robot-tests/areas/<string:area_id>/latest', methods=['GET'])
@login_required
def robot_tests_area_latest(area_id: str):
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    try:
        area = RobotTestsCenterService.get_area_latest(area_id=area_id, company_id=company_id)
    except KeyError:
        return jsonify({"success": False, "error": "Área de teste não encontrada."}), 404
    return jsonify({"success": True, "area": area})


@configs_bp.route('/api/qa/robot-tests/errors', methods=['GET'])
@login_required
def robot_tests_errors():
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    return jsonify({"success": True, "errors": RobotTestsCenterService.list_open_errors(company_id=company_id)})


@configs_bp.route('/api/qa/robot-tests/runs', methods=['POST'])
@login_required
def robot_tests_runs_create():
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    payload = request.get_json(silent=True) or {}
    try:
        result = RobotTestsCenterService.start_run(
            package_key=payload.get("package_key"),
            suite_id=payload.get("suite_id"),
            environment=str(payload.get("environment") or "PROD_SAFE").upper(),
            company_id=company_id,
            user_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    return jsonify({"success": True, "result": result}), 201


@configs_bp.route('/api/qa/robot-tests/errors/<string:error_id>/actions', methods=['POST'])
@login_required
def robot_tests_error_action(error_id: str):
    active_company = _resolve_active_company()
    company_id = _resolve_robot_tests_company_id(active_company)
    _require_ai_admin_access(company_id)
    payload = request.get_json(silent=True) or {}
    try:
        result = RobotTestsCenterService.handle_error_action(
            error_id=error_id,
            action=str(payload.get("action") or "details"),
            company_id=company_id,
            user_id=getattr(current_user, "id", None),
            create_task_fn=create_backlog_task,
        )
    except KeyError:
        return jsonify({"success": False, "error": "Erro de teste não encontrado."}), 404
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "result": result})

@configs_bp.route('/ai')
@login_required
# @permission_required('admin', 'view') # Maybe restrict to admin?
def ai_settings():
    """Hub arquitetural do frontend de IA."""
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    try:
        hub = AIFrontendHubService.build_frontend_state(active_company)
    except Exception:
        current_app.logger.exception('Falha ao montar central de IA.')
        console = AIMCPConsoleService.build_frontend_state(active_company)
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
                        "title": "Abrir API / MCP",
                        "href": "/api-mcp",
                        "description": "Surface, domínio e liberação.",
                    },
                    {
                        "title": "Configurar canais",
                        "href": "/channels",
                        "description": "Configurações de canais, providers e segredos operacionais.",
                    },
                    {
                        "title": "Abrir Tools",
                        "href": "/tools",
                        "description": "Catálogo, risco e gate humano.",
                    },
                    {
                        "title": "Inventário IA",
                        "href": "/ai-capability-inventory",
                        "description": "Capabilities, workflows, integrações e automações.",
                    },
                    {
                        "title": "Malha de automações",
                        "href": "/ai-automation-mesh",
                        "description": "Scheduler, rotinas e automações event-driven.",
                    },
                    {
                        "title": "Abrir monitoramento",
                        "href": "/ai-monitoring",
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
                    "description": "Canais, API / MCP, tools e permissões.",
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


@configs_bp.route('/configs/ai')
@login_required
def ai_settings_legacy_redirect():
    return redirect(url_for('configs.ai_settings'))


@configs_bp.route('/ai-capability-inventory')
@login_required
def ai_capability_inventory_page():
    active_company = _resolve_active_company()
    _require_ai_admin_access(getattr(active_company, "id", None))
    return _render_ai_config_page("inventory", active_company)


@configs_bp.route('/ai-automation-mesh')
@login_required
def ai_automation_mesh_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, "id", None)
    _require_ai_admin_access(company_id)
    filters = {
        'module_key': request.args.get('module_key'),
        'origin_type': request.args.get('origin_type'),
        'status': request.args.get('status'),
        'search': request.args.get('search'),
        'only_error': request.args.get('only_error'),
        'only_approval': request.args.get('only_approval'),
    }
    registry = AutomationRegistryService.build_registry_snapshot(company_id, filters, limit=request.args.get('limit', type=int) or 200)
    return render_template(
        'modules/operations/automation_registry.html',
        active_company=active_company,
        registry=registry,
        filters=registry.get('filters') or {},
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


@configs_bp.route('/api-mcp-legacy')
@login_required
def ai_mcp_page():
    return redirect('/api-mcp')


@configs_bp.route('/configs/ai/tools')
@login_required
def ai_tools_page():
    return redirect("/tools")


@configs_bp.route('/ai-capabilities')
@login_required
def ai_permissions_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    allowed_company_ids = get_accessible_company_ids()
    try:
        state = AICapabilitiesCentralService.build_frontend_state(
            active_company,
            selected_capability_key=request.args.get('capability_key'),
            allowed_company_ids=allowed_company_ids,
        )
    except Exception:
        current_app.logger.exception("Falha ao montar a Central de Capacidades de IA.")
        return _render_ai_config_page("permissions", active_company)

    return render_template(
        'modules/operations/ai_capabilities_central.html',
        active_company=active_company,
        state=state,
    )


@configs_bp.route('/configs/ai/permissions')
@login_required
def ai_permissions_legacy_redirect():
    return redirect('/ai-capabilities')


@configs_bp.route('/ai-monitoring')
@login_required
def ai_monitoring_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    return _render_ai_config_page("monitoring", active_company)


@configs_bp.route('/configs/ai/monitoring')
@login_required
def ai_monitoring_legacy_redirect():
    return redirect('/ai-monitoring')

@configs_bp.route('/api/ai-monitoring/panel', methods=['GET'])
@login_required
def ai_monitoring_panel_api():
    active_company = _resolve_active_company()
    company_id = request.args.get('company_id', type=int) or getattr(active_company, 'id', None)
    if not company_id:
        return jsonify({"success": False, "error": "Empresa ativa obrigatória para monitoramento."}), 400
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao monitoramento de IA."}), 403

    result, error = OperationalAuditService.build_panel(
        company_id=int(company_id),
        allowed_company_ids=None if is_platform_admin() else get_accessible_company_ids(),
        source=request.args.get('source') or None,
        limit=request.args.get('limit', default=12, type=int),
    )
    if error:
        return jsonify({"success": False, "error": error}), 400
    return jsonify({"success": True, "panel": result})


@configs_bp.route('/api/ai-monitoring/requests', methods=['GET'])
@login_required
def ai_monitoring_requests_api():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if company_id and not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao monitoramento de IA."}), 403

    return jsonify({
        "success": True,
        "requests": MonitoringAuditRequestService.list_requests(
            company_id=company_id,
            requester_user_id=int(current_user.id),
            limit=request.args.get('limit', default=10, type=int),
        ),
    })


@configs_bp.route('/api/ai-monitoring/requests', methods=['POST'])
@login_required
def ai_monitoring_create_request_api():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not company_id:
        return jsonify({"success": False, "error": "Empresa ativa obrigatória para abrir solicitação de monitoramento."}), 400
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao monitoramento de IA."}), 403

    payload = request.get_json(silent=True) or {}
    try:
        record = MonitoringAuditRequestService.create_request(
            payload,
            company_id=int(company_id),
            company_name=getattr(active_company, 'name', None),
            requester_user_id=int(current_user.id),
            requester_name=getattr(current_user, 'name', None),
        )
    except ValidationError as exc:
        return jsonify({"success": False, "error": "Payload inválido para solicitação de auditoria.", "details": exc.errors()}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({"success": True, "request": record}), 201


@configs_bp.route('/api/ai-monitoring/report.pdf', methods=['GET'])
@login_required
def ai_monitoring_report_pdf():
    active_company = _resolve_active_company()
    company_id = request.args.get('company_id', type=int) or getattr(active_company, 'id', None)
    if not company_id:
        return jsonify({"success": False, "error": "Empresa ativa obrigatória para exportar o relatório."}), 400
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao monitoramento de IA."}), 403

    panel, error = OperationalAuditService.build_panel(
        company_id=int(company_id),
        allowed_company_ids=None if is_platform_admin() else get_accessible_company_ids(),
        source=request.args.get('source') or None,
        limit=request.args.get('limit', default=50, type=int),
    )
    if error:
        return jsonify({"success": False, "error": error}), 400

    pdf_bytes = generate_ai_monitoring_report_pdf(
        panel=panel or {},
        company_name=getattr(active_company, 'name', None) or f'Empresa {company_id}',
        generated_by=(getattr(current_user, 'name', None) or getattr(current_user, 'email', None) or 'Usuário autenticado'),
    )
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'monitoramento-auditoria-{company_id}.pdf',
    )



@configs_bp.route('/configs/ai/mcp')
@login_required
def ai_mcp_legacy_redirect():
    return redirect('/api-mcp')


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

@configs_bp.route('/ai/factory')
@login_required
def sapiens_factory_page():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        abort(403)
    actor = _build_factory_actor_context(active_company)
    assessment = SapiensFactoryService.assess_change_request(
        {
            'request_text': 'Diagnosticar a prontidão da Sapiens Factory para evoluções assistidas.',
            'execution_mode': 'diagnose',
            'urgency': 'medium',
            'company_id': company_id,
        },
        actor_context=actor.model_dump(mode='json'),
    )
    return render_template(
        'modules/operations/sapiens_factory.html',
        active_company=active_company,
        actor_context=actor.model_dump(mode='json'),
        registry_snapshot=SapiensFactoryRegistryService.build_registry_snapshot(),
        external_surface=ExternalLLMFactoryService.build_surface_manifest(),
        initial_assessment=assessment,
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


@configs_bp.route('/api/configs/ai/mcp/bootstrap-session', methods=['GET'])
@login_required
def get_ai_mcp_bootstrap_session():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao bootstrap documental IA/MCP."}), 403
    if not company_id:
        return jsonify({"success": False, "error": "Empresa ativa obrigatória para bootstrap documental."}), 400
    if MCPDocumentationContext is None or MCPFeatureCatalogService is None:
        return jsonify({"success": False, "error": "Bootstrap documental MCP indisponível neste runtime."}), 503

    requested_surface = (request.args.get('surface') or AIMCPConsoleService.DOCUMENTATION_BOOTSTRAP_SURFACE).strip().lower()
    context = MCPDocumentationContext(
        company_id=int(company_id),
        user_id=int(getattr(current_user, 'id', 0) or 0) or None,
        role='administrador' if is_platform_admin() else 'colaborador',
        surface=requested_surface,
        client='ai_mcp_console',
        transport='web',
    )

    try:
        bootstrap = MCPFeatureCatalogService().bootstrap_context(context)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({
        "success": True,
        "bootstrap": bootstrap,
    })


@configs_bp.route('/api/configs/ai/mcp/connection-snippet', methods=['POST'])
@login_required
def generate_ai_mcp_connection_snippet():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({"success": False, "error": "Acesso negado ao console operacional IA/MCP."}), 403

    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode") or "ai_prompt").strip().lower()

    try:
        source_json = MCPConnectionSnippetService.build_source_json(payload)
        if mode == "raw_config":
            content = MCPConnectionSnippetService.build_raw_config(payload)
        else:
            mode = "ai_prompt"
            content = MCPConnectionSnippetService.build_prompt(payload)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({
        "success": True,
        "mode": mode,
        "content": content,
        "source_json": source_json,
    })




@configs_bp.route('/api/configs/ai/factory/context', methods=['GET'])
@login_required
def get_sapiens_factory_context():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à Sapiens Factory.'}), 403

    actor = _build_factory_actor_context(active_company)
    return jsonify({
        'success': True,
        'actor': actor.model_dump(mode='json'),
        'registry': SapiensFactoryRegistryService.build_registry_snapshot(),
        'external_surface': ExternalLLMFactoryService.build_surface_manifest(),
        'inventory': AICapabilityInventoryService.build_inventory(active_company),
        'automation_registry': AIAutomationRegistryService.build_registry(active_company),
    })


@configs_bp.route('/api/configs/automation-registry', methods=['GET'])
@login_required
def get_automation_registry():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à Central de Automações.'}), 403

    filters = {
        'module_key': request.args.get('module_key'),
        'origin_type': request.args.get('origin_type'),
        'status': request.args.get('status'),
        'entity_type': request.args.get('entity_type'),
        'entity_id': request.args.get('entity_id'),
        'search': request.args.get('search'),
        'only_error': request.args.get('only_error'),
        'only_approval': request.args.get('only_approval'),
    }
    snapshot = AutomationRegistryService.build_registry_snapshot(company_id, filters, limit=request.args.get('limit', type=int) or 200)
    return jsonify({'success': True, 'registry': snapshot})


@configs_bp.route('/api/configs/ai/factory/capabilities', methods=['GET'])
@login_required
def get_sapiens_factory_capabilities():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à Sapiens Factory.'}), 403
    return jsonify({'success': True, 'registry': SapiensFactoryRegistryService.build_registry_snapshot()})


@configs_bp.route('/api/configs/ai/factory/external-surface', methods=['GET'])
@login_required
def get_sapiens_factory_external_surface():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à surface externa da factory.'}), 403
    return jsonify({'success': True, 'surface': ExternalLLMFactoryService.build_surface_manifest()})


@configs_bp.route('/api/configs/ai/factory/assess-change', methods=['POST'])
@login_required
def assess_sapiens_factory_change():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à Sapiens Factory.'}), 403

    actor = _build_factory_actor_context(active_company)
    payload = request.get_json(silent=True) or {}
    if company_id and payload.get('company_id') is None:
        payload['company_id'] = company_id
    try:
        request_model = SapiensFactoryChangeRequest.model_validate(payload)
        assessment = SapiensFactoryService.assess_change_request(
            request_model.model_dump(mode='json'),
            actor_context=actor.model_dump(mode='json'),
        )
        return jsonify({'success': True, 'assessment': assessment})
    except ValidationError as exc:
        return jsonify({'success': False, 'error': exc.errors()}), 400


@configs_bp.route('/api/configs/ai/capability-blueprint', methods=['GET', 'POST'])
@login_required
def get_ai_capability_blueprint():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado ao blueprint de capabilities.'}), 403

    payload = request.get_json(silent=True) or {}
    if request.method == 'GET':
        payload = {
            'title': request.args.get('title') or 'Capability padrão APP32',
            'domain': request.args.get('domain') or 'platform',
            'target_layers': request.args.getlist('target_layers') or ['service', 'tool_contract', 'rest_mcp', 'workflow', 'ui_sapiens'],
            'risk': request.args.get('risk') or 'medium',
            'human_gate_required': request.args.get('human_gate_required', 'true').lower() == 'true',
            'execution_mode': request.args.get('execution_mode') or 'plan',
        }

    blueprint = AICapabilityBlueprintService.build_blueprint(
        title=payload.get('title') or 'Capability padrão APP32',
        domain=payload.get('domain') or 'platform',
        target_layers=payload.get('target_layers') or ['service', 'tool_contract', 'rest_mcp', 'workflow', 'ui_sapiens'],
        risk=payload.get('risk') or 'medium',
        human_gate_required=bool(payload.get('human_gate_required', False)),
        target_object=payload.get('target_object'),
        execution_mode=payload.get('execution_mode') or 'plan',
    )
    return jsonify({'success': True, 'blueprint': blueprint})


@configs_bp.route('/api/configs/ai/factory/create-backlog-card', methods=['POST'])
@login_required
def create_sapiens_factory_backlog_card():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    if not _can_access_ai_mcp_console(company_id):
        return jsonify({'success': False, 'error': 'Acesso negado à Sapiens Factory.'}), 403

    actor = _build_factory_actor_context(active_company)
    payload = request.get_json(silent=True) or {}
    if company_id and payload.get('company_id') is None:
        payload['company_id'] = company_id

    try:
        request_model = SapiensFactoryChangeRequest.model_validate(payload)
        assessment = SapiensFactoryService.assess_change_request(
            request_model.model_dump(mode='json'),
            actor_context=actor.model_dump(mode='json'),
        )
        title = f"[Sapiens Factory] {assessment['summary']['change_type']} · {assessment['request'].get('target_object') or request_model.request_text[:72]}"
        description = "\n".join(
            [
                "Demanda formalizada pela Sapiens Factory.",
                "",
                f"Resumo: {request_model.request_text}",
                f"Domínio: {assessment['request'].get('domain') or '-'}",
                f"Risco: {assessment.get('risk_level') or '-'}",
                f"Human gate: {'sim' if assessment.get('human_gate_required') else 'não'}",
                "",
                "Próximos passos:",
                *[f"- {item}" for item in (assessment.get('next_steps') or [])],
            ]
        )
        task, error = create_backlog_task(
            source_type='sapiens_factory',
            title=title,
            description=description,
            user_id=getattr(current_user, 'id', None),
            company_id=company_id,
            metadata={
                'change_type': assessment['summary'].get('change_type'),
                'risk_level': assessment.get('risk_level'),
                'target_object': assessment['request'].get('target_object'),
                'domain': assessment['request'].get('domain'),
            },
            priority='high' if assessment.get('risk_level') in {'high', 'critical'} else 'normal',
        )
        if error or task is None:
            return jsonify({'success': False, 'error': error or 'Falha ao criar card no backlog.'}), 400
        return jsonify(
            {
                'success': True,
                'backlog_task': {
                    'id': task.id,
                    'code': task.code,
                    'title': task.what,
                    'href': f"/my-work/project-task/{task.id}",
                },
                'assessment': assessment,
            }
        )
    except ValidationError as exc:
        return jsonify({'success': False, 'error': exc.errors()}), 400


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


@configs_bp.route('/api/configs/ai/mcp/instruction-registry/frontend-state', methods=['GET'])
@login_required
def get_instruction_registry_frontend_state():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    return jsonify({
        "success": True,
        "state": InstructionRegistryService.build_frontend_state(),
    })


@configs_bp.route('/api/configs/ai/mcp/instruction-registry/entries', methods=['POST'])
@login_required
def upsert_instruction_registry_entry():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = InstructionRegistryEntryUpsertSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        entry = InstructionRegistryService.upsert_entry(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "entry": entry.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/mcp/instruction-registry/invalidate', methods=['POST'])
@login_required
def invalidate_instruction_registry_entries():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = InstructionRegistryInvalidateSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        result = InstructionRegistryService.invalidate_entries(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "result": result})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/mcp/instruction-registry/promote', methods=['POST'])
@login_required
def promote_instruction_registry_entry():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        payload = InstructionRegistryPromoteSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        entry = InstructionRegistryService.promote_entry(payload, actor_user_id=current_user.id)
        return jsonify({"success": True, "entry": entry.to_dict()})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@configs_bp.route('/api/configs/ai/capabilities/frontend-state', methods=['GET'])
@login_required
def get_ai_capabilities_frontend_state():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    allowed_company_ids = get_accessible_company_ids()
    return jsonify({
        "success": True,
        "state": AICapabilitiesCentralService.build_frontend_state(
            active_company,
            selected_capability_key=request.args.get('capability_key'),
            allowed_company_ids=allowed_company_ids,
        ),
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


@configs_bp.route('/api/configs/ai/capabilities/requests', methods=['GET'])
@login_required
def list_ai_capability_requests():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    return jsonify({
        "success": True,
        "requests": AICapabilityBacklogService.list_requests(
            capability_key=request.args.get('capability_key'),
            limit=request.args.get('limit', 100, type=int),
        ),
    })


@configs_bp.route('/api/configs/ai/capabilities/requests', methods=['POST'])
@login_required
def create_ai_capability_request():
    active_company = _resolve_active_company()
    company_id = getattr(active_company, 'id', None)
    _require_ai_admin_access(company_id)
    try:
        record = AICapabilityBacklogService.create_request(
            request.get_json(silent=True) or {},
            company_id=company_id,
            requester_user_id=current_user.id,
            requester_name=getattr(current_user, 'name', None),
        )
        return jsonify({"success": True, "request": record})
    except ValidationError as exc:
        return jsonify({"success": False, "error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
