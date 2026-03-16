from flask import Blueprint, current_app, jsonify
from models import db, Company, Project, User, Employee, Indicator, IndicatorGroup, IndicatorGoal, IndicatorData, Process, ProcessInstance, OKRGlobal, KeyResult
from datetime import datetime, timedelta

dev_bp = Blueprint('dev', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'

@dev_bp.route('/debug/routes')
def debug_routes():
    """Debug: List all registered routes"""
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return {'routes': routes}, 200

@dev_bp.route('/seed-demo')
def seed_demo():
    """Temporary route to seed demo data"""
    # Check if admin user exists
    admin = User.query.filter_by(email="admin@gestaoversus.com.br").first()
    if not admin:
        admin = User(
            email="admin@gestaoversus.com.br",
            name="Admin Versus",
            role="admin"
        )
        admin.set_password("123456")
        db.session.add(admin)
        db.session.commit()

    # Check if company exists
    company = Company.query.filter_by(client_code="VT001").first()
    if not company:
        company = Company(
            name="Versus Tech Demo",
            client_code="VT001",
            description="Empresa de tecnologia e consultoria.",
            segment="Tecnologia",
            size="Médio"
        )
        db.session.add(company)
        db.session.commit()

    # Add some projects
    projects_data = [
        {"name": "Marketing Digital 2024", "status": "in_progress", "owner": "Renato Santos", "progress": 45},
        {"name": "Expansão de Infraestrutura", "status": "planned", "owner": "Clara Mendes", "progress": 0},
    ]

    for p_data in projects_data:
        existing = Project.query.filter_by(name=p_data['name']).first()
        if not existing:
            project = Project(
                company_id=company.id,
                name=p_data['name'],
                status=p_data['status'],
                owner=p_data['owner'],
                progress=p_data['progress'],
                deadline=(datetime.now() + timedelta(days=60)).date()
            )
            db.session.add(project)
    
    # Add OKR
    if not OKRGlobal.query.first():
        okr = OKRGlobal(
            company_id=company.id,
            objective="Liderar o mercado de consultoria em BI até Dez/2024",
            type="aceleracao",
            owner="CEO",
            deadline=(datetime.today() + timedelta(days=180))
        )
        db.session.add(okr)
        db.session.commit()
    
    # Add Indicator
    if not Indicator.query.filter_by(code="KPI-001").first():
        kpi = Indicator(
            company_id=company.id,
            code="KPI-001",
            name="Faturamento Mensal",
            unit="R$",
            polarity="positive"
        )
        db.session.add(kpi)
        db.session.commit()
        
        goal = IndicatorGoal(
            company_id=company.id,
            indicator_id=kpi.id,
            goal_value=100000,
            goal_date=datetime.today().date(),
            status="active",
            code="META-001"
        )
        db.session.add(goal)
        db.session.commit()
        
        entry = IndicatorData(
            company_id=company.id,
            indicator_id=kpi.id,
            goal_id=goal.id,
            measured_date=datetime.today().date(),
            measured_value=85000,
            status='verified'
        )
        db.session.add(entry)

    # Add Demo Role and Employee for permission testing
    from models.role import Role
    demo_role = Role.query.filter_by(company_id=company.id, title="Gerente de Projetos").first()
    if not demo_role:
        demo_role = Role(
            company_id=company.id,
            title="Gerente de Projetos"
        )
        db.session.add(demo_role)
    
    demo_role.permissions = {
        "projects": ["view", "create", "edit", "delete"],
        "indicators": ["view", "create", "edit", "delete"],
        "processes": ["view", "create", "edit", "delete"],
        "companies": ["view", "create", "edit", "delete"],
        "okrs": ["view", "create", "edit", "delete"],
        "employees": ["view", "create", "edit", "delete"]
    }
    db.session.commit()

    # Link Admin as an employee of this company (even if global admin, it's good for data structure)
    if not Employee.query.filter_by(user_id=admin.id, company_id=company.id).first():
        emp = Employee(
            company_id=company.id,
            user_id=admin.id,
            role_id=demo_role.id,
            name=admin.name,
            email=admin.email,
            status="active"
        )
        db.session.add(emp)

    # Create a non-admin user for testing permissions
    test_user = User.query.filter_by(email="user@test.com").first()
    if not test_user:
        test_user = User(
            email="user@test.com",
            name="Test User",
            role="collaborator"
        )
        test_user.set_password("123456")
        db.session.add(test_user)
        db.session.commit()
        
        # Add test user as employee with the demo role
        emp_test = Employee(
            company_id=company.id,
            user_id=test_user.id,
            role_id=demo_role.id,
            name=test_user.name,
            email=test_user.email,
            status="active"
        )
        db.session.add(emp_test)

    db.session.commit()

    return {"message": "Demo data seeded successfully!"}, 200

@dev_bp.route('/ping/dependencies')
def ping_dependencies():
    from models.project import ProjectTaskDependency
    from models import db
    try:
        count = ProjectTaskDependency.query.count()
        return jsonify({
            "status": "ok",
            "message": "ProjectTaskDependency table is accessible",
            "count": count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": PUBLIC_ERROR_MESSAGE
        }), 500

@dev_bp.route('/trigger-proactive')
def trigger_proactive():
    """Debug: Manually trigger the Sapiens morning summary"""
    from services.proactive_service import send_morning_summaries
    from flask import current_app
    send_morning_summaries(current_app._get_current_object())
    return {"message": "Proactive morning summary triggered!"}, 200
