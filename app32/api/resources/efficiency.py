from __future__ import annotations

from datetime import datetime

from flask import request
from flask_restful import Resource
from flask_login import current_user

from models import Employee
from services.efficiency_collaborators_service import get_efficiency_collaborators, parse_efficiency_period
from utils.permissions import has_company_full_access


class EfficiencyCollaborators(Resource):
    def get(self, company_id):
        start_raw = request.args.get("start_date")
        end_raw = request.args.get("end_date")

        def _parse(raw_value):
            if not raw_value:
                return None
            return datetime.strptime(raw_value, "%Y-%m-%d").date()

        start_date, end_date = parse_efficiency_period(
            start_date=_parse(start_raw),
            end_date=_parse(end_raw),
        )

        can_view_all = bool(current_user.is_authenticated and has_company_full_access(company_id))
        employee_ids = None
        if not can_view_all:
            if not current_user.is_authenticated:
                return []
            employee_ids = [
                int(employee.id)
                for employee in Employee.query.filter_by(company_id=company_id, user_id=current_user.id).all()
            ]

        return get_efficiency_collaborators(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            employee_ids=employee_ids,
        )
