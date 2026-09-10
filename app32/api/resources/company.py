"""
Company API Resources - REST endpoints for Company CRUD operations.
"""

from flask import request
import logging
from flask_login import current_user
from flask_restful import Resource
from marshmallow import ValidationError
from utils.permissions import is_platform_admin, permission_required
from models import db, Company, Employee
from schemas.company import company_schema, companies_schema

logger = logging.getLogger(__name__)
PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


class CompanyListResource(Resource):
    """
    Resource for Company collection operations.
    
    GET /api/companies - List companies (filtered by is_active=True by default)
    POST /api/companies - Create a new company
    """
    
    @permission_required('companies', 'view')
    def get(self):
        """
        List companies.
        
        Query Params:
            all (bool): If true, returns all companies including inactive ones.
        
        Returns:
            200: List of companies
        """
        include_all = request.args.get('all', 'false').lower() == 'true'

        query = Company.query
        if not include_all:
            query = query.filter_by(is_active=True)

        if current_user.is_authenticated and not is_platform_admin():
            linked_company_ids = [
                row.company_id
                for row in Employee.query.with_entities(Employee.company_id)
                .filter(Employee.user_id == current_user.id)
                .filter(db.or_(Employee.status.is_(None), Employee.status == 'active'))
                .distinct()
                .all()
                if row.company_id is not None
            ]

            if not linked_company_ids:
                return [], 200

            query = query.filter(Company.id.in_(linked_company_ids))

        companies = query.order_by(Company.name).all()
        return companies_schema.dump(companies), 200
    
    @permission_required('companies', 'create')
    def post(self):
        """
        Create a new company.
        
        Request Body:
            {
                "name": "Company Name",
                "client_code": "CODE123",
                "description": "Description",
                "segment": "Technology",
                "size": "Médio"
            }
        
        Returns:
            201: Created company
            400: Validation error
        """
        try:
            data = request.get_json()
            company = company_schema.load(data)
            
            db.session.add(company)
            db.session.commit()
            
            return company_schema.dump(company), 201
            
        except ValidationError as err:
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': PUBLIC_ERROR_MESSAGE}, 500


class CompanyResource(Resource):
    """
    Resource for individual Company operations.
    
    GET /api/companies/<id> - Get company by ID
    PUT /api/companies/<id> - Update company
    DELETE /api/companies/<id> - Delete company (soft delete)
    """
    
    @permission_required('companies', 'view')
    def get(self, company_id):
        """
        Get company by ID (including inactive).
        
        Args:
            company_id: Company ID
        
        Returns:
            200: Company data
            404: Company not found
        """
        # Removemos o filtro de is_active=True para permitir visualizar/editar inativas
        company = Company.query.filter_by(id=company_id).first()
        
        if not company:
            return {'error': 'Empresa não encontrada'}, 404
        
        return company_schema.dump(company), 200
    
    @permission_required('companies', 'edit')
    def put(self, company_id):
        """
        Update company.
        
        Args:
            company_id: Company ID
        
        Returns:
            200: Updated company
            404: Company not found
            400: Validation error
        """
        company = Company.query.filter_by(id=company_id).first()
        
        if not company:
            return {'error': 'Empresa não encontrada'}, 404
        
        try:
            data = request.get_json()
            logger.info("Atualizando company_id=%s", company_id)
            
            company = company_schema.load(data, instance=company, partial=True)
            db.session.commit()
            
            logger.info("Company company_id=%s atualizada com sucesso", company_id)
            return company_schema.dump(company), 200
            
        except ValidationError as err:
            logger.warning("Erro de validação ao atualizar company_id=%s: %s", company_id, err.messages)
            return {'errors': err.messages}, 400
        except Exception as e:
            logger.exception("Erro inesperado ao atualizar company_id=%s", company_id)
            db.session.rollback()
            return {'error': PUBLIC_ERROR_MESSAGE}, 500
    
    @permission_required('companies', 'delete')
    def delete(self, company_id):
        """
        Delete company (soft delete).
        
        Args:
            company_id: Company ID
        
        Returns:
            204: Company deleted
            404: Company not found
        """
        company = Company.query.filter_by(id=company_id).first()
        
        if not company:
            return {'error': 'Empresa não encontrada'}, 404
        
        try:
            company.is_active = False  # Soft delete
            db.session.commit()
            
            return '', 204
            
        except Exception as e:
            db.session.rollback()
            return {'error': PUBLIC_ERROR_MESSAGE}, 500
