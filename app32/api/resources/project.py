from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, Project
from schemas.project import project_schema, projects_schema
from utils.permissions import permission_required

def get_request_company_id():
    from flask import session
    
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # 1. Try Query Arg
    cid = clean(request.args.get('company_id'))
    if cid is not None: 
        print(f"DEBUG: get_request_company_id - from query arg: {cid}")
        return cid
    
    # 2. Try JSON Body
    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: 
                    print(f"DEBUG: get_request_company_id - from JSON: {cid}")
                    return cid
    except:
        pass

    # 3. Try Session
    cid = clean(session.get('active_company_id'))
    if cid:
        print(f"DEBUG: get_request_company_id - from session: {cid}")
        return cid

    # 4. Fallback: authenticated user
    from flask_login import current_user
    if current_user.is_authenticated:
        from models import Company, Employee
        
        if current_user.role == 'admin':
            first = Company.query.filter_by(is_active=True).order_by(Company.id).first()
            if first:
                print(f"DEBUG: get_request_company_id - admin fallback: {first.id}")
                return first.id
        else:
            emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
            if emp:
                print(f"DEBUG: get_request_company_id - employee fallback: {emp.company_id}")
                return emp.company_id
                
    return None

class ProjectListResource(Resource):
    @permission_required('projects', 'view')
    def get(self):
        """List all projects, optionally filtered by company_id and plan_id."""
        from flask import session
        from flask_login import current_user
        from datetime import datetime
        
        raw_cid = request.args.get('company_id')
        log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/logs/proj_api_debug.log'
        
        # Direct file logging for debugging in production
        try:
            with open(log_path, 'a') as lf:
                lf.write(f"\n[{datetime.now()}] --- PROJECT GET REQUEST ---\n")
                lf.write(f"  URL args: {dict(request.args)}\n")
                lf.write(f"  session: {dict(session)}\n")
                lf.write(f"  user authenticated: {current_user.is_authenticated}\n")
                if current_user.is_authenticated:
                    lf.write(f"  user id: {current_user.id}, role: {current_user.role}\n")
        except Exception as le:
            # Fallback for local dev or perm issue
            pass
        
        company_id = get_request_company_id()
        plan_id = request.args.get('plan_id', type=int)
        
        try:
            with open(log_path, 'a') as lf:
                lf.write(f"  get_request_company_id resolved: {company_id}\n")
        except:
            pass
        
        if not company_id:
            try:
                with open(log_path, 'a') as lf:
                    lf.write(f"  RETURNING [] because company_id is None\n")
            except:
                pass
            return [], 200
            
        query = Project.query.filter_by(company_id=company_id).order_by(Project.id.asc())
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
            
        projects = query.all()
        
        try:
            with open(log_path, 'a') as lf:
                lf.write(f"  found {len(projects)} projects for {company_id}\n")
        except:
            pass
        
        return projects_schema.dump(projects), 200

    @permission_required('projects', 'create')
    def post(self):
        """Create a new project."""
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            # Handle portfolio creation if needed
            portfolio_option = data.pop('portfolio_option', None)
            
            if portfolio_option == 'new':
                # Create a new portfolio with the plan name
                from models import Portfolio, Plan
                plan_id = data.get('plan_id')
                
                if plan_id:
                    plan = Plan.query.get(plan_id)
                    if plan:
                        # Check if portfolio already exists for this plan
                        existing_portfolio = Portfolio.query.filter_by(
                            company_id=cid,
                            name=plan.title  # FIXED: use 'title' instead of 'name'
                        ).first()
                        
                        if existing_portfolio:
                            data['portfolio_id'] = existing_portfolio.id
                        else:
                            # Create new portfolio
                            new_portfolio = Portfolio(
                                company_id=cid,
                                code=f"PLAN-{plan_id}",
                                name=plan.title,  # FIXED: use 'title' instead of 'name'
                                notes=f"Portfólio criado automaticamente para o plano: {plan.title}"  # FIXED
                            )
                            db.session.add(new_portfolio)
                            db.session.flush()  # Get the ID without committing
                            data['portfolio_id'] = new_portfolio.id
            
            # Ensure IDs are integers or None
            for field in ['plan_id', 'portfolio_id']:
                if field in data:
                    val = data[field]
                    if val is None or str(val).strip().lower() in ('null', 'undefined', ''):
                        data[field] = None
                    else:
                        try:
                            data[field] = int(float(val))
                        except (ValueError, TypeError):
                            data[field] = None
                
            project = project_schema.load(data)
            db.session.add(project)
            db.session.commit()
            return project_schema.dump(project), 201
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProjectResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """Get a single project."""
        project = Project.query.get_or_404(project_id)
        return project_schema.dump(project), 200

    @permission_required('projects', 'edit')
    def put(self, project_id):
        """Update a project."""
        project = Project.query.get_or_404(project_id)
        try:
            data = request.get_json()
            cid = get_request_company_id()
            
            # Handle portfolio creation if needed
            portfolio_option = data.pop('portfolio_option', None)
            if portfolio_option == 'new':
                from models import Portfolio, Plan
                plan_id = data.get('plan_id') or project.plan_id
                if plan_id:
                    plan = Plan.query.get(plan_id)
                    if plan:
                        existing_portfolio = Portfolio.query.filter_by(
                            company_id=cid,
                            name=plan.title
                        ).first()
                        
                        if existing_portfolio:
                            data['portfolio_id'] = existing_portfolio.id
                        else:
                            new_portfolio = Portfolio(
                                company_id=cid,
                                code=f"PLAN-{plan_id}",
                                name=plan.title,
                                notes=f"Portfólio criado automaticamente para o plano: {plan.title}"
                            )
                            db.session.add(new_portfolio)
                            db.session.flush()
                            data['portfolio_id'] = new_portfolio.id

            # Ensure IDs are integers or None
            for field in ['plan_id', 'portfolio_id']:
                if field in data:
                    val = data[field]
                    if val is None or str(val).strip().lower() in ('null', 'undefined', ''):
                        data[field] = None
                    else:
                        try:
                            data[field] = int(float(val) if val else 0) if val else None
                        except (ValueError, TypeError):
                            data[field] = None
                
            print(f"DEBUG: Project PUT data before schema load: {data}")
            project = project_schema.load(data, instance=project, partial=True)
            db.session.commit()
            return project_schema.dump(project), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('projects', 'delete')
    def delete(self, project_id):
        """Delete a project."""
        project = Project.query.get_or_404(project_id)
        try:
            db.session.delete(project)
            db.session.commit()
            return {"message": "Project deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
