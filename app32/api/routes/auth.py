import logging
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from pydantic import ValidationError
from models import User, Employee, Company, ProjectTask, ProcessInstance, Project
from datetime import date, datetime, timedelta
from services.auth_service import auth_service
from services.user_mcp_token_service import user_mcp_token_service
from schemas.user_pydantic import (
    UserProfileUpdateSchema,
    UserPasswordChangeSchema,
    UserMcpTokenConfigSchema,
)
from utils.error_handling import (
    extract_validation_error_message,
    log_and_build_public_error_response,
)
from utils.permissions import can_access_company, get_default_company_id, is_platform_admin
from utils.security import consume_rate_limit, get_request_ip, rate_limit_exceeded_response

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

SUMMARY_CHANNEL_OPTIONS = {'telegram', 'whatsapp', 'email'}


def _resolve_safe_post_login_redirect() -> str | None:
    candidate = (
        request.args.get('next')
        or (request.get_json(silent=True) or {}).get('next')
        or request.form.get('next')
        or session.get('post_login_redirect')
    )
    target = str(candidate or '').strip()
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith('/'):
        return None
    if target.startswith('//'):
        return None
    return target

def _normalize_summary_delivery_channels(raw_channels):
    if raw_channels is None:
        return None
    if isinstance(raw_channels, str):
        items = [item.strip().lower() for item in raw_channels.split(',')]
    else:
        items = [str(item).strip().lower() for item in (raw_channels or [])]

    normalized = []
    for item in items:
        if item in SUMMARY_CHANNEL_OPTIONS and item not in normalized:
            normalized.append(item)

    return ','.join(normalized) if normalized else 'telegram'


def _build_project_task_code_for_portal(company_code, company_name, project_id, task_id):
    normalized_company_code = str(company_code or '').strip()
    normalized_company_name = str(company_name or '').strip()

    if not normalized_company_code and normalized_company_name:
        normalized_company_code = normalized_company_name[:2].upper()

    if normalized_company_code:
        return f"{normalized_company_code}.J.{project_id}.{task_id}"

    return f"J.{project_id}.{task_id}"


