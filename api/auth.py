"""
Authentication API endpoints
"""

import logging
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from services.auth_service import auth_service
from services.log_service import log_service
from models.user import User
from models import db
from middleware.admin_required import admin_required

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and authentication"""
    if request.method == "GET":
        # If already logged in, redirect to dashboard
        if current_user and current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("auth/login.html")

    elif request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip()
            password = data.get("password", "")

            if not email or not password:
                return (
                    jsonify(
                        {"success": False, "message": "Email e senha são obrigatórios"}
                    ),
                    400,
                )

            # Authenticate user
            user = auth_service.authenticate_user(email, password)

            if user:
                # Login user
                remember = data.get("remember", False)
                auth_service.login_user_session(user, remember=remember)

                return jsonify(
                    {
                        "success": True,
                        "message": "Login realizado com sucesso",
                        "user": user.to_dict(),
                        "redirect": url_for("dashboard"),
                    }
                )
            else:
                return (
                    jsonify({"success": False, "message": "Email ou senha incorretos"}),
                    401,
                )

        except Exception as e:
            return (
                jsonify({"success": False, "message": f"Erro no login: {str(e)}"}),
                500,
            )


@login_required
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logout user"""
    try:
        auth_service.logout_user_session()

        # Se for GET (via navegador), redireciona para login
        if request.method == "GET":
            flash("Logout realizado com sucesso", "success")
            return redirect(url_for("login"))

        # Se for POST (via API), retorna JSON
        return jsonify(
            {
                "success": True,
                "message": "Logout realizado com sucesso",
                "redirect": url_for("login"),
            }
        )

    except Exception as e:
        if request.method == "GET":
            flash(f"Erro no logout: {str(e)}", "error")
            return redirect(url_for("login"))

        return jsonify({"success": False, "message": f"Erro no logout: {str(e)}"}), 500


@login_required
@admin_required
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration (admin only)"""
    if request.method == "GET":
        return render_template("auth/register.html")

    elif request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip()
            password = data.get("password", "")
            name = data.get("name", "").strip()
            role = data.get("role", "consultant").strip()

            if not email or not password or not name:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Email, senha e nome são obrigatórios",
                        }
                    ),
                    400,
                )

            # Create user
            user = auth_service.create_user(email, password, name, role)

            if user:
                return jsonify(
                    {
                        "success": True,
                        "message": "Usuário criado com sucesso",
                        "user": user.to_dict(),
                    }
                )
            else:
                return (
                    jsonify({"success": False, "message": "Email já está em uso"}),
                    400,
                )

        except Exception as e:
            return (
                jsonify(
                    {"success": False, "message": f"Erro ao criar usuário: {str(e)}"}
                ),
                500,
            )


@login_required
@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile management"""
    if request.method == "GET":
        if not current_user or not current_user.is_authenticated:
            return redirect(url_for("login"))
        return render_template("auth/profile.html", user=current_user)

    elif request.method == "POST":
        try:
            if not current_user or not current_user.is_authenticated:
                return jsonify({"success": False, "message": "Não autenticado"}), 401

            data = request.get_json() if request.is_json else request.form

            # Update profile
            name = data.get("name", "").strip()
            role = (
                data.get("role", "").strip()
                if getattr(current_user, "role", None) == "admin"
                else None
            )
            is_active = (
                data.get("is_active")
                if getattr(current_user, "role", None) == "admin"
                else None
            )

            if is_active is not None:
                is_active = is_active.lower() in ["true", "1", "yes", "on"]

            success = auth_service.update_user_profile(
                current_user,
                name=name if name else None,
                role=role if role else None,
                is_active=is_active,
            )

            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": "Perfil atualizado com sucesso",
                        "user": current_user.to_dict(),
                    }
                )
            else:
                return (
                    jsonify({"success": False, "message": "Falha ao atualizar perfil"}),
                    400,
                )

        except Exception as e:
            return (
                jsonify(
                    {"success": False, "message": f"Erro ao atualizar perfil: {str(e)}"}
                ),
                500,
            )


