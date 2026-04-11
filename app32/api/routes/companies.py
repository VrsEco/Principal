from flask import Blueprint, render_template, request, jsonify
from models import db, Company, Employee, User, Role, CompanyPerformanceSettings
from services.user_employee_service import UserEmployeeService
from services.company_onboarding_service import CompanyOnboardingService
from utils.permissions import can_access_company, is_platform_admin, permission_required
from flask_login import login_required, current_user
from utils.logo_processor import resize_and_save_logo, get_logo_url

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."

companies_bp = Blueprint('companies', __name__)

@companies_bp.route('/companies')
@permission_required('companies', 'view')
def companies_list():
    """Companies list page"""
    return render_template('modules/companies/companies_v2.html')

@companies_bp.route('/companies/new')
@permission_required('companies', 'create')
def company_new():
    """New company form"""
    tab = request.args.get('tab', 'dados')
    onboarding = CompanyOnboardingService.build_view_model(None, tab)
    return render_template('modules/companies/company_form_v2.html', active_tab=tab, onboarding=onboarding)

@companies_bp.route('/companies/<int:company_id>/edit')
@permission_required('companies', 'edit')
def company_edit(company_id):
    """Edit company form with tab support"""
    tab = request.args.get('tab', 'dados')
    onboarding = CompanyOnboardingService.build_view_model(company_id, tab)
    return render_template('modules/companies/company_form_v2.html', company_id=company_id, active_tab=tab, onboarding=onboarding)

# Complex nested components logic goes to routes.
# Core CRUD functionality should be exclusively in api/resources/company.py

@companies_bp.route('/api/companies/<int:company_id>/users', methods=['GET'])
@permission_required('companies', 'view')
def get_company_users(company_id):
    # Security check: User must have access to this company
    if not can_access_company(company_id):
        return jsonify({"error": "Acesso negado"}), 403

    # Display all employees that actually have a user_id vinculated, including inactive ones
    employees = Employee.query.filter(Employee.company_id==company_id, Employee.user_id.isnot(None)).all()
    # Enriquecer com dados do User se existir
    result = []
    for emp in employees:
        emp_dict = emp.to_dict()
        user = User.query.get(emp.user_id)
        if user:
            emp_dict['user_email'] = user.email
            emp_dict['user_role'] = user.role
            result.append(emp_dict)
    
    return jsonify(result)

@companies_bp.route('/api/companies/<int:company_id>/users', methods=['POST'])
@permission_required('companies', 'edit')
def add_company_user(company_id):
    data = request.json
    email = data.get('email')
    name = data.get('name')
    password = data.get('password', '123456') # Default password if not provided
    role = data.get('role', 'collaborator')
    
    if not email or not name:
        return jsonify({"error": "Nome e Email são obrigatórios"}), 400
        
    # Check if user already exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create user
        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
    
    # Check if already employee of this company
    existing_emp = Employee.query.filter_by(user_id=user.id, company_id=company_id).first()
    if existing_emp:
        return jsonify({"error": "Usuário já vinculado a esta empresa"}), 400
        
    # Attempt to find an existing "Colaborador" (Employee) without a user_id 
    # matching the provided email or name
    employee_to_link = Employee.query.filter_by(company_id=company_id, email=email).filter(Employee.user_id.is_(None)).first()
    
    if not employee_to_link:
        employee_to_link = Employee.query.filter(
            Employee.company_id == company_id,
            db.func.lower(Employee.name) == db.func.lower(name),
            Employee.user_id.is_(None)
        ).first()

    if employee_to_link:
        employee_to_link.user_id = user.id
        employee_to_link.email = email
        employee = employee_to_link
    else:
        # Create employment link
        employee = Employee(
            user_id=user.id,
            company_id=company_id,
            name=name,
            email=email,
            status='active'
        )
        db.session.add(employee)
        
    db.session.commit()
    
    return jsonify(employee.to_dict()), 201

