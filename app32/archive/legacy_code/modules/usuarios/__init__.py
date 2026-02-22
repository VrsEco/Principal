"""
Blueprint para Gerenciamento de Usuários
Interface web para cadastrar, editar e vincular usuários
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.role import Role
from services.user_employee_service import UserEmployeeService

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


@usuarios_bp.route('/')
@login_required
def index():
    """Página principal de gerenciamento de usuários"""
    # Apenas admins podem acessar
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('pev.pev_dashboard'))
    
    # Buscar todos os usuários
    users = User.query.all()
    
    # Buscar todas as empresas
    companies = Company.query.all()
    
    return render_template('usuarios/index.html',
                         users=users,
                         companies=companies,
                         active_nav='usuarios')


@usuarios_bp.route('/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar():
    """Cadastrar novo usuário com empresa"""
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios.index'))
    
    if request.method == 'POST':
        data = request.json
        
        result = UserEmployeeService.create_user_with_company(
            user_data=data.get('user', {}),
            company_data=data.get('company', {}),
            employee_data=data.get('employee', {})
        )
        
        return jsonify(result)
    
    # GET - Mostrar formulário
    companies = Company.query.all()
    return render_template('usuarios/cadastrar.html',
                         companies=companies,
                         active_nav='usuarios')


@usuarios_bp.route('/vincular', methods=['GET', 'POST'])
@login_required
def vincular():
    """Vincular usuário existente a empresa"""
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios.index'))
    
    if request.method == 'POST':
        data = request.json
        
        result = UserEmployeeService.add_employee_to_company(
            user_id=data.get('user_id'),
            company_id=data.get('company_id'),
            role_id=data.get('role_id'),
            employee_data=data.get('employee_data', {})
        )
        
        return jsonify(result)
    
    # GET - Mostrar formulário
    users = User.query.all()
    companies = Company.query.all()
    return render_template('usuarios/vincular.html',
                         users=users,
                         companies=companies,
                         active_nav='usuarios')


@usuarios_bp.route('/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar(user_id):
    """Editar usuário e suas permissões"""
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios.index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        data = request.json
        
        # Atualizar dados do usuário
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({'success': True, 'user': user.to_dict()})
    
    # GET - Mostrar formulário
    employees = Employee.query.filter_by(user_id=user_id).all()
    
    # Buscar empresas e roles de cada employee
    employee_data = []
    for emp in employees:
        company = Company.query.get(emp.company_id)
        role = Role.query.get(emp.role_id) if emp.role_id else None
        employee_data.append({
            'employee': emp,
            'company': company,
            'role': role
        })
    
    return render_template('usuarios/editar.html',
                         user=user,
                         employee_data=employee_data,
                         active_nav='usuarios')


@usuarios_bp.route('/permissoes/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def permissoes(employee_id):
    """Editar permissões de um colaborador"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        data = request.json
        
        # Buscar ou criar role
        if employee.role_id:
            role = Role.query.get(employee.role_id)
        else:
            role = Role(
                company_id=employee.company_id,
                title=data.get('role_title', 'Colaborador')
            )
            db.session.add(role)
            db.session.flush()
            employee.role_id = role.id
        
        # Atualizar permissões
        role.permissions = data.get('permissions', {})
        db.session.commit()
        
        return jsonify({'success': True, 'role': role.to_dict()})
    
    # GET - Retornar permissões atuais
    role = Role.query.get(employee.role_id) if employee.role_id else None
    return jsonify({
        'success': True,
        'employee': employee.to_dict(),
        'role': role.to_dict() if role else None
    })


@usuarios_bp.route('/api/list')
@login_required
def api_list():
    """API para listar usuários"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    users = User.query.all()
    
    users_data = []
    for user in users:
        employees = Employee.query.filter_by(user_id=user.id).all()
        companies = [Company.query.get(emp.company_id).name for emp in employees]
        
        users_data.append({
            **user.to_dict(),
            'companies': companies,
            'companies_count': len(companies)
        })
    
    return jsonify({'success': True, 'users': users_data})


@usuarios_bp.route('/api/delete/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete(user_id):
    """API para deletar usuário"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Deletar employees vinculados
    Employee.query.filter_by(user_id=user_id).delete()
    
    # Deletar usuário
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Usuário deletado com sucesso'})
