from flask import request
from flask_restful import Resource
from utils.permissions import permission_required
from services.plan_service import PlanService
from schemas.plan import PlanCreate, PlanUpdate, PlanDriverCreate, PlanSectionStatusUpdate, PlanParticipantCreate
from schemas.plan_implantation import AlignmentSchema, ModelMarketSchema, ExecutionSchema, FinanceSchema
from pydantic import ValidationError
import json

class PlanListResource(Resource):
    @permission_required('plans', 'view')
    def get(self):
        company_id = request.args.get('company_id', type=int)
        if not company_id:
            return {"error": "company_id is required"}, 400
        
        mode = request.args.get('mode')
        plans = PlanService.list_plans(company_id, mode)
        return [p.to_dict() for p in plans], 200

    @permission_required('plans', 'create')
    def post(self):
        try:
            data = request.get_json()
            # Validate with Pydantic
            plan_data = PlanCreate(**data)
            plan = PlanService.create_plan(plan_data.company_id, plan_data.model_dump())
            return plan.to_dict(), 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400
        except Exception as e:
            return {"error": str(e)}, 500


class PlanParticipantListResource(Resource):
    @permission_required('plans', 'view')
    def get(self, plan_id):
        company_id = request.args.get('company_id', type=int)
        participants = PlanService.list_participants(plan_id, company_id)
        return [p.to_dict() for p in participants], 200

    @permission_required('plans', 'edit')
    def post(self, plan_id):
        try:
            company_id = request.args.get('company_id', type=int)
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
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": str(e)}, 500


class PlanParticipantResource(Resource):
    @permission_required('plans', 'edit')
    def delete(self, plan_id, participant_id):
        try:
            company_id = request.args.get('company_id', type=int)
            PlanService.remove_participant(plan_id, company_id, participant_id)
            return {"message": "Participant removed"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception as e:
            return {"error": str(e)}, 500


class PlanResource(Resource):
    @permission_required('plans', 'view')
    def get(self, plan_id):
        company_id = request.args.get('company_id', type=int)
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return {"error": "Plan not found"}, 404
        return plan.to_dict(), 200

    @permission_required('plans', 'edit')
    def patch(self, plan_id):
        try:
            company_id = request.args.get('company_id', type=int)
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


class PlanDriverResource(Resource):
    @permission_required('plans', 'edit')
    def get(self, plan_id):
        from services.plan_service import PlanService
        company_id = request.args.get('company_id', type=int)
        drivers = PlanService.list_drivers(plan_id, company_id)
        return [d.to_dict() for d in drivers], 200

    @permission_required('plans', 'edit')
    def post(self, plan_id):
        try:
            company_id = request.args.get('company_id', type=int)
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
            return {"error": str(e)}, 400
        except Exception as e:
            from models import db
            db.session.rollback()
            return {"error": str(e)}, 500


class PlanDriverDetailResource(Resource):
    @permission_required('plans', 'edit')
    def put(self, plan_id, driver_id):
        try:
            company_id = request.args.get('company_id', type=int)
            data = request.get_json()
            
            # TODO: Add to service
            from models import PlanDriver, db
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
            return {"error": str(e)}, 500

    @permission_required('plans', 'edit')
    def delete(self, plan_id, driver_id):
        try:
            company_id = request.args.get('company_id', type=int)
            
            from models import PlanDriver, db
            driver = PlanDriver.query.filter_by(id=driver_id, plan_id=plan_id).first()
            if not driver:
                return {"error": "Driver not found"}, 404
                
            db.session.delete(driver)
            db.session.commit()
            return {"message": "Driver deleted"}, 200
        except Exception as e:
            from models import db
            db.session.rollback()
            return {"error": str(e)}, 500


class PlanSectionStatusResource(Resource):
    @permission_required('plans', 'edit')
    def patch(self, plan_id, section_key):
        try:
            data = request.get_json()
            status_data = PlanSectionStatusUpdate(**data)
            
            PlanService.update_section_status(plan_id, section_key, status_data.status)
            return {"message": "Status updated"}, 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400


class PlanImplantationResource(Resource):
    @permission_required('plans', 'view')
    def get(self, plan_id, section_key):
        company_id = request.args.get('company_id', type=int)
        data = PlanService.get_implantation_data(plan_id, company_id, section_key)
        if not data:
            return {"content": {}}, 200
        return data.to_dict(), 200

    @permission_required('plans', 'edit')
    def post(self, plan_id, section_key):
        try:
            company_id = request.args.get('company_id', type=int)
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
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": str(e)}, 500



