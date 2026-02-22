"""
Company Schema - Marshmallow schema for Company model serialization/deserialization.
"""

from marshmallow import fields, validate, validates, ValidationError
from schemas import ma
from models import db
from models.company import Company


class CompanySchema(ma.SQLAlchemyAutoSchema):
    """
    Schema for Company model.
    Handles serialization and deserialization with validation.
    """

    class Meta:
        model = Company
        sqla_session = db.session
        load_instance = True
        include_fk = True
        dump_only = ("created_at", "updated_at")

    # Field validations
    name = fields.String(
        required=True,
        validate=validate.Length(
            min=1, max=200, error="Nome deve ter entre 1 e 200 caracteres"
        ),
    )

    client_code = fields.String(
        allow_none=True,
        validate=validate.Length(
            max=50, error="Código do cliente deve ter no máximo 50 caracteres"
        ),
    )

    description = fields.String(allow_none=True)
    legal_name = fields.String(allow_none=True)
    cnpj = fields.String(allow_none=True)
    city = fields.String(allow_none=True)
    state = fields.String(allow_none=True)
    coverage_physical = fields.String(allow_none=True)
    coverage_online = fields.String(allow_none=True)
    experience_total = fields.String(allow_none=True)
    experience_segment = fields.String(allow_none=True)
    mission = fields.String(allow_none=True)
    vision = fields.String(allow_none=True)
    values = fields.String(allow_none=True)

    segment = fields.String(
        allow_none=True,
        validate=validate.Length(
            max=100, error="Segmento deve ter no máximo 100 caracteres"
        ),
    )

    size = fields.String(
        allow_none=True,
        validate=validate.OneOf(
            ["Pequeno", "Médio", "Grande"],
            error="Tamanho deve ser: Pequeno, Médio ou Grande",
        ),
    )

    logo_primary = fields.String(allow_none=True)
    logo_secondary = fields.String(allow_none=True)
    logo_icon = fields.String(allow_none=True)

    # Computed fields
    logo_count = fields.Method("get_logo_count", dump_only=True)

    # Read-only fields
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)

    def get_logo_count(self, obj):
        """Calculate number of logos configured."""
        return obj.logo_count

    @validates("client_code")
    def validate_client_code(self, value):
        """Ensure client_code is unique if provided."""
        if value:
            existing = Company.query.filter(
                Company.client_code == value,
                Company.id != (self.instance.id if self.instance else None),
            ).first()

            if existing:
                raise ValidationError(f"Código do cliente '{value}' já está em uso")


# Schema instances
company_schema = CompanySchema()
companies_schema = CompanySchema(many=True)
