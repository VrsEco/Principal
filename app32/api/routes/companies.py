from flask import Blueprint, render_template, request, jsonify
from models import (
    db,
    Company,
    Employee,
    User,
    Role,
    CompanyPerformanceSettings,
)
from services.user_employee_service import UserEmployeeService
from services.identity.user_employee_orchestrator_service import (
    UserEmployeeOrchestratorService,
)
from services.company_onboarding_service import CompanyOnboardingService
from services.company_identity_service import CompanyIdentityService
from services.company_role_hierarchy_service import (
    CompanyRoleHierarchyService,
    RoleHierarchyValidationError,
)
from services.company_role_permission_preset_service import (
    CompanyRolePermissionPresetService,
)
from services.rbac_permission_catalog_service import RbacPermissionCatalogService
from utils.permissions import can_access_company, is_platform_admin, permission_required
from flask_login import login_required, current_user
from utils.logo_processor import resize_and_save_logo, get_logo_url

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."

companies_bp = Blueprint('companies', __name__)


def _ensure_company_access(company_id):
    if not can_access_company(company_id):
        return jsonify({"error": "Acesso negado"}), 403
    return None

@companies_bp.route('/companies')
@permission_required('companies', 'view')
def companies_list():
    """Companies list page"""
    return render_template('modules/companies/companies_v2.html')

@companies_bp.route('/companies/new')
@permission_required('companies', 'create')
def company_new():
    """Novo onboarding assistido de empresa."""
    return render_template(
        'cadastro_agent.html',
        agent_type='cadastro',
        agent_name='Onboarding Assistido de Empresa',
        agent_description='Criação guiada da empresa com contexto operacional, estratégico e readiness para IA/MCP.',
        canonical_company_route='/companies/new',
    )

@companies_bp.route('/companies/<int:company_id>/edit')
@permission_required('companies', 'edit')
def company_edit(company_id):
    """Edit company form with tab support"""
    tab = request.args.get('tab', 'dados')
    onboarding = CompanyOnboardingService.build_view_model(company_id, tab)
    return render_template('modules/companies/company_form_v2.html', company_id=company_id, active_tab=tab, onboarding=onboarding)


@companies_bp.route('/companies/<int:company_id>/identity')
@permission_required('companies', 'view')
def company_identity(company_id):
    """Hub consolidado da identidade organizacional."""
    denied = _ensure_company_access(company_id)
    if denied:
        return denied

    summary = CompanyIdentityService.build_summary(company_id)
    return render_template(
        'modules/companies/company_identity_v2.html',
        company=summary.company,
        metrics=summary.metrics,
    )

# Complex nested components logic goes to routes.
# Core CRUD functionality should be exclusively in api/resources/company.py

@companies_bp.route('/api/companies/<int:company_id>/users', methods=['GET'])
@permission_required('companies', 'view')
def get_company_users(company_id):
    # Security check: User must have access to this company
    denied = _ensure_company_access(company_id)
    if denied:
        return denied

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
        
    result = UserEmployeeOrchestratorService.register_or_link_user_employee(
        company_id=company_id,
        create_system_access=True,
        user_payload={
            'name': name,
            'email': email,
            'password': password,
            'role': role,
            'whatsapp': data.get('whatsapp'),
            'telegram': data.get('telegram'),
            'instagram': data.get('instagram'),
        },
        employee_payload={
            'name': name,
            'email': email,
            'phone': data.get('phone'),
            'whatsapp': data.get('whatsapp'),
            'department': data.get('department'),
            'role_id': data.get('role_id'),
            'notes': data.get('notes'),
        },
    )
    if not result.get('success'):
        return jsonify({"error": result['error']}), 400
    status_code = 200 if result.get('action') == 'already_linked' else 201
    return jsonify(result['employee']), status_code

