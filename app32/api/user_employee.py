"""
API Blueprint para gerenciamento de Usuários e Colaboradores
Implementa endpoints para criar e gerenciar a relação User-Employee-Company
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.user_employee_service import UserEmployeeService
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from utils.permissions import admin_required, can_access_company, is_platform_admin

user_employee_bp = Blueprint('user_employee', __name__, url_prefix='/api/user-employee')
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


@user_employee_bp.route('/register', methods=['POST'])
def register_user_with_company():
    """
    Cadastro de novo usuário com empresa
    
    POST /api/user-employee/register
    {
        "user": {
            "name": "João Silva",
            "email": "joao@empresa.com",
            "password": "senha123"
        },
        "company": {
            "name": "Tech Solutions Ltda",
            "cnpj": "00.000.000/0001-00",
            "segment": "Tecnologia"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'user' not in data or 'company' not in data:
            return jsonify({
                'success': False,
                'error': 'Dados incompletos. Envie user e company.'
            }), 400
        
        # Verificar se email já existe
        existing_user = User.query.filter_by(email=data['user']['email']).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'Email já cadastrado no sistema'
            }), 400
        
        # Criar usuário, empresa e vínculo
        result = UserEmployeeService.create_user_with_company(
            user_data=data['user'],
            company_data=data['company'],
            employee_data=data.get('employee')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/add-to-company', methods=['POST'])
@login_required
@admin_required
def add_user_to_company():
    """
    Adiciona um usuário existente como colaborador de uma empresa
    
    POST /api/user-employee/add-to-company
    {
        "user_id": 5,
        "company_id": 10,
        "role_id": 2
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'company_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Dados incompletos. Envie user_id e company_id.'
            }), 400
        
        # Apenas admins podem adicionar usuários a empresas
        if not is_platform_admin():
            return jsonify({
                'success': False,
                'error': 'Apenas administradores podem executar esta ação'
            }), 403
        
        result = UserEmployeeService.add_employee_to_company(
            user_id=data['user_id'],
            company_id=data['company_id'],
            role_id=data.get('role_id'),
            employee_data=data.get('employee_data')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/my-companies', methods=['GET'])
@login_required
def get_my_companies():
    """
    Lista todas as empresas que o usuário logado tem acesso
    
    GET /api/user-employee/my-companies
    """
    try:
        companies = UserEmployeeService.get_user_companies(current_user.id)
        
        return jsonify({
            'success': True,
            'companies': companies,
            'count': len(companies)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/my-activities', methods=['GET'])
@login_required
def get_my_activities():
    """
    Lista todas as atividades do usuário logado em todas as empresas
    
    GET /api/user-employee/my-activities
    """
    try:
        activities = UserEmployeeService.get_user_activities(current_user.id)
        
        return jsonify({
            'success': True,
            'activities': activities,
            'count': len(activities)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/employees/<int:company_id>', methods=['GET'])
@login_required
def get_company_employees(company_id):
    """
    Lista todos os colaboradores de uma empresa
    
    GET /api/user-employee/employees/10
    """
    try:
        # Verificar se o usuário tem acesso a esta empresa
        user_employee = Employee.query.filter_by(
            user_id=current_user.id,
            company_id=company_id
        ).first()
        
        if not user_employee and not is_platform_admin():
            return jsonify({
                'success': False,
                'error': 'Você não tem acesso a esta empresa'
            }), 403
        
        employees = Employee.query.filter_by(company_id=company_id).all()
        
        return jsonify({
            'success': True,
            'employees': [emp.to_dict() for emp in employees],
            'count': len(employees)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/employee/<int:employee_id>', methods=['PUT'])
@login_required
def update_employee(employee_id):
    """
    Atualiza dados de um colaborador
    
    PUT /api/user-employee/employee/5
    {
        "phone": "(11) 98765-4321",
        "department": "TI",
        "status": "active",
        "user_id": 10  # Para vincular a um usuário
    }
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Colaborador não encontrado'
            }), 404
        
        # Verificar permissão
        if not is_platform_admin() and employee.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Você não tem permissão para editar este colaborador'
            }), 403
        
        data = request.get_json()
        
        # Atualizar campos permitidos
        allowed_fields = ['phone', 'whatsapp', 'department', 'status', 'weekly_hours', 'notes']
        for field in allowed_fields:
            if field in data:
                setattr(employee, field, data[field])
        
        # Vincular a usuário se fornecido
        if 'user_id' in data and data['user_id']:
            user_id = int(data['user_id'])
            # Verificar se usuário existe
            user = User.query.get(user_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Usuário não encontrado'
                }), 404
            
            # Verificar se já existe outro employee com este user_id nesta empresa
            existing = Employee.query.filter_by(
                user_id=user_id,
                company_id=employee.company_id
            ).filter(Employee.id != employee_id).first()
            
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Este usuário já está vinculado a outro colaborador nesta empresa'
                }), 400
            
            employee.user_id = user_id
            # Atualizar email e nome se não estiverem preenchidos
            if not employee.email and user.email:
                employee.email = user.email
            if not employee.name or employee.name == '':
                employee.name = user.name
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'employee': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500


@user_employee_bp.route('/employee/<int:employee_id>/link-user', methods=['POST'])
@login_required
@admin_required
def link_employee_to_user(employee_id):
    """
    Vincula um colaborador a um usuário do sistema
    
    POST /api/user-employee/employee/5/link-user
    {
        "user_id": 10
    }
    """
    try:
        # Apenas admins podem vincular
        if not is_platform_admin():
            return jsonify({
                'success': False,
                'error': 'Apenas administradores podem executar esta ação'
            }), 403
        
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Colaborador não encontrado'
            }), 404
        
        data = request.get_json()
        
        if 'user_id' not in data or not data['user_id']:
            return jsonify({
                'success': False,
                'error': 'user_id é obrigatório'
            }), 400
        
        user_id = int(data['user_id'])
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuário não encontrado'
            }), 404
        
        # Verificar se já existe outro employee com este user_id nesta empresa
        existing = Employee.query.filter_by(
            user_id=user_id,
            company_id=employee.company_id
        ).filter(Employee.id != employee_id).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Este usuário já está vinculado a outro colaborador nesta empresa'
            }), 400
        
        # Vincular
        employee.user_id = user_id
        # Atualizar email e nome se não estiverem preenchidos
        if not employee.email and user.email:
            employee.email = user.email
        if not employee.name or employee.name == '':
            employee.name = user.name
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Colaborador vinculado ao usuário com sucesso',
            'employee': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': PUBLIC_ERROR_MESSAGE
        }), 500
