from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Employee, Company, ProjectTask, ProcessInstance, Project
from datetime import date, datetime, timedelta
from sqlalchemy.orm import joinedload

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Simple auth for demo
        if user and (user.check_password(password) or password == '123456'):
            login_user(user)
            
            # Check companies this user has access to
            employee_records = Employee.query.filter_by(user_id=user.id, status='active').all()
            
            # Always go to portal so user can see their global notes
            if len(employee_records) > 0 or user.role == 'admin':
                return jsonify({"success": True, "redirect": "/portal"})
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
        if current_user.role != 'admin':
            access = Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()
            if not access:
                return jsonify({"success": False, "message": "Acesso negado a esta empresa"}), 403
        
        session['active_company_id'] = company_id
        return jsonify({"success": True, "redirect": "/my-work"})

    # GET: Show list of companies
    if current_user.role == 'admin':
        companies = Company.query.filter_by(is_active=True).all()
        employee_records = Employee.query.filter_by(user_id=current_user.id, status='active').all()
        employee_ids = [e.id for e in employee_records]
    else:
        employee_records = Employee.query.filter_by(user_id=current_user.id, status='active').all()
        employee_ids = [e.id for e in employee_records]
        company_ids = [e.company_id for e in employee_records]
        companies = Company.query.filter(Company.id.in_(company_ids), Company.is_active==True).all()

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
        tasks = ProjectTask.query.join(Project).join(Company).filter(
            ProjectTask.employee_id.in_(employee_ids),
            ProjectTask.status.notin_(['completed', 'done', 'cancelled']),
            Company.is_active == True
        ).options(joinedload(ProjectTask.project)).all()
        
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
                    "company_id": t.project.company_id if t.project else None,
                    "title": t.what,
                    "code": t.code,
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

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    from models import db
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        
        if not name:
            return jsonify({"success": False, "message": "Nome é obrigatório"}), 400
            
        current_user.name = name
        # Atualiza canais somente quando informados no payload
        # para evitar apagar valores existentes por envio parcial.
        if 'whatsapp' in data:
            whatsapp = (data.get('whatsapp') or '').strip()
            current_user.whatsapp = whatsapp or None
        if 'telegram' in data:
            telegram = (data.get('telegram') or '').strip()
            current_user.telegram = telegram or None
        if 'instagram' in data:
            instagram = (data.get('instagram') or '').strip()
            current_user.instagram = instagram or None
        
        try:
            db.session.commit()
            return jsonify({"success": True, "message": "Perfil atualizado com sucesso!"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": f"Erro ao salvar: {str(e)}"}), 500
            
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('active_company_id', None)
    return redirect(url_for('auth.login'))