def _load_portal_project_tasks(employee_ids):
    """
    Carrega apenas os campos necessários para o portal.

    Motivo:
    - o clone local pode estar com drift de schema em colunas novas do model
      (`is_deleted`, `deleted_at`, etc.)
    - consultar a entidade completa faz o SQLAlchemy selecionar colunas ausentes
      e derruba a rota /portal com 500
    """
    if not employee_ids:
        return []

    return (
        ProjectTask.query.join(Project, Project.id == ProjectTask.project_id)
        .join(Company, Company.id == Project.company_id)
        .with_entities(
            ProjectTask.id.label('task_id'),
            ProjectTask.project_id.label('project_id'),
            ProjectTask.what.label('title'),
            ProjectTask.due_date.label('due_date'),
            ProjectTask.status.label('status'),
            ProjectTask.priority.label('priority'),
            ProjectTask.estimated_hours.label('estimated_hours'),
            Project.company_id.label('company_id'),
            Company.client_code.label('company_code'),
            Company.name.label('company_name'),
        )
        .filter(
            ProjectTask.employee_id.in_(employee_ids),
            ProjectTask.status.notin_(['completed', 'done', 'cancelled']),
            Company.is_active == True,
        )
        .all()
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        email = str(data.get('email') or '').strip().lower()
        password = str(data.get('password') or '')
        next_target = _resolve_safe_post_login_redirect()

        if not consume_rate_limit("auth.login", f"{get_request_ip()}:{email or 'anonymous'}", limit=8, window_seconds=300):
            return rate_limit_exceeded_response("Muitas tentativas de login. Aguarde alguns minutos.")
        if not email or not password:
            return jsonify({"success": False, "message": "Credenciais inválidas"}), 400
        
        user = User.query.filter_by(email=email).first()

        is_active = getattr(user, "is_active", True) if user else False
        if user and is_active and user.check_password(password):
            session.clear()
            login_user(user)
            if next_target:
                session['post_login_redirect'] = next_target
            
            # Check companies this user has access to
            employee_records = Employee.query.filter_by(user_id=user.id, status='active').all()
            active_company_ids = [
                employee.company_id
                for employee in employee_records
                if getattr(employee, 'company_id', None) is not None
            ]
            
            # Usuário com uma única empresa deve entrar direto no ambiente de trabalho
            # para evitar bloqueio operacional no portal de seleção.
            if len(active_company_ids) == 1 and not is_platform_admin():
                session['active_company_id'] = active_company_ids[0]
                final_redirect = session.pop('post_login_redirect', None) or next_target or "/my-work"
                return jsonify({"success": True, "redirect": final_redirect})

            if len(employee_records) > 0 or is_platform_admin():
                final_redirect = session.pop('post_login_redirect', None) or next_target or "/portal"
                return jsonify({"success": True, "redirect": final_redirect})
            else:
                return jsonify({"success": False, "message": "Usuário não possui empresas vinculadas."}), 403
             
        return jsonify({"success": False, "message": "Credenciais inválidas"}), 401
    
    return render_template('auth/login_v2.html')

@auth_bp.route('/portal', methods=['GET', 'POST'])
@login_required
def portal():
    """Portal page to select active company and view notes"""
    if request.method == 'POST':
        data = request.get_json()
        company_id = data.get('company_id')
        
        if not company_id:
            return jsonify({"success": False, "message": "Empresa não informada"}), 400
            
        # Verify if user has access to this company
        if not can_access_company(company_id):
            return jsonify({"success": False, "message": "Acesso negado a esta empresa"}), 403
        
        session['active_company_id'] = company_id
        return jsonify({"success": True, "redirect": "/my-work"})

    # GET: Show list of companies
    employee_records = Employee.query.filter_by(user_id=current_user.id, status='active').all()
    employee_ids = [e.id for e in employee_records]

    if is_platform_admin():
        companies = Company.query.filter_by(is_active=True).all()
    else:
        company_ids = [e.company_id for e in employee_records]
        companies = Company.query.filter(Company.id.in_(company_ids), Company.is_active == True).all()

    default_company_id = get_default_company_id()
    if default_company_id and 'active_company_id' not in session:
        session['active_company_id'] = default_company_id

    # Fetch activities (Todas as atividades não concluídas)
    activities = []
    today = date.today()
    next_week = today + timedelta(days=7)
    
    stats = {
        "total": 0,
        "overdue": 0,
        "planned": 0,
        "hours_total": 0.0
    }

    if employee_ids:
        # 1. Project Tasks
        tasks = _load_portal_project_tasks(employee_ids)
        
        for t in tasks:
            task_date = (t.due_date.date() if isinstance(t.due_date, datetime) else t.due_date) if t.due_date else None
            is_overdue = task_date < today if task_date else False
            
            # Adiciona aos KPIs globais
            stats["total"] += 1
            if is_overdue:
                stats["overdue"] += 1
            else:
                stats["planned"] += 1
            stats["hours_total"] += float(t.estimated_hours or 0)

            # Filtra para a lista (atrasadas ou próximas 7 dias)
            if is_overdue or (task_date and task_date <= next_week):
                activities.append({
                    "type": "projeto",
                    "category": "Projeto",
                    "company_id": t.company_id,
                    "title": t.title,
                    "code": _build_project_task_code_for_portal(
                        t.company_code,
                        t.company_name,
                        t.project_id,
                        t.task_id,
                    ),
                    "due_date": t.due_date,
                    "status": t.status,
                    "priority": t.priority or "Normal",
                    "is_overdue": is_overdue,
                    "is_planned": task_date > today if task_date else False
                })
            
        # 2. Process Instances
        all_instances = ProcessInstance.query.join(Company).filter(
            ProcessInstance.status.notin_(['completed', 'done', 'cancelled']),
            Company.is_active == True
        ).all()
        
        for inst in all_instances:
            collabs = inst.collaborators_json or []
            if any(c.get('id') in employee_ids for c in collabs):
                inst_date = (inst.due_date.date() if isinstance(inst.due_date, datetime) else inst.due_date) if inst.due_date else None
                is_overdue = inst_date < today if inst_date else False
                
                # Adiciona aos KPIs globais
                stats["total"] += 1
                if is_overdue:
                    stats["overdue"] += 1
                else:
                    stats["planned"] += 1
                stats["hours_total"] += float(inst.estimated_hours or 0)

                # Filtra para a lista
                if is_overdue or (inst_date and inst_date <= next_week):
                    activities.append({
                        "type": "processo",
                        "category": "Processo",
                        "company_id": inst.company_id,
                        "title": inst.title,
                        "code": inst.instance_code,
                        "due_date": inst.due_date,
                        "status": inst.status,
                        "priority": inst.priority or "Alta",
                        "is_overdue": is_overdue,
                        "is_planned": inst_date > today if inst_date else False
                    })

    # Map companies for display names (Code - Name)
    comp_display = {c.id: f"{c.client_code} - {c.name}" if c.client_code else c.name for c in companies}
    
    for act in activities:
        cid = act.get('company_id')
        if cid:
            if cid not in comp_display:
                c = Company.query.get(cid)
                if c:
                    comp_display[cid] = f"{c.client_code} - {c.name}" if c.client_code else c.name
            
            act['type'] = comp_display.get(cid, act['type'])

    # Sort activities: Overdue first, then by date
    activities.sort(key=lambda x: (not x['is_overdue'], (x['due_date'].date() if isinstance(x['due_date'], datetime) else x['due_date']) if x['due_date'] else date.max))

    return render_template('auth/portal.html', companies=companies, urgencies=activities, stats=stats)

@auth_bp.route('/auth/profile', methods=['GET', 'POST'])
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Página de autoatendimento do usuário para dados básicos."""
    if request.method == 'GET':
        return render_template('auth/profile.html', user=current_user)

    try:
        payload = request.get_json(silent=True) or {}
        validated = UserProfileUpdateSchema(**payload)
        success = auth_service.update_user_profile(
            current_user,
            name=validated.name.strip(),
            whatsapp=validated.whatsapp,
            telegram=validated.telegram,
            instagram=validated.instagram,
            summary_delivery_channels=_normalize_summary_delivery_channels(validated.summary_delivery_channels),
        )
        if not success:
            return jsonify({"success": False, "message": "Falha ao atualizar perfil"}), 400

        return jsonify({
            "success": True,
            "message": "Perfil atualizado com sucesso!",
            "user": current_user.to_dict(),
        })
    except ValidationError as exc:
        message = extract_validation_error_message(
            exc,
            fallback_message='Dados inválidos para atualização do perfil',
        )
        return jsonify({"success": False, "message": message}), 400
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao atualizar perfil do usuário autenticado',
            success=False,
        )


@auth_bp.route('/auth/change-password', methods=['POST'])
@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Permite ao próprio usuário alterar sua senha."""
    try:
        payload = request.get_json(silent=True) or {}
        validated = UserPasswordChangeSchema(**payload)

        if validated.new_password != validated.confirm_password:
            return jsonify({"success": False, "message": "Nova senha e confirmação não coincidem"}), 400

        success = auth_service.change_password(
            current_user,
            validated.old_password,
            validated.new_password,
        )
        if not success:
            return jsonify({"success": False, "message": "Senha atual incorreta"}), 400

        return jsonify({"success": True, "message": "Senha alterada com sucesso"})
    except ValidationError as exc:
        message = extract_validation_error_message(
            exc,
            fallback_message='Dados inválidos para alteração de senha',
        )
        return jsonify({"success": False, "message": message}), 400
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao alterar senha do usuário autenticado',
            success=False,
        )


