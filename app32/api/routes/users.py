from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Employee, Company, db
from schemas.user_pydantic import UserCreateSchema, UserUpdateSchema
from pydantic import ValidationError
from utils.permissions import admin_required

usuarios_bp = Blueprint('usuarios', __name__)

def _serialize_summary_channels(channels):
    if channels is None:
        return 'telegram'
    if isinstance(channels, str):
        items = [item.strip().lower() for item in channels.split(',')]
    else:
        items = [str(item).strip().lower() for item in channels]
    normalized = []
    for item in items:
        if item in {'telegram', 'whatsapp', 'email'} and item not in normalized:
            normalized.append(item)
    return ','.join(normalized) if normalized else 'telegram'


def _summary_channels_list(raw_value):
    return [item for item in _serialize_summary_channels(raw_value).split(',') if item]

@usuarios_bp.route('/usuarios')
@login_required
def index():
    """Render user management page"""
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('my_work.my_work'))
    
    users = User.query.all()
    employees = Employee.query.all()
    companies = Company.query.all()
    summary_channel_labels = {
        'telegram': 'Telegram',
        'whatsapp': 'WhatsApp',
        'email': 'E-mail',
    }
    user_summary_channels = {
        user.id: _summary_channels_list(getattr(user, 'summary_delivery_channels', None))
        for user in users
    }
    
    return render_template(
        'usuarios/index.html',
        users=users,
        employees=employees,
        companies=companies,
        user_summary_channels=user_summary_channels,
        summary_channel_labels=summary_channel_labels,
    )

@usuarios_bp.route('/usuarios/cadastrar')
@login_required
@admin_required
def cadastrar():
    """Render user registration page"""
    companies = Company.query.all()
    return render_template('usuarios/cadastrar.html', companies=companies)

@usuarios_bp.route('/usuarios/editar/<int:user_id>')
@login_required
@admin_required
def editar(user_id):
    """Render user edit page"""
    user = User.query.get_or_404(user_id)
    companies = Company.query.all()
    user_companies = []
    
    # Get user employee records
    from models.employee import Employee
    employees = Employee.query.filter_by(user_id=user_id).all()
    
    # Get the company objects directly in python instead of querying all
    company_dict = {c.id: c for c in companies}
    for emp in employees:
        if emp.company_id in company_dict:
            user_companies.append({
                "employee_id": emp.id,
                "company_name": company_dict[emp.company_id].name,
                "department": emp.department,
                "status": emp.status
            })
            
    return render_template('usuarios/editar.html', user=user, companies=companies, user_companies=user_companies)

@usuarios_bp.route('/usuarios/vincular')
@login_required
@admin_required
def vincular():
    """Render user-company linking page"""
    users = User.query.all()
    companies = Company.query.all()
    return render_template('usuarios/vincular.html', users=users, companies=companies)

@usuarios_bp.route('/api/usuarios', methods=['GET'])
@login_required
def get_users():
    """API to list users"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@usuarios_bp.route('/api/usuarios', methods=['POST'])
@login_required
def create_user():
    """API to create a user with Pydantic validation"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        validated_data = UserCreateSchema(**data)
        company_ids = validated_data.company_ids or []

        if company_ids:
            active_company_ids = {company.id for company in Company.query.filter(Company.id.in_(company_ids), Company.is_active == True).all()}
            invalid_company_ids = [company_id for company_id in company_ids if company_id not in active_company_ids]
            if invalid_company_ids:
                return jsonify({"success": False, "message": f"Empresas inválidas ou inativas: {invalid_company_ids}"}), 400
        
        # Check if email exists
        if User.query.filter_by(email=validated_data.email).first():
            return jsonify({"success": False, "message": "Email já cadastrado"}), 400
        
        user = User(
            name=validated_data.name,
            email=validated_data.email,
            role=validated_data.role,
            whatsapp=validated_data.whatsapp,
            telegram=validated_data.telegram,
            instagram=validated_data.instagram,
            summary_delivery_channels=_serialize_summary_channels(validated_data.summary_delivery_channels),
        )
        user.set_password(validated_data.password)
        
        db.session.add(user)
        db.session.commit()
        
        # Vincular empresas se houver
        if company_ids:
            from services.user_employee_service import UserEmployeeService
            UserEmployeeService.add_employee_to_multiple_companies(user.id, company_ids)
            recent_employees = Employee.query.filter_by(user_id=user.id).all()
            for emp in recent_employees:
                if emp.company_id in company_ids:
                    UserEmployeeService.assign_user_to_employee(user.id, emp.id)
        
        return jsonify({"success": True, "user": user.to_dict()}), 201
        
    except ValidationError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@usuarios_bp.route('/api/usuarios/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """API to update a user with Pydantic validation"""
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        validated_data = UserUpdateSchema(**data)
        
        if validated_data.name is not None: user.name = validated_data.name
        if validated_data.role is not None and current_user.role == 'admin': user.role = validated_data.role
        if validated_data.whatsapp is not None: user.whatsapp = validated_data.whatsapp
        if validated_data.telegram is not None: user.telegram = validated_data.telegram
        if validated_data.instagram is not None: user.instagram = validated_data.instagram
        if validated_data.summary_delivery_channels is not None:
            user.summary_delivery_channels = _serialize_summary_channels(validated_data.summary_delivery_channels)
        if validated_data.is_active is not None and current_user.role == 'admin': user.is_active = validated_data.is_active
        
        db.session.commit()
        return jsonify({"success": True, "user": user.to_dict()})
        
    except ValidationError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@usuarios_bp.route('/usuarios/api/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_route(user_id):
    """API for soft delete (matching template expectation)"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"success": False, "message": "Não é possível excluir a si mesmo"}), 400
        
    user.is_active = False
    db.session.commit()
    return jsonify({"success": True})
