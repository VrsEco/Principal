from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.cadastro_agent_service import CadastroAgentService

agents_bp = Blueprint('agents', __name__)
cadastro_service = CadastroAgentService()


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

@agents_bp.route('/sapiens')
@login_required
def sapiens_page():
    """Interface unificada estilo WhatsApp para todos os agentes de IA"""
    return render_template('sapiens.html')

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

@agents_bp.route('/api/agents/chat', methods=['POST'])
@login_required
def agents_chat():
    from models import db, AgentMessage
    from flask import session
    
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    contact = data.get('contact', 'sapiens') # 'sapiens' ou 'engineering'
    
    if not message:
        return jsonify({
            "success": False,
            "error": "Mensagem vazia. Informe o que deseja executar."
        }), 400

    company_id = session.get('active_company_id')
    
    # Define o prefixo se for engenharia
    processed_message = message
    agent_type = 'work_agent_squad'
    
    if contact == 'engineering' and '[CANAL ENGENHARIA]' not in message:
        processed_message = f"[CANAL ENGENHARIA] {message}"
        agent_type = 'engineering_squad'

    # Thread unica e consistente entre logs e execucao do agente.
    thread_id = f"web_{current_user.id}_{contact}"

    # 1. Salva a mensagem do usuário (Inbound)
    user_msg = AgentMessage(
        company_id=company_id,
        user_id=current_user.id,
        agent_type=agent_type,
        agent_name='Usuário',
        direction='inbound',
        content=message,
        channel='platform',
        metadata_json={
            "contact": contact,
            "thread_id": thread_id
        }
    )

    try:
        db.session.add(user_msg)
        db.session.commit()

        # 2. Executa o Agente com Contexto Unificado (@ARQUITETO)
        from src.intelligence.execution import run_agent_with_context, extract_response_text

        response = run_agent_with_context(
            user_id=current_user.id,
            user_msg=processed_message,
            channel="web",
            thread_id=thread_id,
            company_id=company_id,
            metadata={"agent_type": agent_type, "contact": contact}
        )

        final_text = extract_response_text(response)
        fallback_agent = "engineering_squad" if contact == "engineering" else "sapiens"
        agent_executor = response.get("next_node") or fallback_agent
        if agent_executor == "end":
            agent_executor = fallback_agent
        menu_metadata = dict(response.get("menu_metadata") or {})

        # 3. Salva a resposta da IA no log de mensagens (Visual apenas)
        outbound_metadata = {
            "agent": agent_executor,
            "contact": contact,
            "thread_id": thread_id,
        }
        outbound_metadata.update(menu_metadata)
        ai_msg = AgentMessage(
            company_id=company_id,
            user_id=current_user.id,
            agent_type=agent_type,
            agent_name=agent_executor,
            direction='outbound',
            content=final_text,
            channel='platform',
            metadata_json=outbound_metadata
        )
        db.session.add(ai_msg)
        db.session.commit()

        return jsonify({
            "success": True,
            "response": final_text,
            "agent": agent_executor
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para consultar o catálogo operacional de workflows."}), 403

    active_company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para listar gaps operacionais de workflows."}), 403

    active_company_id = session.get('active_company_id')
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


@agents_bp.route('/api/agents/workflow-gaps/link', methods=['GET'])
@login_required
def get_workflow_gap_link():
    from flask import session
    from services.workflow_gap_service import find_workflow_gap_by_task, serialize_workflow_gap_candidate

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para consultar vínculo operacional de workflow gap."}), 403

    active_company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para listar auditoria operacional de workflows."}), 403

    active_company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para consultar métricas operacionais de workflows."}), 403

    company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para listar approvals operacionais."}), 403

    company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para consultar o painel operacional."}), 403

    company_id = session.get('active_company_id')
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para consultar métricas operacionais."}), 403

    company_id = session.get('active_company_id')
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
    if not target_user_id or current_user.role != 'admin':
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
        }
    ]
    
    # 2. Usuários que interagiram (apenas para Admins)
    if current_user.role == 'admin':
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
    if current_user.role != 'admin':
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
    if current_user.role == 'admin' and company_id_param is not None:
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
        return jsonify({"success": False, "error": str(e)}), 500


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
        return jsonify({"success": False, "error": str(e)}), 500

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
        if current_user.role not in {'admin', 'client'}:
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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para revalidar esta ação."}), 403

    active_company_id = session.get('active_company_id')
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
    return render_template('cadastro_agent.html', 
                           agent_type='planejamento', 
                           agent_name='Agente de Planejamento',
                           agent_description='Assistente especializado em Planejamento Estratégico e análises de mercado.')

