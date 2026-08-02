from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.agent_conversation_service import AgentConversationService
from services.cadastro_agent_service import CadastroAgentService
from utils.permissions import has_company_full_access, is_platform_admin

agents_bp = Blueprint('agents', __name__)
cadastro_service = CadastroAgentService()
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'

AGENT_SURFACE_CONFIG = {
    'planejamento': {
        'icon': '🧭',
        'eyebrow': 'Wrapper Sapiens',
        'title': 'Planejamento Estratégico',
        'description': 'Esta antiga tela de agente agora funciona como entrada guiada para o Sapiens. O objetivo é concentrar a inteligência em um hub único e mover capacidades para tools REST + MCP.',
        'preset': 'Quero apoio em planejamento estratégico. Analise o contexto da empresa, identifique lacunas e proponha próximos passos executáveis.',
        'tool_targets': [
            {'name': 'generate_strategy_snapshot', 'description': 'Leitura executiva do contexto estratégico e situação atual.'},
            {'name': 'suggest_okrs', 'description': 'Sugestão de objetivos e indicadores coerentes com o momento da empresa.'},
            {'name': 'list_strategic_gaps', 'description': 'Gap analysis para orientar priorização de execução.'},
        ],
    },
    'processos': {
        'icon': '⚙️',
        'eyebrow': 'Wrapper Sapiens',
        'title': 'Processos',
        'description': 'Em vez de manter um agente isolado para processos, esta superfície orienta o usuário a operar via Sapiens com catálogo de tools específico.',
        'preset': 'Quero ajuda com processos. Identifique gargalos, processos críticos e sugira melhorias com base no contexto atual.',
        'tool_targets': [
            {'name': 'list_processes', 'description': 'Consulta estruturada dos processos disponíveis por empresa.'},
            {'name': 'analyze_process_bottlenecks', 'description': 'Leitura de gargalos e pontos de ruptura operacional.'},
            {'name': 'map_process', 'description': 'Estruturação guiada de fluxos e macroprocessos.'},
        ],
    },
    'rotina': {
        'icon': '📅',
        'eyebrow': 'Wrapper Sapiens',
        'title': 'Rotina Operacional',
        'description': 'A rotina agora deve ser dirigida pelo Sapiens usando tools operacionais. Isso reduz código duplicado e melhora a consistência omnichannel.',
        'preset': 'Quero ajuda com rotina operacional. Liste prioridades, pendências e ações de follow-up para a semana.',
        'tool_targets': [
            {'name': 'list_pending_tasks', 'description': 'Consulta de atividades abertas por empresa, pessoa ou período.'},
            {'name': 'summarize_team_workload', 'description': 'Leitura rápida de carga do time e gargalos de execução.'},
            {'name': 'generate_followup_actions', 'description': 'Próximas ações sugeridas para cobrança e acompanhamento.'},
        ],
    },
    'performance': {
        'icon': '📈',
        'eyebrow': 'Wrapper Sapiens',
        'title': 'Performance',
        'description': 'A camada de performance deixa de ser um agente de tela independente e passa a ser uma jornada do Sapiens sobre indicadores e risco.',
        'preset': 'Quero analisar performance. Leia os indicadores da empresa, aponte riscos, tendências e ações recomendadas.',
        'tool_targets': [
            {'name': 'list_indicators', 'description': 'Catálogo e leitura de indicadores por empresa.'},
            {'name': 'analyze_indicator_trends', 'description': 'Interpretação de tendência, desvio e estabilidade.'},
            {'name': 'detect_performance_risk', 'description': 'Sinalização de risco de performance e impacto operacional.'},
        ],
    },
    'estrategico': {
        'icon': '🏛️',
        'eyebrow': 'Wrapper Sapiens',
        'title': 'Leitura Estratégica',
        'description': 'Esta superfície agora encaminha o usuário para uma leitura estratégica consolidada do Sapiens, com foco em execução, risco e coerência do negócio.',
        'preset': 'Quero uma leitura estratégica da empresa. Compare estratégia e execução, mostre riscos e prioridades executivas.',
        'tool_targets': [
            {'name': 'generate_executive_summary', 'description': 'Resumo executivo para diretoria e tomada de decisão.'},
            {'name': 'compare_strategy_vs_execution', 'description': 'Leitura entre intenção estratégica e operação real.'},
            {'name': 'list_strategic_risks', 'description': 'Riscos e tensões relevantes para alta gestão.'},
        ],
    },
}


def _has_operational_full_access(company_id=None):
    role = str(getattr(current_user, 'role', '')).strip().lower()
    if role in {'admin', 'administrator'}:
        return True
    try:
        return has_company_full_access(company_id)
    except Exception:
        return False


def _is_platform_admin_local():
    return str(getattr(current_user, 'role', '')).strip().lower() in {'admin', 'administrator'}


def _log_workflow_approval_message(action, message: str, metadata=None):
    from models import db, AgentMessage

    payload = dict(getattr(action, 'payload', None) or {})
    resume_payload = dict(payload.get('resume_payload') or {})
    approval_metadata = dict((metadata or {}).get('workflow_approval') or {})
    channel = resume_payload.get('channel') or payload.get('channel') or 'platform'
    thread_id = (resume_payload.get('thread_id') or payload.get('thread_id') or f"approval_{getattr(action, 'id', 'unknown')}")

    db.session.add(
        AgentMessage(
            company_id=getattr(action, 'company_id', None),
            user_id=getattr(action, 'user_id', None),
            agent_type='work_agent_squad',
            agent_name='workflow_approval',
            direction='outbound',
            channel=channel,
            content=message,
            metadata_json={
                'thread_id': thread_id,
                'contact': 'sapiens',
                'agent': 'workflow_approval',
                'workflow_action_id': getattr(action, 'id', None),
                **({'workflow_approval': approval_metadata} if approval_metadata else {}),
            },
        )
    )


def _render_company_onboarding_agent():
    """Renderiza o onboarding assistido de empresa com UX de agente."""
    return render_template(
        'cadastro_agent.html',
        agent_type='cadastro',
        agent_name='Onboarding Assistido de Empresa',
        agent_description='Criação guiada da empresa com contexto operacional, estratégico e readiness para IA/MCP.',
        canonical_company_route='/companies/new',
    )