@auth_bp.route('/auth/profile/mcp-token/status', methods=['GET'])
@auth_bp.route('/profile/mcp-token/status', methods=['GET'])
@login_required
def profile_mcp_token_status():
    try:
        status = user_mcp_token_service.get_status(current_user.id)
        return jsonify({"success": True, "data": status})
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao consultar status do token MCP do usuário autenticado',
            success=False,
        )


def _parse_mcp_config_payload():
    payload = request.get_json(silent=True) or {}
    return UserMcpTokenConfigSchema(**payload)


@auth_bp.route('/auth/profile/mcp-token/generate', methods=['POST'])
@auth_bp.route('/profile/mcp-token/generate', methods=['POST'])
@login_required
def generate_profile_mcp_token():
    try:
        validated = _parse_mcp_config_payload()
        result = user_mcp_token_service.generate_token(
            user_id=current_user.id,
            created_by_user_id=current_user.id,
            company_id=validated.company_id,
            surface=validated.surface,
            client_name=validated.client_name,
            runtime=validated.runtime,
            squad=validated.squad,
        )
        return jsonify({"success": True, "message": "Token MCP gerado com sucesso.", "data": result})
    except ValidationError as exc:
        message = extract_validation_error_message(
            exc,
            fallback_message='Dados inválidos para geração do token MCP',
        )
        return jsonify({"success": False, "message": message}), 400
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao gerar token MCP do usuário autenticado',
            success=False,
        )