@agents_bp.route('/agents/processos')
@login_required
def agent_processos():
    return render_template('cadastro_agent.html', 
                           agent_type='processos', 
                           agent_name='Agente de Processos',
                           agent_description='Especialista em mapeamento, análise e otimização de processos operacionais.')

@agents_bp.route('/agents/rotina')
@login_required
def agent_rotina():
    return render_template('cadastro_agent.html', 
                           agent_type='rotina', 
                           agent_name='Agente de Rotina',
                           agent_description='Focado em monitoramento, cobrança e follow-up de atividades diárias.')

@agents_bp.route('/agents/performance')
@login_required
def agent_performance():
    return render_template('cadastro_agent.html', 
                           agent_type='performance', 
                           agent_name='Agente de Performance',
                           agent_description='Análise profunda de indicadores de desempenho e resultados organizacionais.')

@agents_bp.route('/agents/estrategico')
@login_required
def agent_estrategico():
    return render_template('cadastro_agent.html', 
                           agent_type='estrategico', 
                           agent_name='Agente Estratégico',
                           agent_description='Suporte à alta gestão no monitoramento da execução da estratégia.')

@agents_bp.route('/agents/cadastro')
@login_required
def agent_cadastro():
    return render_template('cadastro_agent.html', 
                           agent_type='cadastro', 
                           agent_name='Agente de Cadastro',
                           agent_description='Assistente inteligente para cadastro e configuração de empresas e dados mestres.')

# API Routes for Agent
@agents_bp.route('/api/cadastro-agent/empresa/iniciar', methods=['POST'])
@login_required
def iniciar_cadastro():
    data = request.get_json()
    tipo = data.get('tipo', 'real')
    
    if tipo == 'real':
        return jsonify({
            'success': True,
            'data': {
                'mensagem': 'Ótimo! Para começar o cadastro da empresa real, por favor, me informe o CNPJ:',
                'proximo_campo': 'cnpj',
                'progresso': 5,
                'dados_coletados': {}
            }
        })
    else:
        return jsonify({
            'success': True,
            'data': {
                'mensagem': 'Vamos criar uma empresa exemplo. Qual nome deseja dar a ela?',
                'proximo_campo': 'name',
                'progresso': 5,
                'dados_coletados': {}
            }
        })