def _build_sapiens_url(surface_key: str, preset: str, contact: str = 'sapiens') -> str:
    from urllib.parse import urlencode

    return f"/sapiens?{urlencode({'contact': contact, 'surface': surface_key, 'preset': preset})}"


def _render_agent_surface_wrapper(surface_key: str):
    config = AGENT_SURFACE_CONFIG[surface_key]
    return render_template(
        'agent_surface_wrapper.html',
        icon=config['icon'],
        eyebrow=config['eyebrow'],
        title=config['title'],
        description=config['description'],
        quick_steps=[
            {
                'title': '1. Abra no Sapiens',
                'body': 'A superfície já entrega um prompt inicial focado no domínio para acelerar a conversa.',
            },
            {
                'title': '2. Valide o contexto da empresa',
                'body': 'O hub usa o contexto ativo da unidade e deve operar com segurança multi-tenant.',
            },
            {
                'title': '3. Evolua por tools',
                'body': 'A próxima camada não é novo agente de tela; é tool REST + MCP com contrato claro.',
            },
        ],
        suggested_prompts=[
            {'title': 'Prompt guiado', 'body': config['preset']},
            {'title': 'Exploração controlada', 'body': 'Peça diagnóstico, lacunas, próximos passos e evidências antes de executar qualquer ação sensível.'},
            {'title': 'Escalonamento técnico', 'body': 'Se houver falha estrutural, use o Squad de Engenharia com contexto do domínio atual.'},
        ],
        governance_notes=[
            {'title': 'MCP First', 'body': 'Toda capacidade nova deste domínio deve nascer em service + REST + MCP Tool.'},
            {'title': 'Sem novos agentes de tela', 'body': 'A superfície atual é um wrapper temporário; a especialização deve ficar no catálogo de tools.'},
            {'title': 'Custo sob controle', 'body': 'A inferência pesada pode migrar para runtimes externos do cliente via MCP quando apropriado.'},
        ],
        tool_targets=config['tool_targets'],
        sapiens_url=_build_sapiens_url(surface_key, config['preset']),
        engineering_url=_build_sapiens_url(
            surface_key,
            f"Analise tecnicamente a convergência tool-first do domínio {surface_key} no APP32 e aponte riscos arquiteturais.",
            contact='engineering',
        ),
    )

@agents_bp.route('/sapiens')
@login_required
def sapiens_page():
    """Interface unificada estilo WhatsApp para todos os agentes de IA"""
    return render_template('sapiens.html')


@agents_bp.route('/sapiens/training')
@login_required
def sapiens_training_page():
    """Curadoria supervisionada para evoluir respostas do Sapiens."""
    from flask import session

    if not _has_operational_full_access(session.get('active_company_id')):
        return render_template(
            'sapiens_training.html',
            access_denied=True,
        ), 403
    return render_template('sapiens_training.html', access_denied=False)

@agents_bp.route('/agents/board')
@login_required
def ai_board():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', contact='sapiens'))

@agents_bp.route('/agents/logs')
@login_required
def get_agent_logs_page():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', view='logs'))

@agents_bp.route('/agents/engineering')
@login_required
def get_engineering_board():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', contact='engineering'))

@agents_bp.route('/agents/factory')
@login_required
def get_factory_board():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', contact='factory'))


@agents_bp.route('/api/agents/chat', methods=['POST'])
@login_required
def agents_chat():
    from flask import session

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    contact = data.get('contact', 'sapiens')
    company_id = session.get('active_company_id')

    try:
        result = AgentConversationService.chat_with_agent(
            user_id=int(current_user.id),
            company_id=company_id,
            message=message,
            contact=contact,
        )
        return jsonify({
            "success": True,
            "response": result["response"],
            "agent": result["agent"],
            "thread_id": result["thread_id"],
            "menu_metadata": result.get("menu_metadata") or {},
        })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception("Erro no endpoint /api/agents/chat para user_id=%s", getattr(current_user, "id", None))
        return jsonify({
            "success": False,
            "error": PUBLIC_ERROR_MESSAGE
        }), 500


