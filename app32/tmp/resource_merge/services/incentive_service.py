import logging
from datetime import date
from decimal import Decimal
from typing import Dict

from sqlalchemy import text

from models import (
    db, Indicator, IncentiveRuleSet, IncentiveRule,
    IncentiveCalculation, Employee, Role, IncentiveParticipant,
)

logger = logging.getLogger(__name__)


class IncentiveService:
    """Serviço de incentivos compatível com o schema atual de produção."""

    @staticmethod
    def _to_decimal(value, default='0.00') -> Decimal:
        try:
            if value is None or value == '':
                return Decimal(default)
            return Decimal(str(value))
        except Exception:
            return Decimal(default)

    @staticmethod
    def _latest_realized(company_id: int, indicator_id: int, period_start: date, period_end: date) -> Decimal:
        row = db.session.execute(
            text(
                """
                SELECT d.value
                FROM indicator_data d
                JOIN indicator_goals g ON g.id = d.goal_id
                WHERE d.company_id = :company_id
                  AND g.company_id = :company_id
                  AND g.indicator_id = :indicator_id
                  AND (:period_start IS NULL OR d.record_date >= :period_start)
                  AND (:period_end IS NULL OR d.record_date <= :period_end)
                ORDER BY d.record_date DESC NULLS LAST, d.id DESC
                LIMIT 1
                """
            ),
            {
                'company_id': company_id,
                'indicator_id': indicator_id,
                'period_start': period_start,
                'period_end': period_end,
            }
        ).first()
        return IncentiveService._to_decimal(row[0] if row else None)

    @staticmethod
    def _goal_target(company_id: int, indicator_id: int, fallback=None) -> Decimal:
        row = db.session.execute(
            text(
                """
                SELECT g.goal_value
                FROM indicator_goals g
                WHERE g.company_id = :company_id
                  AND g.indicator_id = :indicator_id
                ORDER BY g.goal_date DESC NULLS LAST, g.id DESC
                LIMIT 1
                """
            ),
            {'company_id': company_id, 'indicator_id': indicator_id}
        ).first()
        if row and row[0] is not None:
            return IncentiveService._to_decimal(row[0], '1.00')
        return IncentiveService._to_decimal(fallback, '1.00')

    @staticmethod
    def harvest_process_facts(company_id: int, period_start: date, period_end: date):
        logger.info('[Harvest] processo compatível: leitura apenas, sem escrita no schema legado.')
        return 0

    @staticmethod
    def harvest_project_facts(company_id: int, period_start: date, period_end: date):
        logger.info('[Harvest] projeto compatível: leitura apenas, sem escrita no schema legado.')
        return 0

    @staticmethod
    def harvest_occurrence_facts(company_id: int, period_start: date, period_end: date):
        logger.info('[Harvest] ocorrência compatível: leitura apenas, sem escrita no schema legado.')
        return 0

    @staticmethod
    def harvest_manual_pending(company_id: int, period_start: date, period_end: date) -> list:
        manual_inds = Indicator.query.filter_by(
            company_id=company_id, collection_mode='manual', is_active=True
        ).all()
        pending = []
        for ind in manual_inds:
            count = db.session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM indicator_data d
                    JOIN indicator_goals g ON g.id = d.goal_id
                    WHERE d.company_id = :company_id
                      AND g.company_id = :company_id
                      AND g.indicator_id = :indicator_id
                      AND (:period_start IS NULL OR d.record_date >= :period_start)
                      AND (:period_end IS NULL OR d.record_date <= :period_end)
                    """
                ),
                {
                    'company_id': company_id,
                    'indicator_id': ind.id,
                    'period_start': period_start,
                    'period_end': period_end,
                }
            ).scalar() or 0
            if count == 0:
                pending.append({
                    'indicator_id': ind.id,
                    'indicator_name': ind.name,
                    'indicator_code': ind.code,
                    'unit': ind.unit,
                })
        return pending

    @classmethod
    def harvest_all_modules(cls, company_id: int, period_start: date, period_end: date) -> dict:
        logger.info(f"[Harvest] Compat company={company_id} {period_start}->{period_end}")
        summary: Dict[str, int] = {'processo': 0, 'projeto': 0, 'ocorrencia': 0, 'manual_pendente': 0}
        pending = cls.harvest_manual_pending(company_id, period_start, period_end)
        summary['manual_pendente'] = len(pending)
        return {'summary': summary, 'manual_pending': pending}

    @staticmethod
    def calculate_incentive(company_id: int, rule_set_id: int, period_start: date, period_end: date):
        rule_set = IncentiveRuleSet.query.get(rule_set_id)
        if not rule_set or rule_set.company_id != company_id:
            return {'error': 'Plano de Incentivo inválido'}

        rules = IncentiveRule.query.filter_by(rule_set_id=rule_set_id).order_by(IncentiveRule.order_index).all()
        participants = IncentiveParticipant.query.filter_by(
            rule_set_id=rule_set_id, company_id=company_id, elegivel=True
        ).all()

        if not participants:
            return {'error': 'Nenhum participante elegível configurado para este plano.'}

        calc = IncentiveCalculation(
            company_id=company_id,
            rule_set_id=rule_set_id,
            period_start=period_start,
            period_end=period_end,
            status='preview'
        )
        db.session.add(calc)
        db.session.flush()

        results = []
        total_distributed = Decimal('0.00')

        for part in participants:
            emp = part.employee
            if not emp:
                continue

            base_bonus = IncentiveService._to_decimal(part.valor_base)
            total_base_discounts = Decimal('0.00')
            sum_multipliers = Decimal('0.00')
            sum_reductions = Decimal('0.00')
            bloqueado = False
            steps = []

            for rule in rules:
                realized = IncentiveService._latest_realized(company_id, rule.indicator_id, period_start, period_end)
                target = IncentiveService._goal_target(company_id, rule.indicator_id, rule.target_value)
                if target <= 0:
                    target = Decimal('1.00')

                impact = IncentiveService._to_decimal(getattr(rule, 'impact_value', None) or rule.weight, '1.00')
                achievement = realized / target if target > 0 else Decimal('0.00')

                if rule.max_cap is not None and achievement > IncentiveService._to_decimal(rule.max_cap, '0.00'):
                    achievement = IncentiveService._to_decimal(rule.max_cap, '0.00')

                vetor_type = (rule.vetor_type or 'bonus').strip().lower()
                contribution = Decimal('0.00')
                display_contribution = Decimal('0.00')

                if vetor_type == 'desconto_base':
                    contribution = achievement * impact
                    total_base_discounts += contribution
                    display_contribution = -contribution
                elif vetor_type == 'bloqueador':
                    piso = IncentiveService._to_decimal(rule.min_threshold, '0.00')
                    if realized < piso:
                        bloqueado = True
                elif vetor_type == 'redutor':
                    penalty_factor = max(Decimal('0.00'), Decimal('1.00') - achievement)
                    contribution = impact * penalty_factor
                    sum_reductions += contribution
                    display_contribution = -contribution
                else:
                    contribution = impact * achievement
                    sum_multipliers += contribution
                    display_contribution = contribution

                steps.append({
                    'rule_id': rule.id,
                    'indicator_id': rule.indicator_id,
                    'indicator_name': rule.indicator.name if rule.indicator else None,
                    'vetor_type': vetor_type,
                    'impact': float(impact),
                    'realized': float(realized),
                    'target': float(target),
                    'achievement': float(achievement),
                    'contribution': float(display_contribution),
                    'blocked': bloqueado,
                })

            final_base = max(Decimal('0.00'), base_bonus - total_base_discounts)
            sum_multipliers = max(Decimal('1.00'), sum_multipliers)
            final_multiplier = Decimal('0.00') if bloqueado else max(Decimal('0.00'), sum_multipliers - sum_reductions)
            unclamped_multiplier = sum_multipliers - sum_reductions
            unclamped_bonus = final_base * unclamped_multiplier
            final_bonus = final_base * final_multiplier

            participant_result = {
                'participant_id': part.id,
                'employee_id': emp.id,
                'name': emp.name,
                'base_value': str(final_base.quantize(Decimal('0.01'))),
                'base_target': str(final_base.quantize(Decimal('0.01'))),
                'total_score': float(final_multiplier),
                'bonus': str(final_bonus.quantize(Decimal('0.01'))),
                'unclamped_bonus': str(unclamped_bonus.quantize(Decimal('0.01'))),
                'unclamped_multiplier': float(unclamped_multiplier),
                'sum_multipliers': float(sum_multipliers),
                'sum_reductions': float(sum_reductions),
                'steps': steps,
                'bloqueado': bloqueado,
            }
            results.append(participant_result)
            total_distributed += final_bonus

        calc.total_distributed = total_distributed
        calc.participants_count = len(results)
        calc.status = 'calculated'
        calc.results_payload = {'participants': results}
        db.session.commit()
        return {
            'calculation_id': calc.id,
            'total_payout': str(total_distributed.quantize(Decimal('0.01'))),
            'participants': results,
        }

    @staticmethod
    def get_governability_report(company_id: int):
        rules = db.session.query(
            IncentiveRule, Indicator.name, Role.title
        ).join(Indicator, Indicator.id == IncentiveRule.indicator_id
        ).join(IncentiveRuleSet, IncentiveRuleSet.id == IncentiveRule.rule_set_id
        ).filter(IncentiveRuleSet.company_id == company_id).all()

        report = []
        for rule, ind_name, role_title in rules:
            report.append({
                'role': role_title,
                'indicator': ind_name,
                'level': 'Direto' if rule.incidencia == 'individual' else 'Indireto'
            })
        return report