@auth_bp.route('/auth/profile/mcp-token/renew', methods=['POST'])
@auth_bp.route('/profile/mcp-token/renew', methods=['POST'])
@login_required
def renew_profile_mcp_token():
    try:
        validated = _parse_mcp_config_payload()
        result = user_mcp_token_service.renew_token(
            user_id=current_user.id,
            renewed_by_user_id=current_user.id,
            company_id=validated.company_id,
            surface=validated.surface,
            client_name=validated.client_name,
            runtime=validated.runtime,
            squad=validated.squad,
        )
        return jsonify({"success": True, "message": "Token MCP renovado com sucesso.", "data": result})
    except ValidationError as exc:
        message = extract_validation_error_message(
            exc,
            fallback_message='Dados inválidos para renovação do token MCP',
        )
        return jsonify({"success": False, "message": message}), 400
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao renovar token MCP do usuário autenticado',
            success=False,
        )


@auth_bp.route('/auth/profile/mcp-token/revoke', methods=['POST'])
@auth_bp.route('/profile/mcp-token/revoke', methods=['POST'])
@login_required
def revoke_profile_mcp_token():
    try:
        status = user_mcp_token_service.revoke_token(
            user_id=current_user.id,
            revoked_by_user_id=current_user.id,
        )
        return jsonify({"success": True, "message": "Token MCP revogado com sucesso.", "data": status})
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao revogar token MCP do usuário autenticado',
            success=False,
        )


@auth_bp.route('/auth/profile/mcp-token/config', methods=['POST'])
@auth_bp.route('/profile/mcp-token/config', methods=['POST'])
@login_required
def profile_mcp_token_config():
    try:
        validated = _parse_mcp_config_payload()
        config = user_mcp_token_service.build_client_config(
            user_id=current_user.id,
            company_id=validated.company_id,
            surface=validated.surface,
            client_name=validated.client_name,
            runtime=validated.runtime,
            squad=validated.squad,
        )
        return jsonify({"success": True, "data": config})
    except ValidationError as exc:
        message = extract_validation_error_message(
            exc,
            fallback_message='Dados inválidos para configuração do cliente MCP',
        )
        return jsonify({"success": False, "message": message}), 400
    except Exception as exc:
        return log_and_build_public_error_response(
            logger,
            exc,
            context='Falha ao montar configuração MCP do usuário autenticado',
            success=False,
        )

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('active_company_id', None)
    return redirect(url_for('auth.login'))