@agents_bp.route('/api/agents/knowledge/answer', methods=['POST'])
@login_required
def answer_sapiens_knowledge():
    """Responde pela camada estruturada sem aceitar company_id do cliente."""
    from flask import session
    from services.knowledge.interaction_service import KnowledgeInteractionService
    from services.knowledge.query_service import KnowledgeQueryError

    data = request.get_json(silent=True) or {}
    try:
        result = KnowledgeInteractionService().answer(
            data.get("question"),
            scope=data.get("scope", "all"),
            company_id=session.get("active_company_id"),
            user_id=int(current_user.id),
            employee_id=getattr(current_user, "employee_id", None),
            source_types=data.get("source_types")
            if isinstance(data.get("source_types"), list)
            else (),
            limit=5,
        )
        return jsonify({"success": True, **result})
    except KnowledgeQueryError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Erro na consulta web de conhecimento para user_id=%s",
            getattr(current_user, "id", None),
        )
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/knowledge/feedback', methods=['POST'])
@login_required
def register_sapiens_knowledge_feedback():
    """Registra avaliação supervisionada sem aceitar company_id do cliente."""
    from flask import session
    from services.knowledge.feedback_service import (
        KnowledgeFeedbackError,
        KnowledgeFeedbackService,
    )

    data = request.get_json(silent=True) or {}
    try:
        result = KnowledgeFeedbackService().register_feedback(
            interaction_id=data.get("interaction_id"),
            rating=data.get("rating"),
            reason=data.get("reason"),
            comment=data.get("comment"),
            expected_answer=data.get("expected_answer"),
            metadata={
                "surface": data.get("surface") or "sapiens",
            },
            company_id=session.get("active_company_id"),
            user_id=int(current_user.id),
        )
        return jsonify({"success": True, **result})
    except KnowledgeFeedbackError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Erro ao registrar feedback de conhecimento para user_id=%s",
            getattr(current_user, "id", None),
        )
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/knowledge/training/overview', methods=['GET'])
@login_required
def sapiens_knowledge_training_overview():
    """Lista lacunas, feedbacks e propostas sem aceitar company_id do cliente."""
    from flask import session
    from services.knowledge.training_review_service import KnowledgeTrainingReviewService

    company_id = session.get("active_company_id")
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para curadoria do Sapiens."}), 403
    try:
        limit = request.args.get("limit", 50)
        result = KnowledgeTrainingReviewService().overview(company_id=company_id, limit=limit)
        return jsonify({"success": True, **result})
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Erro ao consultar treinamento do Sapiens para user_id=%s",
            getattr(current_user, "id", None),
        )
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/knowledge/training/proposals/build', methods=['POST'])
@login_required
def sapiens_knowledge_training_build_proposals():
    """Gera propostas auditáveis a partir do feedback da empresa ativa."""
    from flask import session
    from services.knowledge.training_review_service import KnowledgeTrainingReviewService

    company_id = session.get("active_company_id")
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para treinar o Sapiens."}), 403
    data = request.get_json(silent=True) or {}
    try:
        result = KnowledgeTrainingReviewService().build_proposals(
            company_id=company_id,
            min_evidence=data.get("min_evidence", 1),
            limit=data.get("limit", 100),
        )
        return jsonify({"success": True, **result})
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Erro ao gerar propostas de treinamento do Sapiens para user_id=%s",
            getattr(current_user, "id", None),
        )
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/knowledge/training/proposals/<string:proposal_id>/decision', methods=['POST'])
@login_required
def sapiens_knowledge_training_decide_proposal(proposal_id):
    """Aprova ou rejeita proposta sem aplicar automaticamente no produto."""
    from flask import session
    from services.knowledge.training_review_service import (
        KnowledgeTrainingReviewError,
        KnowledgeTrainingReviewService,
    )

    company_id = session.get("active_company_id")
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para revisar propostas do Sapiens."}), 403
    data = request.get_json(silent=True) or {}
    try:
        result = KnowledgeTrainingReviewService().decide_proposal(
            company_id=company_id,
            proposal_id=proposal_id,
            decision=data.get("decision"),
            note=data.get("note"),
            user_id=int(current_user.id),
        )
        return jsonify({"success": True, **result})
    except KnowledgeTrainingReviewError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        from models import db
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Erro ao revisar proposta de treinamento do Sapiens para user_id=%s",
            getattr(current_user, "id", None),
        )
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500

@agents_bp.route('/api/agents/diagnostics', methods=['GET'])
@login_required
def agents_diagnostics():
    """Rota de diagnóstico profundo para o Agente Sapiens V2 (@ARQUITETO)"""
    from flask import session
    from src.intelligence.diagnostics import run_deep_diagnostics
    
    # Simula o contexto do Agente para o diagnóstico
    company_id = session.get('active_company_id')
    user_id = current_user.id
    
    report = run_deep_diagnostics(user_id, company_id)
    return jsonify(report)

@agents_bp.route('/api/agents/actions/pending', methods=['GET'])
@login_required
def get_pending_actions():
    from models.agent_action import AgentAction
    from flask import session
    
    company_id = session.get('active_company_id')
    actions = AgentAction.query.filter_by(
        company_id=company_id, 
        status='pending'
    ).all()
    
    return jsonify({
        "success": True,
        "actions": [a.to_dict() for a in actions]
    })


@agents_bp.route('/api/agents/workflows/catalog', methods=['GET'])
@login_required
def workflow_catalog():
    from flask import session
    from sqlalchemy import or_
    from models.agent_menu import AgentMenuOption
    from models.workflow_gap import WorkflowGapCandidate
    from models.workflow_usage import WorkflowExecutionLog
    from services.workflow_catalog_service import build_workflow_catalog

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar o catálogo operacional de workflows."}), 403
    include_inactive = (request.args.get('include_inactive') or 'false').strip().lower() == 'true'
    include_global = (request.args.get('include_global') or 'true').strip().lower() != 'false'
    limit_raw = (request.args.get('limit') or '500').strip()

    try:
        limit = max(1, min(int(limit_raw), 1000))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    option_query = AgentMenuOption.query
    if active_company_id is not None:
        company_filters = [AgentMenuOption.company_id == active_company_id]
        if include_global:
            company_filters.append(AgentMenuOption.company_id.is_(None))
        option_query = option_query.filter(or_(*company_filters))
    elif not include_global:
        option_query = option_query.filter(AgentMenuOption.company_id.isnot(None))
    if not include_inactive:
        option_query = option_query.filter_by(is_active=True)

    options = option_query.order_by(AgentMenuOption.sort_order.asc(), AgentMenuOption.code.asc()).all()

    codes = [str(option.code or '').strip() for option in options if str(option.action_key or '').strip()]
    usage_logs = []
    gap_candidates = []
    if codes:
        usage_query = WorkflowExecutionLog.query
        if active_company_id is not None:
            usage_query = usage_query.filter_by(company_id=active_company_id)
        usage_logs = usage_query.order_by(WorkflowExecutionLog.updated_at.desc()).limit(limit).all()

        gap_query = WorkflowGapCandidate.query
        if active_company_id is not None:
            gap_query = gap_query.filter(
                or_(
                    WorkflowGapCandidate.company_id == active_company_id,
                    WorkflowGapCandidate.company_id.is_(None),
                )
            )
        gap_candidates = gap_query.order_by(WorkflowGapCandidate.created_at.desc()).limit(limit).all()

    catalog = build_workflow_catalog(
        options=options,
        usage_logs=usage_logs,
        gap_candidates=gap_candidates,
        preferred_company_id=active_company_id,
    )
    return jsonify({
        "success": True,
        "filters": {
            "include_inactive": include_inactive,
            "include_global": include_global,
            "limit": limit,
            "active_company_id": active_company_id,
        },
        **catalog,
    })


