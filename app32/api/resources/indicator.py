from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, Indicator, IndicatorGroup, IndicatorGoal, IndicatorData
from schemas.indicator import (
    indicator_schema, indicators_schema, 
    indicator_group_schema, indicator_groups_schema,
    indicator_goal_schema, indicator_goals_schema,
    indicator_data_schema, indicator_data_list_schema
)

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
    if cid is not None: return cid
    
    # 2. Try JSON Body
    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: return cid
    except:
        pass

    # 3. Try Session
    cid = clean(session.get('active_company_id'))
    return cid

class IndicatorListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        process_id = request.args.get('process_id')
        project_id = request.args.get('project_id')
        
        query = Indicator.query.filter_by(company_id=company_id)
        if process_id:
            query = query.filter_by(process_id=process_id)
        if project_id:
            query = query.filter_by(project_id=project_id)
            
        indicators = query.all()
        return indicators_schema.dump(indicators), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            indicator = indicator_schema.load(data)
            db.session.add(indicator)
            db.session.commit()
            return indicator_schema.dump(indicator), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, indicator_id):
        indicator = Indicator.query.get_or_404(indicator_id)
        return indicator_schema.dump(indicator), 200

    @permission_required('indicators', 'edit')
    def put(self, indicator_id):
        indicator = Indicator.query.get_or_404(indicator_id)
        try:
            data = request.get_json()
            indicator = indicator_schema.load(data, instance=indicator, partial=True)
            db.session.commit()
            return indicator_schema.dump(indicator), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('indicators', 'delete')
    def delete(self, indicator_id):
        indicator = Indicator.query.get_or_404(indicator_id)
        try:
            db.session.delete(indicator)
            db.session.commit()
            return {"message": "Indicator deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGroupListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        query = IndicatorGroup.query.filter_by(company_id=company_id)
        groups = query.all()
        return indicator_groups_schema.dump(groups), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            group = indicator_group_schema.load(data)
            db.session.add(group)
            db.session.commit()
            return indicator_group_schema.dump(group), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGoalListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        indicator_id = request.args.get('indicator_id')
        if not indicator_id:
            return [], 200
            
        query = IndicatorGoal.query.filter_by(indicator_id=indicator_id)
        goals = query.all()
        return indicator_goals_schema.dump(goals), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            goal = indicator_goal_schema.load(data)
            db.session.add(goal)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGoalResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        return indicator_goal_schema.dump(goal), 200

    @permission_required('indicators', 'edit')
    def put(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            data = request.get_json()
            goal = indicator_goal_schema.load(data, instance=goal, partial=True)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('indicators', 'edit')
    def delete(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            db.session.delete(goal)
            db.session.commit()
            return {"message": "Goal deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorDataListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        goal_id = request.args.get('goal_id')
        indicator_id = request.args.get('indicator_id')
        
        if not goal_id and not indicator_id:
            return [], 200
            
        query = IndicatorData.query
        if goal_id:
            query = query.filter_by(goal_id=goal_id)
        elif indicator_id:
            query = query.join(IndicatorGoal).filter(IndicatorGoal.indicator_id == indicator_id)
            
        data_records = query.all()
        return indicator_data_list_schema.dump(data_records), 200


    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            record = indicator_data_schema.load(data)
            db.session.add(record)
            db.session.commit()
            return indicator_data_schema.dump(record), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorDataResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, data_id):
        record = IndicatorData.query.get_or_404(data_id)
        return indicator_data_schema.dump(record), 200

    @permission_required('indicators', 'edit')
    def delete(self, data_id):
        record = IndicatorData.query.get_or_404(data_id)
        try:
            db.session.delete(record)
            db.session.commit()
            return {"message": "Data record deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
