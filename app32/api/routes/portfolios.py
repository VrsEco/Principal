"""Portfolio API routes"""
from flask import Blueprint, request, jsonify, render_template, abort
from flask_login import login_required, current_user
from models import db
from models.portfolio import Portfolio
from models.company import Company
from schemas.portfolio import (
    PortfolioSchema,
    PortfolioCreateSchema,
    PortfolioUpdateSchema,
)
from marshmallow import ValidationError
from utils.permissions import permission_required, has_company_full_access

portfolios_bp = Blueprint("portfolios", __name__)

portfolio_schema = PortfolioSchema()
portfolios_schema = PortfolioSchema(many=True)
portfolio_create_schema = PortfolioCreateSchema()
portfolio_update_schema = PortfolioUpdateSchema()


@portfolios_bp.route("/project-portfolios")
@permission_required("projects", "view")
def portfolios_page_redirect():
    """Redirect to the portfolio page of the active company."""
    from flask import session, redirect, url_for

    company_id = session.get("active_company_id")
    if not company_id:
        from models.employee import Employee

        emp = Employee.query.filter_by(user_id=current_user.id, status="active").first()
        if emp:
            company_id = emp.company_id
            session["active_company_id"] = company_id

    if company_id:
        return redirect(
            url_for("portfolios.portfolios_page", company_id=company_id)
        )

    # Fallback to dashboard if no company found
    return redirect(url_for("my_work.my_work"))


@portfolios_bp.route("/companies/<int:company_id>/project-portfolios")
@permission_required("projects", "view")
def portfolios_page(company_id):
    """Portfolio management page"""
    if not has_company_full_access(company_id):
        abort(403, description='Acesso negado: colaboradores não podem acessar portfólios de projetos.')
    company = Company.query.get_or_404(company_id)
    return render_template("project_portfolios.html", company=company)


@portfolios_bp.route("/api/companies/<int:company_id>/portfolios", methods=["GET"])
@permission_required("projects", "view")
def list_portfolios(company_id):
    """List all portfolios for a company"""
    try:
        if not has_company_full_access(company_id):
            return jsonify({"success": False, "message": "Acesso negado: colaboradores não podem acessar portfólios de projetos."}), 403
        # Verify company access
        company = Company.query.get_or_404(company_id)

        # Get all portfolios for this company
        portfolios = Portfolio.query.filter_by(company_id=company_id).order_by(
            Portfolio.code
        ).all()

        # Serialize with project count
        portfolios_data = [p.to_dict(include_project_count=True) for p in portfolios]

        return jsonify({"success": True, "portfolios": portfolios_data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@portfolios_bp.route("/api/companies/<int:company_id>/portfolios", methods=["POST"])
@permission_required("projects", "create")
def create_portfolio(company_id):
    """Create a new portfolio"""
    try:
        if not has_company_full_access(company_id):
            return jsonify({"success": False, "message": "Acesso negado: colaboradores não podem criar portfólios."}), 403
        # Verify company access
        company = Company.query.get_or_404(company_id)

        # Validate request data
        data = request.get_json()
        validated_data = portfolio_create_schema.load(data)

        # Check if code already exists for this company
        existing = Portfolio.query.filter_by(
            company_id=company_id, code=validated_data["code"]
        ).first()
        if existing:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Código '{validated_data['code']}' já existe para esta empresa",
                    }
                ),
                400,
            )

        # Create portfolio
        portfolio = Portfolio(company_id=company_id, **validated_data)
        db.session.add(portfolio)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Portfólio criado com sucesso",
                    "portfolio": portfolio.to_dict(),
                }
            ),
            201,
        )

    except ValidationError as e:
        return jsonify({"success": False, "message": str(e.messages)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@portfolios_bp.route(
    "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>", methods=["GET"]
)
@permission_required("projects", "view")
def get_portfolio(company_id, portfolio_id):
    """Get a specific portfolio"""
    try:
        if not has_company_full_access(company_id):
            return jsonify({"success": False, "message": "Acesso negado: colaboradores não podem acessar portfólios de projetos."}), 403
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, company_id=company_id
        ).first_or_404()

        return (
            jsonify(
                {"success": True, "portfolio": portfolio.to_dict(include_project_count=True)}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@portfolios_bp.route(
    "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>", methods=["PUT"]
)
@permission_required("projects", "edit")
def update_portfolio(company_id, portfolio_id):
    """Update a portfolio"""
    try:
        if not has_company_full_access(company_id):
            return jsonify({"success": False, "message": "Acesso negado: colaboradores não podem editar portfólios."}), 403
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, company_id=company_id
        ).first_or_404()

        # Validate request data
        data = request.get_json()
        validated_data = portfolio_update_schema.load(data)

        # Check if code is being changed and if it already exists
        if "code" in validated_data and validated_data["code"] != portfolio.code:
            existing = Portfolio.query.filter_by(
                company_id=company_id, code=validated_data["code"]
            ).first()
            if existing:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Código '{validated_data['code']}' já existe para esta empresa",
                        }
                    ),
                    400,
                )

        # Update portfolio
        for key, value in validated_data.items():
            setattr(portfolio, key, value)

        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Portfólio atualizado com sucesso",
                    "portfolio": portfolio.to_dict(),
                }
            ),
            200,
        )

    except ValidationError as e:
        return jsonify({"success": False, "message": str(e.messages)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@portfolios_bp.route(
    "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>",
    methods=["DELETE"],
)
@permission_required("projects", "delete")
def delete_portfolio(company_id, portfolio_id):
    """Delete a portfolio"""
    try:
        if not has_company_full_access(company_id):
            return jsonify({"success": False, "message": "Acesso negado: colaboradores não podem excluir portfólios."}), 403
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, company_id=company_id
        ).first_or_404()

        # Check if portfolio has associated projects
        from models.project import Project

        project_count = Project.query.filter_by(portfolio_id=portfolio_id).count()
        if project_count > 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Não é possível excluir o portfólio. Existem {project_count} projeto(s) associado(s).",
                    }
                ),
                400,
            )

        db.session.delete(portfolio)
        db.session.commit()

        return (
            jsonify({"success": True, "message": "Portfólio removido com sucesso"}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