@companies_bp.route('/api/companies/<int:company_id>/roles', methods=['GET'])
@permission_required('companies', 'view')
def get_company_roles(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    roles = Role.query.filter_by(company_id=company_id).all()
    return jsonify([RbacPermissionCatalogService.serialize_role(r) for r in roles])


@companies_bp.route('/api/companies/<int:company_id>/roles/tree', methods=['GET'])
@permission_required('companies', 'view')
def get_company_roles_tree(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    return jsonify({"success": True, "data": CompanyIdentityService.build_roles_tree(company_id)})


@companies_bp.route('/api/companies/<int:company_id>/identity/summary', methods=['GET'])
@permission_required('companies', 'view')
def get_company_identity_summary(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    summary = CompanyIdentityService.build_summary(company_id)
    return jsonify(
        {
            "success": True,
            "company": summary.company,
            "metrics": {
                **summary.metrics,
                "org_chart_created_at": summary.metrics["org_chart_created_at"].isoformat()
                if summary.metrics.get("org_chart_created_at")
                else None,
                "org_chart_updated_at": summary.metrics["org_chart_updated_at"].isoformat()
                if summary.metrics.get("org_chart_updated_at")
                else None,
            },
            "roles": summary.roles,
            "employees": summary.employees,
        }
    )


@companies_bp.route('/api/companies/<int:company_id>/permission-catalog', methods=['GET'])
@permission_required('companies', 'view')
def get_company_permission_catalog(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    company_presets = CompanyRolePermissionPresetService.list_presets(company_id)
    return jsonify(
        RbacPermissionCatalogService.get_catalog(company_presets=company_presets)
    )


@companies_bp.route('/api/companies/<int:company_id>/role-permission-presets', methods=['GET'])
@permission_required('companies', 'view')
def list_company_role_permission_presets(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    return jsonify(CompanyRolePermissionPresetService.list_presets(company_id))


@companies_bp.route('/api/companies/<int:company_id>/role-permission-presets', methods=['POST'])
@permission_required('companies', 'edit')
def create_company_role_permission_preset(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    try:
        payload = CompanyRolePermissionPresetService.create_preset(
            company_id,
            request.json or {},
            created_by_user_id=getattr(current_user, "id", None),
        )
        return jsonify(payload), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500


@companies_bp.route('/api/companies/<int:company_id>/role-permission-presets/<int:preset_id>', methods=['GET'])
@permission_required('companies', 'view')
def get_company_role_permission_preset(company_id, preset_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    preset = CompanyRolePermissionPresetService.get_preset(company_id, preset_id)
    if not preset:
        return jsonify({"error": "Preset não encontrado"}), 404
    return jsonify(CompanyRolePermissionPresetService.serialize_preset(preset))


@companies_bp.route('/api/companies/<int:company_id>/role-permission-presets/<int:preset_id>', methods=['PUT'])
@permission_required('companies', 'edit')
def update_company_role_permission_preset(company_id, preset_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    preset = CompanyRolePermissionPresetService.get_preset(company_id, preset_id)
    if not preset:
        return jsonify({"error": "Preset não encontrado"}), 404
    try:
        payload = CompanyRolePermissionPresetService.update_preset(
            preset,
            request.json or {},
        )
        return jsonify(payload)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500


@companies_bp.route('/api/companies/<int:company_id>/role-permission-presets/<int:preset_id>', methods=['DELETE'])
@permission_required('companies', 'edit')
def delete_company_role_permission_preset(company_id, preset_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    preset = CompanyRolePermissionPresetService.get_preset(company_id, preset_id)
    if not preset:
        return jsonify({"error": "Preset não encontrado"}), 404
    try:
        CompanyRolePermissionPresetService.delete_preset(preset)
        return jsonify({"success": True})
    except Exception:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500

@companies_bp.route('/api/companies/<int:company_id>/roles', methods=['POST'])
@permission_required('companies', 'edit')
def add_company_role(company_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    try:
        role = CompanyRoleHierarchyService.create(company_id, request.get_json(silent=True))
        return jsonify(RbacPermissionCatalogService.serialize_role(role, include_tree=True)), 201
    except RoleHierarchyValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500

@companies_bp.route('/api/companies/<int:company_id>/roles/<int:role_id>', methods=['PUT', 'GET'])
@permission_required('companies', 'edit')
def update_company_role(company_id, role_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    if request.method == 'GET':
        role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
        return jsonify(RbacPermissionCatalogService.serialize_role(role, include_tree=True))
    
    try:
        role = CompanyRoleHierarchyService.update(company_id, role_id, request.get_json(silent=True))
        return jsonify(RbacPermissionCatalogService.serialize_role(role, include_tree=True))
    except RoleHierarchyValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500

@companies_bp.route('/api/companies/<int:company_id>/roles/<int:role_id>', methods=['DELETE'])
@permission_required('companies', 'edit')
def delete_company_role(company_id, role_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
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
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
    from sqlalchemy.orm import joinedload
    employees = Employee.query.options(joinedload(Employee.role)).filter_by(company_id=company_id).all()
    return jsonify([e.to_dict() for e in employees])

@companies_bp.route('/api/companies/<int:company_id>/employees', methods=['POST'])
@permission_required('companies', 'edit')
def add_company_employee(company_id):
    try:
        data = request.json
        user_id = data.get('user_id')
        if user_id:
            result = UserEmployeeOrchestratorService.register_or_link_user_employee(
                company_id=company_id,
                existing_user_id=int(user_id),
                create_system_access=True,
                employee_payload=data,
                employee_id=data.get('employee_id'),
            )
        else:
            result = UserEmployeeOrchestratorService.register_or_link_user_employee(
                company_id=company_id,
                employee_payload=data,
                create_system_access=False,
                employee_id=data.get('employee_id'),
            )
        if not result.get('success'):
            return jsonify({"error": result['error']}), 400
        return jsonify(result['employee']), 201
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
        
    result = UserEmployeeOrchestratorService.link_existing_user_to_employee(
        company_id=company_id,
        user_id=user.id,
        employee_id=employee.id,
        start_date=start_date,
        end_date=end_date,
    )
    
    if not result['success']:
        return jsonify({"error": result['error']}), 400
    
    return jsonify({"success": True, "assignment": result.get("assignment")}), 200

@companies_bp.route('/api/companies/<int:company_id>/employees/<int:employee_id>', methods=['GET', 'PUT'])
@permission_required('companies', 'edit')
def update_company_employee(company_id, employee_id):
    denied = _ensure_company_access(company_id)
    if denied:
        return denied
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
