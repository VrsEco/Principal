from flask import request, session
from flask_restful import Resource
from utils.permissions import active_company_permission_required
from services.plan_service import PlanService
from schemas.plan import PlanCreate, PlanUpdate, PlanDriverCreate, PlanSectionStatusUpdate, PlanParticipantCreate
from schemas.plan_implantation import AlignmentSchema, ModelMarketSchema, ExecutionSchema, FinanceSchema
from pydantic import ValidationError
import json

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


def _get_request_company_id():
    from api.resources.project import get_request_company_id

    try:
        active_company_id = int(session.get('active_company_id'))
    except (TypeError, ValueError):
        active_company_id = None
    return active_company_id if active_company_id and active_company_id > 0 else get_request_company_id()

class PlanListResource(Resource):
    @active_company_permission_required('plans', 'view')
    def get(self):
        company_id = _get_request_company_id()
                    
        if not company_id:
            return {"error": "company_id is required"}, 400
        
        mode = request.args.get('mode')
        paginated = (request.args.get('paginated') or 'false').strip().lower() == 'true'
        if not paginated:
            plans = PlanService.list_plans(company_id, mode)
            return [p.to_dict() for p in plans], 200

        plans, total, page, per_page = PlanService.list_plans_page(
            company_id,
            mode,
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 50, type=int),
        )
        return {
            'items': [plan.to_dict() for plan in plans],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_more': page * per_page < total,
            },
        }, 200

    @active_company_permission_required('plans', 'create')
    def post(self):
        try:
            data = request.get_json()
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data['company_id'] = company_id
            # Validate with Pydantic
            plan_data = PlanCreate(**data)
            plan = PlanService.create_plan(plan_data.company_id, plan_data.model_dump())
            return plan.to_dict(), 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except Exception as e:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanParticipantListResource(Resource):
    @active_company_permission_required('plans', 'view')
    def get(self, plan_id):
        company_id = _get_request_company_id()
        if not company_id:
            return {"error": "company_id is required"}, 400
        participants = PlanService.list_participants(plan_id, company_id)
        return [p.to_dict() for p in participants], 200

    @active_company_permission_required('plans', 'edit')
    def post(self, plan_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data = request.get_json()
            # Remove company_id if present in body (handled via query param)
            if 'company_id' in data:
                del data['company_id']
            participant_data = PlanParticipantCreate(**data)
            
            participant = PlanService.add_participant(plan_id, company_id, participant_data.model_dump())
            return participant.to_dict(), 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except ValueError as e:
            return {"error": "Requisição inválida."}, 400
        except Exception as e:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanParticipantResource(Resource):
    @active_company_permission_required('plans', 'edit')
    def delete(self, plan_id, participant_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            PlanService.remove_participant(plan_id, company_id, participant_id)
            return {"message": "Participant removed"}, 200
        except ValueError as e:
            return {"error": "Recurso não encontrado."}, 404
        except Exception as e:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanResource(Resource):
    @active_company_permission_required('plans', 'view')
    def get(self, plan_id):
        company_id = _get_request_company_id()
        if not company_id:
            return {"error": "company_id is required"}, 400
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return {"error": "Plan not found"}, 404
        return plan.to_dict(), 200

    @active_company_permission_required('plans', 'edit')
    def patch(self, plan_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data = request.get_json()
            # Validate with Pydantic
            update_data = PlanUpdate(**data)
            
            plan = PlanService.get_plan(plan_id, company_id)
            if not plan:
                return {"error": "Plan not found"}, 404
            
            # Apply updates
            for key, value in update_data.model_dump(exclude_unset=True).items():
                setattr(plan, key, value)
            
            from models import db
            db.session.commit()
            return plan.to_dict(), 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except Exception:
            from models import db
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanDriverResource(Resource):
    @active_company_permission_required('plans', 'edit')
    def get(self, plan_id):
        from services.plan_service import PlanService
        company_id = _get_request_company_id()
        if not company_id:
            return {"error": "company_id is required"}, 400
        drivers = PlanService.list_drivers(plan_id, company_id)
        return [d.to_dict() for d in drivers], 200

    @active_company_permission_required('plans', 'edit')
    def post(self, plan_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data = request.get_json()
            if 'company_id' in data:
                del data['company_id']
            # Basic validation manually if schema fails or to succeed schema
            if not data.get('type') or not data.get('description'):
                return {"error": "Type and description are required"}, 400
                
            driver = PlanService.add_driver(plan_id, company_id, data)
            return driver.to_dict(), 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except ValueError as e:
            return {"error": "Requisição inválida."}, 400
        except Exception as e:
            from models import db
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanDriverDetailResource(Resource):
    @active_company_permission_required('plans', 'edit')
    def put(self, plan_id, driver_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data = request.get_json()
            
            # TODO: Add to service
            from models import PlanDriver, db
            plan = PlanService.get_plan(plan_id, company_id)
            if not plan:
                return {"error": "Plan not found"}, 404
            driver = PlanDriver.query.filter_by(id=driver_id, plan_id=plan_id).first()
            if not driver:
                return {"error": "Driver not found"}, 404
                
            if 'type' in data:
                driver.type = data['type']
            if 'description' in data:
                driver.description = data['description']
            if 'priority' in data:
                driver.priority = data['priority']
            if 'meta_data' in data:
                driver.meta_data = data['meta_data']
                
            db.session.commit()
            return driver.to_dict(), 200
        except Exception as e:
            from models import db
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @active_company_permission_required('plans', 'edit')
    def delete(self, plan_id, driver_id):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            
            from models import PlanDriver, db
            plan = PlanService.get_plan(plan_id, company_id)
            if not plan:
                return {"error": "Plan not found"}, 404
            driver = PlanDriver.query.filter_by(id=driver_id, plan_id=plan_id).first()
            if not driver:
                return {"error": "Driver not found"}, 404
                
            db.session.delete(driver)
            db.session.commit()
            return {"message": "Driver deleted"}, 200
        except Exception as e:
            from models import db
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanSectionStatusResource(Resource):
    @active_company_permission_required('plans', 'edit')
    def patch(self, plan_id, section_key):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            data = request.get_json()
            status_data = PlanSectionStatusUpdate(**data)

            plan = PlanService.get_plan(plan_id, company_id)
            if not plan:
                return {"error": "Plan not found"}, 404
            PlanService.update_section_status(plan_id, section_key, status_data.status)
            return {"message": "Status updated"}, 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except Exception:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class PlanImplantationResource(Resource):
    @active_company_permission_required('plans', 'view')
    def get(self, plan_id, section_key):
        company_id = _get_request_company_id()
        if not company_id:
            return {"error": "company_id is required"}, 400
        data = PlanService.get_implantation_data(plan_id, company_id, section_key)
        if not data:
            return {"content": {}}, 200
        return data.to_dict(), 200

    @active_company_permission_required('plans', 'edit')
    def post(self, plan_id, section_key):
        try:
            company_id = _get_request_company_id()
            if not company_id:
                return {"error": "company_id is required"}, 400
            content = request.get_json()
            
            # Structured validation based on section
            schema_map = {
                'alignment': AlignmentSchema,
                'model': ModelMarketSchema,
                'execution': ExecutionSchema,
                'finance': FinanceSchema
            }
            
            if section_key in schema_map:
                validated_data = schema_map[section_key](**content)
                content = validated_data.model_dump()
            
            data = PlanService.save_implantation_data(plan_id, company_id, section_key, content)
            return data.to_dict(), 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except ValueError as e:
            return {"error": "Requisição inválida."}, 400
        except Exception as e:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500
