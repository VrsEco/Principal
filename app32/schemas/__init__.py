"""
Schemas package for APP32.
Contains Marshmallow schemas for serialization/deserialization.
"""

from flask_marshmallow import Marshmallow

ma = Marshmallow()

# Import schemas here
from .company import CompanySchema, company_schema, companies_schema
from .indicator import indicator_schema, indicators_schema, indicator_group_schema, indicator_groups_schema
from .occurrence import occurrence_schema, occurrences_schema

__all__ = [
    'ma', 'CompanySchema', 'company_schema', 'companies_schema',
    'indicator_schema', 'indicators_schema', 'indicator_group_schema', 'indicator_groups_schema',
    'occurrence_schema', 'occurrences_schema'
]