@agents_bp.route('/api/agents/workflow-gaps', methods=['GET'])
@login_required
def list_workflow_gaps():
    from flask import session
    from sqlalchemy import or_
    from models.workflow_gap import WorkflowGapCandidate
    from services.workflow_gap_service import serialize_workflow_gap_candidate

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para listar gaps operacionais de workflows."}), 403
    status_filter = (request.args.get('status') or 'all').strip().lower()
    channel_filter = (request.args.get('channel') or '').strip().lower()
    source_filter = (request.args.get('source') or '').strip().lower()
    resolution_filter = (request.args.get('resolution_type') or '').strip().lower()
    user_id_filter = (request.args.get('user_id') or '').strip()
    limit_raw = (request.args.get('limit') or '50').strip()

    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    query = WorkflowGapCandidate.query
    if active_company_id:
        query = query.filter(
            or_(
                WorkflowGapCandidate.company_id == active_company_id,
                WorkflowGapCandidate.company_id.is_(None),
            )
        )
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if channel_filter:
        query = query.filter_by(channel=channel_filter)
    if source_filter:
        query = query.filter_by(source=source_filter)
    if resolution_filter:
        query = query.filter_by(resolution_type=resolution_filter)
    if user_id_filter:
        if not user_id_filter.isdigit():
            return jsonify({"success": False, "error": "Parâmetro user_id inválido."}), 400
        query = query.filter_by(user_id=int(user_id_filter))

    items = query.order_by(WorkflowGapCandidate.created_at.desc()).limit(limit).all()
    serialized = [serialize_workflow_gap_candidate(item) for item in items]

    return jsonify({
        "success": True,
        "count": len(serialized),
        "filters": {
            "status": status_filter,
            "channel": channel_filter or None,
            "source": source_filter or None,
            "resolution_type": resolution_filter or None,
            "user_id": int(user_id_filter) if user_id_filter.isdigit() else None,
            "limit": limit,
            "active_company_id": active_company_id,
        },
        "workflow_gaps": serialized,
    })


@agents_bp.route('/api/agents/workflow-gaps/metrics', methods=['GET'])
@login_required
def workflow_gap_metrics():
    from flask import session
    from sqlalchemy import or_
    from models.workflow_gap import WorkflowGapCandidate
    from services.workflow_gap_service import build_workflow_gap_metrics

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar métricas operacionais de workflow gaps."}), 403

    limit_raw = (request.args.get('limit') or '500').strip()
    try:
        limit = max(1, min(int(limit_raw), 1000))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    query = WorkflowGapCandidate.query
    if active_company_id:
        query = query.filter(
            or_(
                WorkflowGapCandidate.company_id == active_company_id,
                WorkflowGapCandidate.company_id.is_(None),
            )
        )

    items = query.order_by(WorkflowGapCandidate.created_at.desc()).limit(limit).all()
    return jsonify({
        "success": True,
        "limit": limit,
        "active_company_id": active_company_id,
        "metrics": build_workflow_gap_metrics(items),
    })


@agents_bp.route('/api/agents/workflow-gaps/maintenance/reclassify', methods=['POST'])
@login_required
def reclassify_workflow_gaps():
    from flask import session
    from sqlalchemy import or_
    from models.workflow_gap import WorkflowGapCandidate
    from services.workflow_gap_service import reclassify_workflow_gap_candidates

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para reclassificar workflow gaps operacionais."}), 403

    body = request.get_json(silent=True) or {}
    status_filter = str(body.get('status') or 'inbox').strip().lower()
    limit_raw = str(body.get('limit') or '200').strip()
    persist = bool(body.get('persist'))

    try:
        limit = max(1, min(int(limit_raw), 1000))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    query = WorkflowGapCandidate.query
    if active_company_id:
        query = query.filter(
            or_(
                WorkflowGapCandidate.company_id == active_company_id,
                WorkflowGapCandidate.company_id.is_(None),
            )
        )
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    items = query.order_by(WorkflowGapCandidate.created_at.desc()).limit(limit).all()
    report = reclassify_workflow_gap_candidates(items, persist=persist)
    return jsonify({
        "success": True,
        "active_company_id": active_company_id,
        "persist": persist,
        "status": status_filter,
        "limit": limit,
        **report,
    })


@agents_bp.route('/api/agents/conversation-regression/run', methods=['POST'])
@login_required
def run_conversation_regression_pipeline():
    from flask import session
    from services.conversation_regression_backlog_service import ConversationRegressionBacklogService
    from services.conversation_regression_service import ConversationRegressionService

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para executar a pipeline de regressão conversacional."}), 403

    body = request.get_json(silent=True) or {}
    status_filter = str(body.get('status') or 'inbox').strip().lower() or 'inbox'
    limit_raw = str(body.get('limit') or '100').strip()
    snapshot_dir = str(body.get('snapshot_dir') or '').strip() or None
    sync_backlog = bool(body.get('sync_backlog', True))
    persist_snapshot = bool(body.get('persist_snapshot', False))
    persist_backlog = bool(body.get('persist_backlog', True))
    company_id = body.get('company_id', active_company_id)
    if company_id in {'', None}:
        company_id = active_company_id

    try:
        limit = max(1, min(int(limit_raw), 500))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    if company_id is not None:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Parâmetro company_id inválido."}), 400
        if not _has_operational_full_access(company_id):
            return jsonify({"success": False, "error": "Sem permissão para executar a pipeline no escopo informado."}), 403

    candidates = ConversationRegressionService.collect_workflow_gap_candidates(
        status=status_filter,
        limit=limit,
        company_id=company_id,
    )
    snapshot = ConversationRegressionService.build_snapshot(workflow_gap_candidates=candidates)

    persisted_paths = None
    if persist_snapshot and snapshot_dir:
        persisted_paths = ConversationRegressionService.persist_snapshot(snapshot, output_dir=snapshot_dir)

    backlog_sync = snapshot.get('backlog_sync')
    if sync_backlog:
        backlog_sync = ConversationRegressionBacklogService.apply_sync_payload(
            snapshot.get('backlog_sync') or {},
            user_id=int(getattr(current_user, 'id', 0) or 0),
            allowed_company_ids=[company_id] if company_id is not None else None,
            persist=persist_backlog,
        )

    return jsonify({
        "success": True,
        "filters": {
            "status": status_filter,
            "limit": limit,
            "company_id": company_id,
            "active_company_id": active_company_id,
        },
        "report": snapshot.get('report'),
        "backlog_sync": backlog_sync,
        "persisted_paths": persisted_paths,
    })