@companies_bp.route('/api/companies/<int:company_id>/roles', methods=['GET'])
@permission_required('companies', 'view')
def get_company_roles(company_id):
    roles = Role.query.filter_by(company_id=company_id).all()
    return jsonify([r.to_dict() for r in roles])

@companies_bp.route('/api/companies/<int:company_id>/roles', methods=['POST'])
@permission_required('companies', 'edit')
def add_company_role(company_id):
    try:
        data = request.json
        role = Role(company_id=company_id, **data)
        db.session.add(role)
        db.session.commit()
        return jsonify(role.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500

@companies_bp.route('/api/companies/<int:company_id>/roles/<int:role_id>', methods=['PUT', 'GET'])
@permission_required('companies', 'edit')
def update_company_role(company_id, role_id):
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    if request.method == 'GET':
        return jsonify(role.to_dict())
    
    data = request.json
    for key, value in data.items():
        if hasattr(role, key) and key not in ['id', 'company_id']:
            setattr(role, key, value)
    db.session.commit()
    return jsonify(role.to_dict())

@companies_bp.route('/api/companies/<int:company_id>/roles/<int:role_id>', methods=['DELETE'])
@permission_required('companies', 'edit')
def delete_company_role(company_id, role_id):
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    db.session.delete(role)
    db.session.commit()
    return jsonify({"success": True})

@companies_bp.route('/api/companies/<int:company_id>/performance-settings', methods=['GET'])
@permission_required('companies', 'view')
def get_performance_settings(company_id):
    settings = CompanyPerformanceSettings.query.filter_by(company_id=company_id).first()
    if not settings:
        # Create default if not exists
        settings = CompanyPerformanceSettings(company_id=company_id)
        db.session.add(settings)
        db.session.commit()
    return jsonify(settings.to_dict())

@companies_bp.route('/api/companies/<int:company_id>/performance-settings', methods=['PUT'])
@permission_required('companies', 'edit')
def update_performance_settings(company_id):
    settings = CompanyPerformanceSettings.query.filter_by(company_id=company_id).first()
    if not settings:
        settings = CompanyPerformanceSettings(company_id=company_id)
        db.session.add(settings)
    
    data = request.json
    boolean_fields = {'allow_postpone_after_due_date'}
    for key, value in data.items():
        if hasattr(settings, key):
            if key in boolean_fields:
                if isinstance(value, str):
                    value = value.strip().lower() in {'1', 'true', 'sim', 'yes', 'on'}
                else:
                    value = bool(value)
            setattr(settings, key, value)
    db.session.commit()
    return jsonify(settings.to_dict())

@companies_bp.route('/api/companies/<int:company_id>/employees/full', methods=['GET'])
@permission_required('companies', 'view')
def get_company_employees_full(company_id):
    from sqlalchemy.orm import joinedload
    employees = Employee.query.options(joinedload(Employee.role)).filter_by(company_id=company_id).all()
    return jsonify([e.to_dict() for e in employees])

@companies_bp.route('/api/companies/<int:company_id>/employees', methods=['POST'])
@permission_required('companies', 'edit')
def add_company_employee(company_id):
    try:
        data = request.json
        employee = Employee(company_id=company_id, **data)
        db.session.add(employee)
        db.session.commit()
        return jsonify(employee.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500

@companies_bp.route('/api/system-users', methods=['GET'])
@permission_required('companies', 'view')
def get_system_users():
    # Retorna usuários ativos do sistema para vínculo
    users = User.query.filter_by(is_active=True).all()
    # Adicionando tratamento caso a model User não possua to_dict ou similares
    result = []
    for u in users:
        result.append({
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role
        })
    return jsonify(result)

@companies_bp.route('/api/companies/<int:company_id>/unlinked-employees', methods=['GET'])
@permission_required('companies', 'view')
def get_unlinked_employees(company_id):
    # Retorna colaboradores da unidade que não possuem user_id vinculado e estão ativos
    employees = Employee.query.filter_by(company_id=company_id, user_id=None, status='active').all()
    return jsonify([e.to_dict() for e in employees])

@companies_bp.route('/api/companies/<int:company_id>/link-user', methods=['POST'])
@permission_required('companies', 'edit')
def link_company_user(company_id):
    data = request.json
    user_id = data.get('user_id')
    employee_id = data.get('employee_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not user_id or not employee_id:
        return jsonify({"error": "Usuário e Colaborador são obrigatórios"}), 400
        
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if not employee:
        return jsonify({"error": "Colaborador não encontrado"}), 404
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário do sistema não encontrado"}), 404
        
    # Verifica se este colaborador já possui um usuário (bloqueia apenas se for um usuário DIFERENTE)
    if employee.user_id and employee.user_id != user.id:
        return jsonify({"error": f"O colaborador selecionado já possui outro usuário vinculado (ID: {employee.user_id})"}), 400
        
    # Verifica se este usuário já está vinculado a outro colaborador nesta empresa
    existing_emp = Employee.query.filter_by(user_id=user.id, company_id=company_id).first()
    if existing_emp and existing_emp.id != employee.id:
        return jsonify({"error": "Este usuário já está vinculado a outro colaborador nesta empresa"}), 400
        
    # Realiza o vínculo através do serviço que gerencia períodos
    result = UserEmployeeService.assign_user_to_employee(
        user_id=user.id, 
        employee_id=employee.id, 
        start_date=start_date, 
        end_date=end_date
    )
    
    if not result['success']:
        return jsonify({"error": result['error']}), 400
    
    if not employee.email and user.email:
        employee.email = user.email
    db.session.commit()
    
    return jsonify({"success": True}), 200

@companies_bp.route('/api/companies/<int:company_id>/employees/<int:employee_id>', methods=['GET', 'PUT'])
@permission_required('companies', 'edit')
def update_company_employee(company_id, employee_id):
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first_or_404()
    if request.method == 'GET':
        return jsonify(employee.to_dict())
    
    data = request.json
    for key, value in data.items():
        if hasattr(employee, key) and key not in ['id', 'company_id', 'user_id']:
            setattr(employee, key, value)
    db.session.commit()
    return jsonify(employee.to_dict())

@companies_bp.route('/api/companies/<int:company_id>/employees/<int:employee_id>/access', methods=['DELETE'])
@permission_required('companies', 'edit')
def remove_company_user_access(company_id, employee_id):
    from models.user_employee_assignment import UserEmployeeAssignment
    from datetime import date
    
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first_or_404()
    
    if not employee.user_id:
        return jsonify({"error": "Colaborador não possui um usuário vinculado"}), 400
        
    assignment = UserEmployeeAssignment.query.filter_by(
        employee_id=employee_id, 
        user_id=employee.user_id, 
        is_active=True
    ).first()
    
    end_date = request.json.get('end_date') if request.is_json else date.today().isoformat()
    
    if assignment:
        result = UserEmployeeService.terminate_assignment(assignment.id, end_date=end_date)
        if not result['success']:
            return jsonify({"error": result['error']}), 400
    else:
        # Fallback se não existir assignment
        employee.user_id = None
        db.session.commit()
        
    return jsonify({"success": True})

@companies_bp.route('/api/companies/<int:company_id>/employees/<int:employee_id>', methods=['DELETE'])
@permission_required('companies', 'edit')
def delete_company_employee(company_id, employee_id):
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first_or_404()
    # Soft delete do histórico/função do colaborador em si
    employee.status = 'inactive'
    db.session.commit()
    return jsonify({"success": True})

@companies_bp.route('/api/companies/<int:company_id>/logo', methods=['POST'])
@permission_required('companies', 'edit')
def upload_company_logo(company_id):
    if 'logo' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    company = Company.query.get_or_404(company_id)
    
    try:
        # Usamos o 'horizontal' como padrão para relatórios
        logo_path = resize_and_save_logo(file, company_id, 'horizontal')
        
        # O logo_processor retorna o path relativo a partir de 'uploads/'
        # mas para o template, precisamos que comece com /uploads/
        full_path = f"/uploads/{logo_path}"
        
        company.logo_primary = full_path
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "logo_url": full_path
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500
