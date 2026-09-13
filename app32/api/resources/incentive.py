from flask_restful import Resource
from flask import request, session
import logging
from datetime import datetime
from sqlalchemy import or_
logger = logging.getLogger(__name__)
from services.incentive_service import IncentiveService
from services.incentive_access_service import IncentiveAccessService
from models import Indicator, IncentiveRuleSet, IncentiveCalculation, db
from datetime import date


def _authorized_company(action):
    """Return the session company only when the actor can use it for ``action``."""
    company_id = session.get('active_company_id')
    try:
        company_id = int(company_id)
    except (TypeError, ValueError):
        return None, ({"error": "No company active"}, 400)

    if not IncentiveAccessService.is_allowed(company_id, action):
        return None, ({"error": "Permission denied"}, 403)

    return company_id, None

class IncentiveIndicatorListResource(Resource):
    def get(self):
        company_id, error = _authorized_company('view')
        if error:
            return error
        
        indicators = Indicator.query.filter_by(company_id=company_id).all()
        return [
            {
                "id": i.id,
                "code": i.code,
                "name": i.name,
                "type": i.indicator_type,
                "source": i.source_module
            } for i in indicators
        ]

class IncentiveCalculationResource(Resource):
    def post(self):
        company_id, error = _authorized_company('approve')
        if error:
            return error

        data = request.get_json(silent=True) or {}
        try:
            rule_set_id = int(data.get('rule_set_id'))
            start_date = date.fromisoformat(data.get('start_date'))
            end_date = date.fromisoformat(data.get('end_date'))
        except (TypeError, ValueError):
            return {"error": "rule_set_id e período ISO são obrigatórios"}, 400

        if not IncentiveService.get_rule_set(company_id, rule_set_id):
            # Do not disclose whether a rule set exists in another tenant.
            return {"error": "Plano de incentivo não encontrado"}, 404
        
        logger.info(f"Triggering calculation for Company {company_id}, Plan {rule_set_id} ({data.get('start_date')} to {data.get('end_date')})")
        
        # Trigger harvesting before calculation
        IncentiveService.harvest_all_modules(company_id, start_date, end_date)
        
        result = IncentiveService.calculate_incentive(company_id, rule_set_id, start_date, end_date)
        return result

class IncentiveSpiderWebResource(Resource):
    def get(self):
        company_id, error = _authorized_company('view')
        if error:
            return error

        from services.incentive_spider_web_service import IncentiveSpiderWebService

        return IncentiveSpiderWebService.build_graph(int(company_id))


class IncentiveRuleResource(Resource):
    def get(self, rule_set_id):
        company_id, error = _authorized_company('view')
        if error:
            return error
        from models import IncentiveRule, Indicator

        if not IncentiveService.get_rule_set(company_id, rule_set_id):
            return {"error": "Plano de incentivo não encontrado"}, 404

        rules = db.session.query(
            IncentiveRule, Indicator.name
        ).join(
            Indicator, Indicator.id == IncentiveRule.indicator_id
        ).filter(
            IncentiveRule.rule_set_id == rule_set_id,
            or_(
                IncentiveRule.company_id == company_id,
                IncentiveRule.company_id.is_(None),
            ),
            Indicator.company_id == company_id,
            IncentiveRule.deleted_at.is_(None),
        ).order_by(IncentiveRule.order_index).all()
        
        return [
            {
                "id": r.IncentiveRule.id,
                "indicator_id": r.IncentiveRule.indicator_id,
                "indicator_name": r.name,
                "weight": float(r.IncentiveRule.weight or 0),
                "target": float(r.IncentiveRule.target_value or 0),
                "cap": float(r.IncentiveRule.max_cap or 0),
                "impact_type": r.IncentiveRule.impact_type
            } for r in rules
        ]

    def post(self, rule_set_id):
        company_id, error = _authorized_company('configure')
        if error:
            return error
        data = request.get_json(silent=True) or {}
        rules_data = data.get('rules', [])
        if not isinstance(rules_data, list):
            return {"error": "rules deve ser uma lista"}, 400

        from models import IncentiveRule, IncentiveRuleSet
        
        # Verify ownership
        rs = IncentiveRuleSet.query.filter(
            IncentiveRuleSet.id == rule_set_id,
            IncentiveRuleSet.company_id == company_id,
            IncentiveRuleSet.deleted_at.is_(None),
        ).first()
        if not rs:
            return {"error": "Plano de incentivo não encontrado"}, 404

        try:
            indicator_ids = [int(rule_data['indicator_id']) for rule_data in rules_data]
        except (KeyError, TypeError, ValueError):
            return {"error": "Cada regra exige indicator_id válido"}, 400

        if indicator_ids:
            owned_indicators = Indicator.query.filter(
                Indicator.company_id == company_id,
                Indicator.id.in_(indicator_ids),
            ).count()
            if owned_indicators != len(set(indicator_ids)):
                return {"error": "Indicador não encontrado"}, 404
            
        IncentiveRule.query.filter(
            IncentiveRule.rule_set_id == rule_set_id,
            or_(
                IncentiveRule.company_id == company_id,
                IncentiveRule.company_id.is_(None),
            ),
            IncentiveRule.deleted_at.is_(None),
        ).update({"deleted_at": datetime.utcnow()}, synchronize_session=False)
        
        for idx, r_data in enumerate(rules_data):
            rule = IncentiveRule(
                rule_set_id=rule_set_id,
                indicator_id=int(r_data['indicator_id']),
                weight=r_data.get('weight', 1.0),
                target_value=r_data.get('target'),
                max_cap=r_data.get('cap'),
                impact_type=r_data.get('impact_type', 'multiplier'),
                order_index=idx,
                company_id=company_id # Added explicitly
            )
            db.session.add(rule)
            
        db.session.commit()
        return {"success": True, "count": len(rules_data)}