@agents_bp.route('/api/agents/workflow-gaps/link', methods=['GET'])
@login_required
def get_workflow_gap_link():
    from flask import session
    from services.workflow_gap_service import find_workflow_gap_by_task, serialize_workflow_gap_candidate

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar vínculo operacional de workflow gap."}), 403
    task_id_raw = (request.args.get('task_id') or '').strip()
    task_code = (request.args.get('task_code') or '').strip()

    task_id = None
    if task_id_raw:
        if not task_id_raw.isdigit():
            return jsonify({"success": False, "error": "Parâmetro task_id inválido."}), 400
        task_id = int(task_id_raw)

    if not task_id and not task_code:
        return jsonify({"success": False, "error": "Informe task_id ou task_code para localizar o vínculo."}), 400

    gap = find_workflow_gap_by_task(task_id=task_id, task_code=task_code)
    if gap is None:
        return jsonify({
            "success": True,
            "found": False,
            "active_company_id": active_company_id,
            "workflow_gap": None,
        })

    if active_company_id and getattr(gap, 'company_id', None) not in {None, active_company_id}:
        return jsonify({"success": False, "error": "Workflow gap fora do contexto da empresa ativa."}), 403

    return jsonify({
        "success": True,
        "found": True,
        "active_company_id": active_company_id,
        "workflow_gap": serialize_workflow_gap_candidate(gap),
    })


@agents_bp.route('/api/agents/workflow-usage', methods=['GET'])
@login_required
def list_workflow_usage_logs():
    from flask import session
    from sqlalchemy import or_
    from models.workflow_usage import WorkflowExecutionLog
    from services.workflow_usage_service import serialize_workflow_execution_log

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para listar auditoria operacional de workflows."}), 403
    status_filter = (request.args.get('status') or 'all').strip().lower()
    action_key_filter = (request.args.get('action_key') or '').strip().lower()
    channel_filter = (request.args.get('channel') or '').strip().lower()
    user_id_filter = (request.args.get('user_id') or '').strip()
    limit_raw = (request.args.get('limit') or '50').strip()

    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    query = WorkflowExecutionLog.query
    if active_company_id:
        query = query.filter(
            or_(
                WorkflowExecutionLog.company_id == active_company_id,
                WorkflowExecutionLog.company_id.is_(None),
            )
        )
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if action_key_filter:
        query = query.filter_by(action_key=action_key_filter)
    if channel_filter:
        query = query.filter_by(channel=channel_filter)
    if user_id_filter:
        if not user_id_filter.isdigit():
            return jsonify({"success": False, "error": "Parâmetro user_id inválido."}), 400
        query = query.filter_by(user_id=int(user_id_filter))

    items = query.order_by(WorkflowExecutionLog.updated_at.desc()).limit(limit).all()
    serialized = [serialize_workflow_execution_log(item) for item in items]

    return jsonify({
        "success": True,
        "count": len(serialized),
        "filters": {
            "status": status_filter,
            "action_key": action_key_filter or None,
            "channel": channel_filter or None,
            "user_id": int(user_id_filter) if user_id_filter.isdigit() else None,
            "limit": limit,
            "active_company_id": active_company_id,
        },
        "workflow_usage": serialized,
    })


@agents_bp.route('/api/agents/workflow-usage/metrics', methods=['GET'])
@login_required
def workflow_usage_metrics():
    from flask import session
    from models.workflow_usage import WorkflowExecutionLog
    from services.workflow_usage_service import build_workflow_usage_metrics

    company_id = session.get('active_company_id')
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar métricas operacionais de workflows."}), 403
    limit_raw = (request.args.get('limit') or '500').strip()
    try:
        limit = max(1, min(int(limit_raw), 1000))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    items = (
        WorkflowExecutionLog.query
        .filter_by(company_id=company_id)
        .order_by(WorkflowExecutionLog.updated_at.desc())
        .limit(limit)
        .all()
    )

    return jsonify({
        "success": True,
        "limit": limit,
        "metrics": build_workflow_usage_metrics(items),
    })


@agents_bp.route('/api/agents/actions/workflow-approvals', methods=['GET'])
@login_required
def list_workflow_approvals():
    from flask import session
    from models.agent_action import AgentAction
    from services.workflow_approval_service import serialize_workflow_approval_action

    company_id = session.get('active_company_id')
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para listar approvals operacionais."}), 403
    status_filter = (request.args.get('status') or 'pending').strip().lower()
    if status_filter not in {'pending', 'approved', 'executed', 'rejected', 'all', 'expired'}:
        return jsonify({"success": False, "error": "Parâmetro status inválido."}), 400
    action_key_filter = (request.args.get('action_key') or '').strip().lower()
    channel_filter = (request.args.get('channel') or '').strip().lower()
    user_id_filter = (request.args.get('user_id') or '').strip()
    limit_raw = (request.args.get('limit') or '50').strip()

    try:
        limit = max(1, min(int(limit_raw), 100))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    query = AgentAction.query.filter_by(
        company_id=company_id,
        type='workflow_approval_request',
    )
    if status_filter not in {'all', 'expired'}:
        query = query.filter_by(status=status_filter)

    actions = query.order_by(AgentAction.created_at.desc()).limit(limit).all()

    serialized = []
    for action in actions:
        item = serialize_workflow_approval_action(action)
        approval = item.get('approval') or {}
        if status_filter == 'expired' and not approval.get('expired'):
            continue
        if status_filter == 'pending' and approval.get('expired'):
            continue
        if action_key_filter and str(approval.get('action_key') or '').strip().lower() != action_key_filter:
            continue
        if channel_filter and str(approval.get('channel') or '').strip().lower() != channel_filter:
            continue
        if user_id_filter and str(item.get('user_id') or '') != user_id_filter:
            continue
        serialized.append(item)

    return jsonify({
        "success": True,
        "filters": {
            "status": status_filter,
            "action_key": action_key_filter or None,
            "channel": channel_filter or None,
            "user_id": int(user_id_filter) if user_id_filter.isdigit() else None,
            "limit": limit,
        },
        "count": len(serialized),
        "workflow_approvals": serialized,
    })

