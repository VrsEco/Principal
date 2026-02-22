from flask import request
from utils.permissions import permission_required
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, OKRGlobal, KeyResult, OKRArea, KeyResultArea
from schemas.okr import (
    okr_global_schema, okrs_global_schema,
    key_result_schema, key_results_schema,
    okr_area_schema, okrs_area_schema,
    key_result_area_schema, key_results_area_schema
)


class OKRGlobalListResource(Resource):
    @permission_required('okrs', 'view')
    def get(self):
        plan_id = request.args.get('plan_id', type=int)
        company_id = request.args.get('company_id', type=int)
        
        query = OKRGlobal.query
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
        if company_id:
            query = query.filter_by(company_id=company_id)
            
        okrs = query.all()
        return okrs_global_schema.dump(okrs), 200

    def post(self):
        try:
            data = request.get_json()
            okr = okr_global_schema.load(data)
            db.session.add(okr)
            db.session.commit()
            return okr_global_schema.dump(okr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


class OKRGlobalResource(Resource):
    @permission_required('okrs', 'view')
    def get(self, okr_id):
        okr = OKRGlobal.query.get_or_404(okr_id)
        return okr_global_schema.dump(okr), 200

    def put(self, okr_id):
        okr = OKRGlobal.query.get_or_404(okr_id)
        try:
            data = request.get_json()
            okr = okr_global_schema.load(data, instance=okr, partial=True)
            db.session.commit()
            return okr_global_schema.dump(okr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    def delete(self, okr_id):
        okr = OKRGlobal.query.get_or_404(okr_id)
        try:
            db.session.delete(okr)
            db.session.commit()
            return {"message": "OKR deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


class KeyResultListResource(Resource):
    @permission_required('okrs', 'edit')
    def post(self):
        try:
            data = request.get_json()
            kr = key_result_schema.load(data)
            db.session.add(kr)
            db.session.commit()
            return key_result_schema.dump(kr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class KeyResultResource(Resource):
    @permission_required('okrs', 'edit')
    def delete(self, kr_id):
        kr = KeyResult.query.get_or_404(kr_id)
        db.session.delete(kr)
        db.session.commit()
        return {"message": "KR deleted successfully"}, 200

    @permission_required('okrs', 'edit')
    def put(self, kr_id):
        kr = KeyResult.query.get_or_404(kr_id)
        try:
            data = request.get_json()
            kr = key_result_schema.load(data, instance=kr, partial=True)
            db.session.commit()
            return key_result_schema.dump(kr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


class OKRAreaListResource(Resource):
    @permission_required('okrs', 'view')
    def get(self):
        plan_id = request.args.get('plan_id', type=int)
        company_id = request.args.get('company_id', type=int)
        
        query = OKRArea.query
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
        if company_id:
            query = query.filter_by(company_id=company_id)
            
        okrs = query.all()
        return okrs_area_schema.dump(okrs), 200

    def post(self):
        try:
            data = request.get_json()
            okr = okr_area_schema.load(data)
            db.session.add(okr)
            db.session.commit()
            return okr_area_schema.dump(okr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class OKRAreaResource(Resource):
    @permission_required('okrs', 'view')
    def get(self, okr_id):
        okr = OKRArea.query.get_or_404(okr_id)
        return okr_area_schema.dump(okr), 200

    def put(self, okr_id):
        okr = OKRArea.query.get_or_404(okr_id)
        try:
            data = request.get_json()
            okr = okr_area_schema.load(data, instance=okr, partial=True)
            db.session.commit()
            return okr_area_schema.dump(okr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    def delete(self, okr_id):
        okr = OKRArea.query.get_or_404(okr_id)
        db.session.delete(okr)
        db.session.commit()
        return {"message": "Area OKR deleted successfully"}, 200


class KeyResultAreaListResource(Resource):
    @permission_required('okrs', 'edit')
    def post(self):
        try:
            data = request.get_json()
            kr = key_result_area_schema.load(data)
            db.session.add(kr)
            db.session.commit()
            return key_result_area_schema.dump(kr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class KeyResultAreaResource(Resource):
    @permission_required('okrs', 'edit')
    def put(self, kr_id):
        kr = KeyResultArea.query.get_or_404(kr_id)
        try:
            data = request.get_json()
            kr = key_result_area_schema.load(data, instance=kr, partial=True)
            db.session.commit()
            return key_result_area_schema.dump(kr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('okrs', 'edit')
    def delete(self, kr_id):
        kr = KeyResultArea.query.get_or_404(kr_id)
        db.session.delete(kr)
        db.session.commit()
        return {"message": "KR Area deleted successfully"}, 200