@login_required
@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change user password"""
    try:
        data = request.get_json() if request.is_json else request.form
        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")
        confirm_password = data.get("confirm_password", "")

        if not old_password or not new_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Senha atual e nova senha são obrigatórias",
                    }
                ),
                400,
            )

        if new_password != confirm_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Nova senha e confirmação não coincidem",
                    }
                ),
                400,
            )

        if len(new_password) < 6:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Nova senha deve ter pelo menos 6 caracteres",
                    }
                ),
                400,
            )

        success = auth_service.change_password(current_user, old_password, new_password)

        if success:
            return jsonify({"success": True, "message": "Senha alterada com sucesso"})
        else:
            return jsonify({"success": False, "message": "Senha atual incorreta"}), 400

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Erro ao alterar senha: {str(e)}"}),
            500,
        )


@auth_bp.route("/users/page", methods=["GET"])
@login_required
@admin_required
def list_users_page():
    """User management page (admin only)"""
    return render_template("auth/users.html")


@auth_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    """List all users API with pagination and companies (admin only)"""
    try:
        from models.employee import Employee
        from models.company import Company
        
        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Query com paginação
        pagination = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Buscar empresas vinculadas para cada usuário
        users_data = []
        for user in pagination.items:
            user_dict = user.to_dict()
            
            # Buscar empresas vinculadas através de Employee
            employees = Employee.query.filter_by(user_id=user.id).all()
            companies = []
            for emp in employees:
                try:
                    # Query apenas com colunas que existem
                    company = db.session.query(
                        Company.id,
                        Company.name,
                        Company.legal_name
                    ).filter_by(id=emp.company_id).first()
                    
                    if company:
                        companies.append({
                            'id': company.id,
                            'name': company.name,
                            'legal_name': company.legal_name,
                            'employee_id': emp.id,
                            'status': emp.status
                        })
                except Exception as e:
                    # Se falhar, tentar query apenas com colunas que existem
                    try:
                        company = db.session.query(
                            Company.id, Company.name, Company.legal_name
                        ).filter_by(id=emp.company_id).first()
                        if company:
                            companies.append({
                                'id': company.id,
                                'name': company.name,
                                'legal_name': company.legal_name,
                                'employee_id': emp.id,
                                'status': emp.status
                            })
                    except Exception:
                        # Se ainda falhar, pular esta empresa
                        continue
            
            user_dict['companies'] = companies
            users_data.append(user_dict)

        return jsonify({
            "success": True,
            "users": users_data,
            "pagination": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        })

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao listar usuários: {str(e)}"}
            ),
            500,
        )


@login_required
@auth_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    try:
        data = request.get_json() if request.is_json else request.form
        is_active = data.get("is_active", True)

        if isinstance(is_active, str):
            is_active = is_active.lower() in ["true", "1", "yes", "on"]

        success = auth_service.update_user_status(user_id, is_active)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f'Usuário {"ativado" if is_active else "desativado"} com sucesso',
                }
            )
        else:
            return jsonify({"success": False, "message": "Usuário não encontrado"}), 404

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao atualizar status: {str(e)}"}
            ),
            500,
        )


@auth_bp.route("/current-user", methods=["GET"])
@login_required
def get_current_user():
    """Get current user information"""
    try:
        return jsonify({"success": True, "user": current_user.to_dict()})

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Erro ao obter usuário: {str(e)}"}),
            500,
        )


@auth_bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
@admin_required
def get_user(user_id):
    """Get user by ID (admin only)"""
    try:
        user = auth_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"success": False, "message": "Usuário não encontrado"}), 404

        return jsonify({"success": True, "user": user.to_dict()})

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Erro ao obter usuário: {str(e)}"}),
            500,
        )


@login_required
@admin_required
@auth_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user (admin only)"""
    try:
        user = auth_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"success": False, "message": "Usuário não encontrado"}), 404

        data = request.get_json() if request.is_json else request.form

        name = data.get("name", "").strip()
        role = data.get("role", "").strip()
        is_active = data.get("is_active")

        if is_active is not None and isinstance(is_active, str):
            is_active = is_active.lower() in ["true", "1", "yes", "on"]

        success = auth_service.update_user_profile(
            user,
            name=name if name else None,
            role=role if role else None,
            is_active=is_active,
        )

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Usuário atualizado com sucesso",
                    "user": user.to_dict(),
                }
            )
        else:
            return (
                jsonify({"success": False, "message": "Falha ao atualizar usuário"}),
                400,
            )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao atualizar usuário: {str(e)}"}
            ),
            500,
        )