@agents_bp.route('/api/agents/actions/workflow-approvals/board', methods=['GET'])
@login_required
def workflow_approval_board():
    from flask import session
    from models.agent_action import AgentAction
    from services.workflow_approval_service import build_workflow_approval_board

    company_id = session.get('active_company_id')
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar o painel operacional."}), 403
    limit_raw = (request.args.get('limit') or '50').strip()
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    actions = (
        AgentAction.query.filter_by(company_id=company_id, type='workflow_approval_request')
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
        .all()
    )

    board = build_workflow_approval_board(actions)
    return jsonify({
        "success": True,
        "limit": limit,
        **board,
    })


@agents_bp.route('/api/agents/actions/workflow-approvals/metrics', methods=['GET'])
@login_required
def workflow_approval_metrics():
    from flask import session
    from models.agent_action import AgentAction
    from services.workflow_approval_service import build_workflow_approval_metrics

    company_id = session.get('active_company_id')
    if not _has_operational_full_access(company_id):
        return jsonify({"success": False, "error": "Sem permissão para consultar métricas operacionais."}), 403
    limit_raw = (request.args.get('limit') or '200').strip()
    try:
        limit = max(1, min(int(limit_raw), 500))
    except ValueError:
        return jsonify({"success": False, "error": "Parâmetro limit inválido."}), 400

    actions = (
        AgentAction.query.filter_by(company_id=company_id, type='workflow_approval_request')
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
        .all()
    )

    metrics = build_workflow_approval_metrics(actions)
    return jsonify({
        "success": True,
        "limit": limit,
        "metrics": metrics,
    })


@agents_bp.route('/api/agents/history', methods=['GET'])
@login_required
def get_chat_history():
    from models import AgentMessage
    from flask import session
    
    company_id = session.get('active_company_id')
    contact = request.args.get('contact', 'sapiens')
    target_user_id = request.args.get('user_id')
    
    # Se não for especificado user_id, usa o atual
    # Se for admin, pode ver de outros, senão, apenas o seu
    if not target_user_id or not _is_platform_admin_local():
        target_user_id = current_user.id
    
    agent_type = 'work_agent_squad'
    if contact == 'engineering':
        agent_type = 'engineering_squad'
        from sqlalchemy import or_
        messages = AgentMessage.query.filter(
            AgentMessage.company_id == company_id,
            AgentMessage.user_id == target_user_id,
            or_(
                AgentMessage.agent_type == 'engineering_squad',
                AgentMessage.content.contains('[CANAL ENGENHARIA]')
            )
        ).order_by(AgentMessage.created_at.asc()).limit(100).all()
    else:
        # Padrão: Sapiens ou um usuário específico
        filters = [
            AgentMessage.company_id == company_id,
            AgentMessage.user_id == target_user_id,
            ~AgentMessage.content.contains('[CANAL ENGENHARIA]')
        ]
        
        # Se o "contact" for um ID numérico, estamos vendo a conversa de um usuário específico com o Sapiens
        # Nesse caso, o agent_type deve ser o padrão do Sapiens
        messages = AgentMessage.query.filter(*filters).order_by(AgentMessage.created_at.asc()).limit(100).all()
    
    return jsonify({
        "success": True,
        "history": [m.to_dict() for m in messages]
    })

@agents_bp.route('/api/agents/contacts', methods=['GET'])
@login_required
def get_agents_contacts():
    from models import db, AgentMessage, User
    from flask import session
    from sqlalchemy import func
    
    company_id = session.get('active_company_id')
    
    # 1. Contatos Fixos (Bots)
    contacts = [
        {
            "id": "sapiens",
            "name": "Sapiens",
            "avatar": "🧭",
            "status": "online",
            "description": "Líder Supervisor & Especialistas",
            "type": "bot"
        },
        {
            "id": "engineering",
            "name": "Squad Engenharia",
            "avatar": "🛠️",
            "status": "online",
            "description": "@Arquitetos & @QA Automation",
            "type": "bot"
        },
        {
            "id": "factory",
            "name": "Sapiens Factory",
            "avatar": "🏭",
            "status": "online",
            "description": "Factory assistida para evolução técnica com governança",
            "type": "bot"
        }
    ]
    
    # 2. Usuários que interagiram (apenas para Admins)
    if _is_platform_admin_local():
        # Busca subquery de usuários com mensagens
        user_ids_query = db.session.query(AgentMessage.user_id).filter(
            AgentMessage.company_id == company_id
        ).distinct()
        
        users = User.query.filter(User.id.in_(user_ids_query)).all()
        
        for u in users:
            # Pula o próprio usuário admin para não duplicar se ele for o contato principal
            if u.id == current_user.id:
                continue
                
            contacts.append({
                "id": str(u.id),
                "name": u.name,
                "avatar": u.name[0].upper(),
                "status": "recent",
                "description": u.email,
                "type": "user"
            })
            
    return jsonify({
        "success": True,
        "contacts": contacts
    })


@agents_bp.route('/api/agents', methods=['GET'])
@login_required
def list_agents():
    from models.ai_agent import AIAgent

    rows = AIAgent.query.order_by(AIAgent.created_at.desc()).all()
    agents = []
    for row in rows:
        item = row.to_dict()
        activation = item.get("activation", {})
        agents.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description"),
                "status": item.get("status"),
                "page": activation.get("page"),
                "section": activation.get("section"),
                "version": item.get("version"),
            }
        )

    return jsonify({"success": True, "agents": agents})


@agents_bp.route('/api/agents/<string:agent_id>/test', methods=['POST'])
@login_required
def test_agent(agent_id):
    from models.ai_agent import AIAgent
    from services.ai_service import AIService

    agent = AIAgent.query.filter_by(id=agent_id).first()
    if not agent:
        return jsonify({"success": False, "error": "Agente nao encontrado."}), 404

    prompt_configured = bool((agent.prompt_template or "").strip())
    ai_result = AIService().test_connection()

    result = {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "agent_status": agent.status,
        "prompt_configured": prompt_configured,
        "ai_connection": ai_result,
    }

    success = bool(ai_result.get("success")) and prompt_configured
    if not prompt_configured:
        result["warning"] = "Prompt template do agente nao configurado."

    return jsonify({"success": success, "result": result})


def _menu_admin_guard():
    if not _is_platform_admin_local():
        return jsonify({
            "success": False,
            "error": "Apenas administradores podem editar o menu de agentes."
        }), 403
    return None


