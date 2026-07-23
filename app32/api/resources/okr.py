from flask import request
from utils.permissions import permission_required
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, OKRGlobal, KeyResult, OKRArea, KeyResultArea
PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."

from schemas.okr import (
    okr_global_schema, okrs_global_schema,
    key_result_schema, key_results_schema,
    okr_area_schema, okrs_area_schema,
    key_result_area_schema, key_results_area_schema
)


def _get_request_company_id():
    from api.resources.project import get_request_company_id

    return get_request_company_id()


def _ensure_company_id():
    company_id = _get_request_company_id()
    if not company_id:
        return None, ({"error": "company_id is required"}, 400)
    return company_id, None


def _tenant_key_result_or_404(kr_id, company_id):
    return (
        KeyResult.query.join(OKRGlobal, KeyResult.okr_global_id == OKRGlobal.id)
        .filter(KeyResult.id == kr_id, OKRGlobal.company_id == company_id)
        .first_or_404()
    )


def _tenant_key_result_area_or_404(kr_id, company_id):
    return (
        KeyResultArea.query.join(OKRArea, KeyResultArea.okr_area_id == OKRArea.id)
        .filter(KeyResultArea.id == kr_id, OKRArea.company_id == company_id)
        .first_or_404()
    )


def _validate_global_okr_parent(data, company_id):
    okr_id = data.get("okr_global_id")
    if not okr_id:
        return {"okr_global_id": ["Missing data for required field."]}
    if not OKRGlobal.query.filter_by(id=okr_id, company_id=company_id).first():
        return {"okr_global_id": ["OKR global não encontrado para a empresa ativa."]}
    return None


def _validate_area_okr_parent(data, company_id):
    okr_id = data.get("okr_area_id")
    if not okr_id:
        return {"okr_area_id": ["Missing data for required field."]}
    if not OKRArea.query.filter_by(id=okr_id, company_id=company_id).first():
        return {"okr_area_id": ["OKR de área não encontrado para a empresa ativa."]}
    return None


class OKRGlobalListResource(Resource):
    @permission_required('okrs', 'view')
    def get(self):
        plan_id = request.args.get('plan_id', type=int)
        company_id, error = _ensure_company_id()
        if error:
            return error
        
        query = OKRGlobal.query.filter_by(company_id=company_id)
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
            
        okrs = query.all()
        return okrs_global_schema.dump(okrs), 200

    @permission_required('okrs', 'create')
    def post(self):
        try:
            data = request.get_json()
            company_id, error = _ensure_company_id()
            if error:
                return error
            data['company_id'] = company_id
            okr = okr_global_schema.load(data)
            db.session.add(okr)
            db.session.commit()
            return okr_global_schema.dump(okr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class OKRGlobalResource(Resource):
    @permission_required('okrs', 'view')
    def get(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRGlobal.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        return okr_global_schema.dump(okr), 200

    @permission_required('okrs', 'edit')
    def put(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRGlobal.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        try:
            data = request.get_json()
            data['company_id'] = company_id
            okr = okr_global_schema.load(data, instance=okr, partial=True)
            db.session.commit()
            return okr_global_schema.dump(okr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('okrs', 'delete')
    def delete(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRGlobal.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        try:
            db.session.delete(okr)
            db.session.commit()
            return {"message": "OKR deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class KeyResultListResource(Resource):
    @permission_required('okrs', 'edit')
    def post(self):
        try:
            data = request.get_json()
            company_id, error = _ensure_company_id()
            if error:
                return error
            data.pop('company_id', None)
            parent_error = _validate_global_okr_parent(data, company_id)
            if parent_error:
                return {"errors": parent_error}, 400
            kr = key_result_schema.load(data)
            db.session.add(kr)
            db.session.commit()
            return key_result_schema.dump(kr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class KeyResultResource(Resource):
    @permission_required('okrs', 'edit')
    def delete(self, kr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        kr = _tenant_key_result_or_404(kr_id, company_id)
        db.session.delete(kr)
        db.session.commit()
        return {"message": "KR deleted successfully"}, 200

    @permission_required('okrs', 'edit')
    def put(self, kr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        kr = _tenant_key_result_or_404(kr_id, company_id)
        try:
            data = request.get_json()
            data.pop('company_id', None)
            if 'okr_global_id' in data:
                parent_error = _validate_global_okr_parent(data, company_id)
                if parent_error:
                    return {"errors": parent_error}, 400
            kr = key_result_schema.load(data, instance=kr, partial=True)
            db.session.commit()
            return key_result_schema.dump(kr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class OKRAreaListResource(Resource):
    @permission_required('okrs', 'view')
    def get(self):
        plan_id = request.args.get('plan_id', type=int)
        company_id, error = _ensure_company_id()
        if error:
            return error
        
        query = OKRArea.query.filter_by(company_id=company_id)
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
            
        okrs = query.all()
        return okrs_area_schema.dump(okrs), 200

    @permission_required('okrs', 'create')
    def post(self):
        try:
            data = request.get_json()
            company_id, error = _ensure_company_id()
            if error:
                return error
            data['company_id'] = company_id
            okr = okr_area_schema.load(data)
            db.session.add(okr)
            db.session.commit()
            return okr_area_schema.dump(okr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class OKRAreaResource(Resource):
    @permission_required('okrs', 'view')
    def get(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRArea.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        return okr_area_schema.dump(okr), 200

    @permission_required('okrs', 'edit')
    def put(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRArea.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        try:
            data = request.get_json()
            data['company_id'] = company_id
            okr = okr_area_schema.load(data, instance=okr, partial=True)
            db.session.commit()
            return okr_area_schema.dump(okr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('okrs', 'delete')
    def delete(self, okr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        okr = OKRArea.query.filter_by(id=okr_id, company_id=company_id).first_or_404()
        db.session.delete(okr)
        db.session.commit()
        return {"message": "Area OKR deleted successfully"}, 200


class KeyResultAreaListResource(Resource):
    @permission_required('okrs', 'edit')
    def post(self):
        try:
            data = request.get_json()
            company_id, error = _ensure_company_id()
            if error:
                return error
            data.pop('company_id', None)
            parent_error = _validate_area_okr_parent(data, company_id)
            if parent_error:
                return {"errors": parent_error}, 400
            kr = key_result_area_schema.load(data)
            db.session.add(kr)
            db.session.commit()
            return key_result_area_schema.dump(kr), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


class KeyResultAreaResource(Resource):
    @permission_required('okrs', 'edit')
    def put(self, kr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        kr = _tenant_key_result_area_or_404(kr_id, company_id)
        try:
            data = request.get_json()
            data.pop('company_id', None)
            if 'okr_area_id' in data:
                parent_error = _validate_area_okr_parent(data, company_id)
                if parent_error:
                    return {"errors": parent_error}, 400
            kr = key_result_area_schema.load(data, instance=kr, partial=True)
            db.session.commit()
            return key_result_area_schema.dump(kr), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('okrs', 'edit')
    def delete(self, kr_id):
        company_id, error = _ensure_company_id()
        if error:
            return error
        kr = _tenant_key_result_area_or_404(kr_id, company_id)
        db.session.delete(kr)
        db.session.commit()
        return {"message": "KR Area deleted successfully"}, 200
