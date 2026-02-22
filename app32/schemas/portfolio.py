"""Portfolio schema for API serialization"""
from marshmallow import Schema, fields, validate


class PortfolioSchema(Schema):
    """Schema for Portfolio model"""

    id = fields.Int(dump_only=True)
    company_id = fields.Int(required=True)
    code = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    responsible_id = fields.Int(allow_none=True)
    responsible_name = fields.Str(dump_only=True, allow_none=True)
    notes = fields.Str(allow_none=True)
    project_count = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PortfolioCreateSchema(Schema):
    """Schema for creating a portfolio"""

    code = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    responsible_id = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)


class PortfolioUpdateSchema(Schema):
    """Schema for updating a portfolio"""

    code = fields.Str(validate=validate.Length(min=1, max=100))
    name = fields.Str(validate=validate.Length(min=1, max=200))
    responsible_id = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)