def _to_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y', 'sim'}


@agents_bp.route('/api/agents/menu/options', methods=['GET'])
@login_required
def list_agent_menu_options():
    from flask import session
    from src.intelligence.menu_engine import list_menu_options

    active_company_id = session.get('active_company_id')
    parent_code = request.args.get('parent_code')
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    include_global = request.args.get('include_global', 'true').lower() == 'true'

    # Admin pode consultar menu de qualquer empresa explicitamente
    company_id_param = request.args.get('company_id')
    if is_platform_admin() and company_id_param is not None:
        try:
            company_id = int(company_id_param)
        except ValueError:
            return jsonify({"success": False, "error": "company_id invalido"}), 400
    else:
        company_id = active_company_id

    options = list_menu_options(
        company_id=company_id,
        parent_code=parent_code,
        include_inactive=include_inactive,
        include_global=include_global,
    )

    return jsonify({
        "success": True,
        "options": [opt.to_dict(include_children=False) for opt in options]
    })


@agents_bp.route('/api/agents/menu/options', methods=['POST'])
@login_required
def create_agent_menu_option():
    guard = _menu_admin_guard()
    if guard:
        return guard

    from flask import session
    from models import db
    from models.agent_menu import AgentMenuOption

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    title = (data.get('title') or '').strip()
    if not code or not title:
        return jsonify({
            "success": False,
            "error": "Campos obrigatorios: code e title."
        }), 400

    company_id = data.get('company_id', session.get('active_company_id'))
    if company_id in ('', 'null', 'None'):
        company_id = None
    if company_id is not None:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "company_id invalido"}), 400
    parent_id = data.get('parent_id')
    parent_code = data.get('parent_code')

    if parent_id is None and parent_code:
        candidates = AgentMenuOption.query.filter(
            AgentMenuOption.code == parent_code
        ).all()
        parent = next((p for p in candidates if p.company_id == company_id), None) or next(
            (p for p in candidates if p.company_id is None),
            None
        )
        if not parent:
            return jsonify({"success": False, "error": "parent_code nao encontrado"}), 400
        parent_id = parent.id

    existing = AgentMenuOption.query.filter_by(company_id=company_id, code=code).first()
    if existing:
        return jsonify({
            "success": False,
            "error": f"Ja existe opcao com codigo '{code}' para esta empresa."
        }), 409

    option = AgentMenuOption(
        company_id=company_id,
        parent_id=parent_id,
        code=code,
        title=title,
        action_key=data.get('action_key'),
        description=data.get('description'),
        required_fields=data.get('required_fields') or [],
        keywords=data.get('keywords') or [],
        confirmation_template=data.get('confirmation_template'),
        execution_template=data.get('execution_template'),
        sort_order=int(data.get('sort_order', 0) or 0),
        is_active=_to_bool(data.get('is_active'), default=True),
        created_by_user_id=current_user.id
    )

    try:
        db.session.add(option)
        db.session.commit()
        return jsonify({
            "success": True,
            "option": option.to_dict(include_children=False)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/menu/options/<int:option_id>', methods=['PUT', 'PATCH'])
@login_required
def update_agent_menu_option(option_id):
    guard = _menu_admin_guard()
    if guard:
        return guard

    from models import db
    from models.agent_menu import AgentMenuOption

    option = AgentMenuOption.query.get(option_id)
    if not option:
        return jsonify({"success": False, "error": "Opcao nao encontrada."}), 404

    data = request.get_json(silent=True) or {}

    allowed_fields = {
        'code', 'title', 'action_key', 'description', 'required_fields', 'keywords',
        'confirmation_template', 'execution_template', 'sort_order', 'is_active',
        'parent_id', 'company_id'
    }

    for field, value in data.items():
        if field in allowed_fields:
            setattr(option, field, value)

    if data.get('is_active', None) is not None:
        option.is_active = _to_bool(data.get('is_active'), default=option.is_active)

    if data.get('company_id', None) in ('', 'null', 'None'):
        option.company_id = None
    elif data.get('company_id', None) is not None:
        try:
            option.company_id = int(data.get('company_id'))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "company_id invalido"}), 400

    if data.get('sort_order', None) is not None:
        try:
            option.sort_order = int(data.get('sort_order'))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "sort_order invalido"}), 400

    parent_code = data.get('parent_code')
    if parent_code is not None:
        if not parent_code:
            option.parent_id = None
        else:
            candidates = AgentMenuOption.query.filter(
                AgentMenuOption.code == parent_code
            ).all()
            parent = next((p for p in candidates if p.company_id == option.company_id), None) or next(
                (p for p in candidates if p.company_id is None),
                None
            )
            if not parent:
                return jsonify({"success": False, "error": "parent_code nao encontrado"}), 400
            option.parent_id = parent.id

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "option": option.to_dict(include_children=False)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500

@agents_bp.route('/api/agents/actions/approve/<int:action_id>', methods=['POST'])
@login_required
def approve_action(action_id):
    from flask import session
    from models import db
    from models.agent_action import AgentAction
    from services.engineering_service import engineering_service
    from services.workflow_approval_service import WorkflowApprovalService
    from src.intelligence.menu_engine import execute_approved_resume_payload

    action = AgentAction.query.get(action_id)
    if not action:
        return jsonify({"success": False, "error": "Ação não encontrada."}), 404

    active_company_id = session.get('active_company_id')

    if action.type == 'workflow_approval_request':
        if not _has_operational_full_access(active_company_id):
            return jsonify({"success": False, "error": "Sem permissão para aprovar esta ação."}), 403

        service = WorkflowApprovalService(resume_executor=execute_approved_resume_payload)
        outcome = service.approve(
            action=action,
            approver_user_id=current_user.id,
            approver_name=current_user.name,
            active_company_id=active_company_id,
        )
        if outcome.success:
            _log_workflow_approval_message(action, outcome.message, outcome.audit_metadata)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": outcome.message,
                "action": action.to_dict(),
                "resume_payload": outcome.resume_payload,
                "resume_result": outcome.resume_result,
                "approval_metadata": outcome.audit_metadata,
            }), outcome.http_status

        db.session.rollback()
        return jsonify({"success": False, "error": outcome.message}), outcome.http_status

    if active_company_id and action.company_id != active_company_id:
        return jsonify({"success": False, "error": "Ação não pertence à empresa ativa."}), 403

    success, message = engineering_service.execute_repair(action_id)

    if success:
        return jsonify({
            "success": True,
            "message": message
        })
    else:
        return jsonify({"success": False, "error": message}), 500

