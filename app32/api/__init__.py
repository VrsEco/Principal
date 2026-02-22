"""
API package for APP32.
Contains Flask-RESTful resources for REST APIs.
"""

from flask_restful import Api

api = Api()

# Import resources here
from .resources.company import CompanyListResource, CompanyResource

# Register resources
def register_resources(api):
    """Register all API resources."""
    api.add_resource(CompanyListResource, '/api/companies')
    api.add_resource(CompanyResource, '/api/companies/<int:company_id>')

__all__ = ['api', 'register_resources']
