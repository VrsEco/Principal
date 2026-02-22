from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, AIAgent, AgentMessage
from utils.permissions import permission_required

configs_bp = Blueprint('configs', __name__)

@configs_bp.route('/configs/ai')
@login_required
# @permission_required('admin', 'view') # Maybe restrict to admin?
def ai_settings():
    """AI Configuration Page"""
    agents = AIAgent.query.all()
    return render_template('configurations_ai.html', agents=agents)

@configs_bp.route('/configs/system')
@login_required
def system_settings():
    """System Configuration Page"""
    # Dummy data to prevent template errors
    audit_summary = {
        'total_routes': 0,
        'routes_with_logging': 0,
        'coverage_percentage': 0.0
    }
    log_stats = {
        'total_logs': 0,
        'actions': [],
        'top_users': []
    }
    return render_template('configs_system.html', audit_summary=audit_summary, log_stats=log_stats)

# API Endpoints

@configs_bp.route('/api/configs/ai/agents', methods=['GET'])
@login_required
def get_agents_config():
    agents = AIAgent.query.all()
    return jsonify({"success": True, "agents": [a.to_dict() for a in agents]})

@configs_bp.route('/api/configs/ai/agents/<string:agent_id>', methods=['PUT'])
@login_required
def update_agent_config(agent_id):
    data = request.get_json()
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
    limit = request.args.get('limit', 50, type=int)
    logs = AgentMessage.query.order_by(AgentMessage.created_at.desc()).limit(limit).all()
    
    return jsonify({
        "success": True, 
        "logs": [l.to_dict() for l in logs]
    })