@agents_bp.route('/api/agents/actions/revalidate/<int:action_id>', methods=['POST'])
@login_required
def revalidate_action(action_id):
    from flask import session
    from models import db
    from models.agent_action import AgentAction
    from services.workflow_approval_service import WorkflowApprovalService
    from src.intelligence.menu_engine import execute_approved_resume_payload

    action = AgentAction.query.get(action_id)
    if not action:
        return jsonify({"success": False, "error": "Ação não encontrada."}), 404

    if action.type != 'workflow_approval_request':
        return jsonify({"success": False, "error": "Ação não suporta revalidação operacional."}), 400

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para revalidar esta ação."}), 403
    service = WorkflowApprovalService(resume_executor=execute_approved_resume_payload)
    outcome = service.revalidate(
        action=action,
        approver_user_id=current_user.id,
        approver_name=current_user.name,
        active_company_id=active_company_id,
    )
    if outcome.success:
        _log_workflow_approval_message(action, outcome.message, outcome.audit_metadata)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": outcome.message,
            "action": action.to_dict(),
            "resume_payload": outcome.resume_payload,
            "approval_metadata": outcome.audit_metadata,
        }), outcome.http_status

    db.session.rollback()
    return jsonify({"success": False, "error": outcome.message, "approval_metadata": outcome.audit_metadata}), outcome.http_status


@agents_bp.route('/api/agents/actions/rollback/<int:action_id>', methods=['POST'])
@login_required
def rollback_action(action_id):
    from services.engineering_service import engineering_service
    
    success, message = engineering_service.rollback_repair(action_id)
    
    if success:
        return jsonify({
            "success": True, 
            "message": message
        })
    else:
        return jsonify({"success": False, "error": message}), 500

@agents_bp.route('/agents/planejamento')
@login_required
def agent_planejamento():
    return _render_agent_surface_wrapper('planejamento')

@agents_bp.route('/agents/processos')
@login_required
def agent_processos():
    return _render_agent_surface_wrapper('processos')

@agents_bp.route('/agents/rotina')
@login_required
def agent_rotina():
    return _render_agent_surface_wrapper('rotina')

@agents_bp.route('/agents/performance')
@login_required
def agent_performance():
    return _render_agent_surface_wrapper('performance')

@agents_bp.route('/agents/estrategico')
@login_required
def agent_estrategico():
    return _render_agent_surface_wrapper('estrategico')

@agents_bp.route('/agents/cadastro')
@login_required
def agent_cadastro():
    return _render_company_onboarding_agent()

# API Routes for Agent
@agents_bp.route('/api/cadastro-agent/empresa/iniciar', methods=['POST'])
@login_required
def iniciar_cadastro():
    data = request.get_json(silent=True) or {}
    tipo = data.get('tipo', 'real')

    try:
        payload = cadastro_service.iniciar_fluxo_empresa(
            user_id=current_user.id,
            tipo_cadastro=tipo,
        )
        return jsonify({'success': True, 'data': payload})
    except Exception:
        return jsonify({'success': False, 'error': PUBLIC_ERROR_MESSAGE}), 500

@agents_bp.route('/api/cadastro-agent/empresa/processar', methods=['POST'])
@login_required
def processar_cadastro():
    data = request.get_json(silent=True) or {}

    try:
        payload = cadastro_service.processar_fluxo_empresa(
            user_id=current_user.id,
            campo=data.get('campo'),
            valor=data.get('valor'),
            dados_coletados=data.get('dados_coletados', {}),
            tipo_cadastro=data.get('tipo', 'real'),
            session_id=data.get('session_id'),
        )
        return jsonify({'success': True, 'data': payload})
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'error': PUBLIC_ERROR_MESSAGE}), 500

@agents_bp.route('/api/cadastro-agent/empresa/finalizar', methods=['POST'])
@login_required
def finalizar_cadastro():
    data = request.get_json(silent=True) or {}
    dados = data.get('dados', {})

    try:
        payload = cadastro_service.finalizar_fluxo_empresa(
            user=current_user,
            dados_coletados=dados,
            tipo_cadastro=data.get('tipo', 'real'),
            session_id=data.get('session_id'),
        )
        return jsonify({'success': True, 'data': payload})
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception:
        return jsonify({'success': False, 'error': PUBLIC_ERROR_MESSAGE}), 500


@agents_bp.route('/api/agents/actions/reject/<int:action_id>', methods=['POST'])
@login_required
def reject_action(action_id):
    from flask import session
    from models import db
    from models.agent_action import AgentAction
    from services.workflow_approval_service import WorkflowApprovalService
    from src.intelligence.menu_engine import execute_approved_resume_payload

    action = AgentAction.query.get(action_id)
    if not action:
        return jsonify({"success": False, "error": "Ação não encontrada."}), 404

    if action.type != 'workflow_approval_request':
        return jsonify({"success": False, "error": "Ação não suporta rejeição operacional."}), 400

    active_company_id = session.get('active_company_id')
    if not _has_operational_full_access(active_company_id):
        return jsonify({"success": False, "error": "Sem permissão para rejeitar esta ação."}), 403

    feedback = (request.get_json(silent=True) or {}).get('feedback')
    service = WorkflowApprovalService(resume_executor=execute_approved_resume_payload)
    outcome = service.reject(
        action=action,
        approver_user_id=current_user.id,
        approver_name=current_user.name,
        active_company_id=active_company_id,
        feedback=feedback,
    )
    if outcome.success:
        _log_workflow_approval_message(action, outcome.message, outcome.audit_metadata)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": outcome.message,
            "action": action.to_dict(),
            "resume_payload": outcome.resume_payload,
            "approval_metadata": outcome.audit_metadata,
        }), outcome.http_status

    db.session.rollback()
    return jsonify({"success": False, "error": outcome.message}), outcome.http_status