@agents_bp.route('/api/cadastro-agent/empresa/processar', methods=['POST'])
@login_required
def processar_cadastro():
    data = request.get_json()
    campo = data.get('campo')
    valor = data.get('valor')
    dados_coletados = data.get('dados_coletados', {})
    tipo = data.get('tipo', 'real')
    
    # Atualizar dados
    dados_coletados[campo] = valor
    
    # Se for CNPJ, buscar dados
    if campo == 'cnpj' and tipo == 'real':
        # Remove special chars for search
        cnpj_clean = "".join(filter(str.isdigit, valor))
        dados_api = cadastro_service._buscar_dados_cnpj(cnpj_clean)
        if dados_api:
            # Merge API data
            for k, v in dados_api.items():
                if v: dados_coletados[k] = v
            
            return jsonify({
                'success': True,
                'data': {
                    'mensagem': f"Encontrei os dados da empresa {dados_api.get('name')}! Algumas informações foram preenchidas automaticamente. Podemos continuar?",
                    'proximo_campo': 'segment' if 'segment' not in dados_coletados else 'city',
                    'progresso': 60,
                    'dados_coletados': dados_coletados
                }
            })

    # Sequence of fields
    sequence = ['name', 'client_code', 'cnpj', 'segment', 'city', 'state']
    if tipo == 'exemplo':
        sequence = ['name', 'segment']
        
    try:
        current_idx = sequence.index(campo)
        if current_idx + 1 < len(sequence):
            proximo = sequence[current_idx + 1]
            # Skip if already filled (from API)
            while proximo in dados_coletados and current_idx + 1 < len(sequence):
                current_idx += 1
                if current_idx + 1 < len(sequence):
                    proximo = sequence[current_idx + 1]
                else:
                    proximo = None
                    break
        else:
            proximo = None
    except ValueError:
        proximo = None

    if proximo:
        prompts = {
            'name': 'Qual o nome fantasia da empresa?',
            'client_code': 'Qual o código curto (3 letras/números) para identificação?',
            'segment': 'Qual o segmento de atuação?',
            'city': 'Em qual cidade fica a sede?',
            'state': 'E o estado (UF)?'
        }
        return jsonify({
            'success': True,
            'data': {
                'mensagem': prompts.get(proximo, f"Qual o {proximo}?"),
                'proximo_campo': proximo,
                'progresso': int((sequence.index(proximo) / len(sequence)) * 100),
                'dados_coletados': dados_coletados
            }
        })
    else:
        return jsonify({
            'success': True,
            'data': {
                'mensagem': "Tudo pronto! Já tenho os dados necessários. Podemos finalizar o cadastro?",
                'status': 'pronto_para_criar',
                'progresso': 100,
                'dados_coletados': dados_coletados
            }
        })

@agents_bp.route('/api/cadastro-agent/empresa/finalizar', methods=['POST'])
@login_required
def finalizar_cadastro():
    from models import db, Company, Role, Employee
    data = request.get_json()
    dados = data.get('dados', {})
    
    try:
        # Avoid duplicate client code
        client_code = dados.get('client_code')
        if not client_code:
            client_code = dados.get('name', 'EMP')[:3].upper()
            
        existing = Company.query.filter_by(client_code=client_code).first()
        if existing:
            import time
            client_code = f"{client_code[:2]}{int(time.time()) % 10}"

        company = Company(
            name=dados.get('name'),
            client_code=client_code,
            legal_name=dados.get('legal_name', dados.get('name')),
            cnpj=dados.get('cnpj'),
            segment=dados.get('segment'),
            city=dados.get('city'),
            state=dados.get('state')
        )
        db.session.add(company)
        db.session.commit()
        
        # Create Admin Role
        role = Role.query.filter_by(company_id=company.id, title='Administrador').first()
        if not role:
            role = Role(
                company_id=company.id, 
                title='Administrador', 
                permissions={
                    "projects": ["view", "create", "edit", "delete"],
                    "indicators": ["view", "create", "edit", "delete"],
                    "processes": ["view", "create", "edit", "delete"],
                    "companies": ["view", "edit"],
                    "okrs": ["view", "create", "edit", "delete"]
                }
            )
            db.session.add(role)
            db.session.commit()
            
        emp = Employee(
            user_id=current_user.id,
            company_id=company.id,
            role_id=role.id,
            name=current_user.name,
            email=current_user.email,
            status='active'
        )
        db.session.add(emp)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'mensagem': f"Empresa '{company.name}' criada com sucesso! Você agora é o administrador desta unidade.",
                'proximos_passos': [
                    "Acessar o módulo de 'Planejamento' para definir OKRs.",
                    "Configurar os primeiros 'Indicadores' de desempenho.",
                    "Mapear os 'Processos' críticos da operação."
                ]
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

    if current_user.role not in {'admin', 'client'}:
        return jsonify({"success": False, "error": "Sem permissão para rejeitar esta ação."}), 403

    feedback = (request.get_json(silent=True) or {}).get('feedback')
    active_company_id = session.get('active_company_id')
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
