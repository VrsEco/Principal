from marshmallow import fields
from models import db, OKRGlobal, KeyResult, OKRArea, KeyResultArea
from schemas import ma


class KeyResultSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = KeyResult
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class OKRGlobalSchema(ma.SQLAlchemyAutoSchema):
    key_results = fields.Nested(KeyResultSchema, many=True, dump_only=True)

    class Meta:
        model = OKRGlobal
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class KeyResultAreaSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = KeyResultArea
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class OKRAreaSchema(ma.SQLAlchemyAutoSchema):
    key_results = fields.Nested(KeyResultAreaSchema, many=True, dump_only=True)

    class Meta:
        model = OKRArea
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


# Schema instances
okr_global_schema = OKRGlobalSchema()
okrs_global_schema = OKRGlobalSchema(many=True)
key_result_schema = KeyResultSchema()
key_results_schema = KeyResultSchema(many=True)

okr_area_schema = OKRAreaSchema()
okrs_area_schema = OKRAreaSchema(many=True)
key_result_area_schema = KeyResultAreaSchema()
key_results_area_schema = KeyResultAreaSchema(many=True)