@login_required
@admin_required
@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete user (admin only) - Soft delete"""
    try:
        # Não permitir que o admin delete a si mesmo
        if user_id == current_user.id:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Você não pode excluir sua própria conta",
                    }
                ),
                400,
            )

        user = auth_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"success": False, "message": "Usuário não encontrado"}), 404

        # Soft delete - apenas desativa o usuário
        success = auth_service.update_user_status(user_id, False)

        if success:
            return jsonify({"success": True, "message": "Usuário excluído com sucesso"})
        else:
            return (
                jsonify({"success": False, "message": "Falha ao excluir usuário"}),
                400,
            )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao excluir usuário: {str(e)}"}
            ),
            500,
        )


@auth_bp.route("/users/companies", methods=["GET"])
@login_required
@admin_required
def list_companies():
    """List all companies for user-company linking (admin only)"""
    try:
        from models.company import Company
        
        # Query apenas com colunas que existem no banco
        try:
            companies = db.session.query(
                Company.id,
                Company.name,
                Company.legal_name
            ).order_by(Company.name).all()
            
            companies_data = []
            for company in companies:
                companies_data.append({
                    'id': company.id,
                    'name': company.name,
                    'legal_name': company.legal_name
                })
        except Exception as e:
            logger.error(f"Erro ao listar empresas: {e}")
            return jsonify({
                "success": False,
                "message": f"Erro ao listar empresas: {str(e)}"
            }), 500

        return jsonify({"success": True, "companies": companies_data})

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao listar empresas: {str(e)}"}
            ),
            500,
        )


@auth_bp.route("/users/<int:user_id>/link-company", methods=["POST"])
@login_required
@admin_required
def link_user_to_company(user_id):
    """Link user to company (admin only)"""
    try:
        from services.user_employee_service import UserEmployeeService
        
        data = request.get_json() if request.is_json else request.form
        company_id = data.get("company_id")
        
        if not company_id:
            return jsonify({
                "success": False,
                "message": "company_id é obrigatório"
            }), 400
        
        # Verificar se usuário existe
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "Usuário não encontrado"
            }), 404
        
        # Vincular usuário a empresa
        result = UserEmployeeService.add_employee_to_company(
            user_id=user_id,
            company_id=company_id,
            employee_data=data.get("employee_data")
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Usuário vinculado à empresa com sucesso",
                "employee": result.get("employee")
            }), 201
        else:
            error_msg = result.get("error", "Erro ao vincular usuário")
            # Tratar erro de constraint única
            if "já é colaborador" in error_msg.lower() or "unique" in error_msg.lower():
                return jsonify({
                    "success": False,
                    "message": "Usuário já é colaborador desta empresa"
                }), 409  # Conflict
            return jsonify({
                "success": False,
                "message": error_msg
            }), 400

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao vincular usuário: {str(e)}"}
            ),
            500,
        )


@auth_bp.route("/users/<int:user_id>/link-companies", methods=["POST"])
@login_required
@admin_required
def link_user_to_companies(user_id):
    """Link user to multiple companies at once (admin only)"""
    try:
        from services.user_employee_service import UserEmployeeService
        
        data = request.get_json() if request.is_json else request.form
        company_ids = data.get("company_ids", [])
        
        if not company_ids or not isinstance(company_ids, list):
            return jsonify({
                "success": False,
                "message": "company_ids deve ser uma lista de IDs de empresas"
            }), 400
        
        if len(company_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Selecione pelo menos uma empresa"
            }), 400
        
        # Converter para inteiros (caso venham como strings do JSON)
        try:
            company_ids = [int(cid) for cid in company_ids if cid]
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao converter company_ids: {e}")
            return jsonify({
                "success": False,
                "message": "IDs de empresas inválidos"
            }), 400
        
        # Validar se ainda há IDs válidos após conversão
        if len(company_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Nenhum ID de empresa válido foi fornecido"
            }), 400
        
        # Verificar se usuário existe
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "Usuário não encontrado"
            }), 404
        
        # Vincular usuário a múltiplas empresas
        results = UserEmployeeService.add_employee_to_multiple_companies(
            user_id=user_id,
            company_ids=company_ids,
            employee_data=data.get("employee_data")
        )
        
        if results["success"]:
            linked_count = results.get("linked_count", 0)
            skipped_count = results.get("skipped_count", 0)
            
            message = f"Usuário vinculado a {linked_count} empresa(s) com sucesso"
            if skipped_count > 0:
                message += f" ({skipped_count} já estava(m) vinculada(s))"
            
            return jsonify({
                "success": True,
                "message": message,
                "linked_count": linked_count,
                "skipped_count": skipped_count,
                "employees": results.get("employees", [])
            }), 201
        else:
            return jsonify({
                "success": False,
                "message": results.get("error", "Erro ao vincular usuário às empresas")
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao vincular usuário às empresas: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Erro ao vincular usuário: {str(e)}"
        }), 500


@auth_bp.route("/users/<int:user_id>/unlink-company/<int:employee_id>", methods=["DELETE"])
@login_required
@admin_required
def unlink_user_from_company(user_id, employee_id):
    """Unlink user from company (admin only)"""
    try:
        from models.employee import Employee
        from models import db
        
        # Verificar se o employee pertence ao usuário
        employee = Employee.query.filter_by(
            id=employee_id,
            user_id=user_id
        ).first()
        
        if not employee:
            return jsonify({
                "success": False,
                "message": "Vínculo não encontrado"
            }), 404
        
        # Soft delete - apenas desativar
        employee.status = "inactive"
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Vínculo removido com sucesso"
        })

    except Exception as e:
        from models import db
        db.session.rollback()
        return (
            jsonify(
                {"success": False, "message": f"Erro ao remover vínculo: {str(e)}"}
            ),
            500,
        )
