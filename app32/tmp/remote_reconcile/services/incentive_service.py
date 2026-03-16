import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import func
from models import (
    db, Indicator, IncentiveRuleSet, IncentiveRule,
    IndicatorData, IndicatorGoal, IncentiveCalculation,
    Project, ProcessInstance, Occurrence, Employee, Role, IncentiveParticipant
)

logger = logging.getLogger(__name__)

class IncentiveService:
    """
    Core Service for the Incentive System (Onda 1B)
    Handles Fact Harvesting, Calculation Pipeline and Governance.
    Now leveraging the independent Indicator model.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # SCORE HARVESTERS — lê pontuação obtida/possível do sistema nativo
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _upsert_fact(company_id, indicator_id, employee_id, period_start, period_end,
                     value, evidence):
        """Cria ou atualiza um IndicatorData (substitui IncentiveFact)."""
        data_record = IndicatorData.query.filter_by(
            company_id=company_id, indicator_id=indicator_id,
            employee_id=employee_id, period_start=period_start, period_end=period_end
        ).first()
        if not data_record:
            data_record = IndicatorData(
                company_id=company_id, indicator_id=indicator_id,
                employee_id=employee_id, period_start=period_start, period_end=period_end,
                measured_date=period_end # Assumed as reference date
            )
            db.session.add(data_record)
        data_record.measured_value = Decimal(str(round(value, 4)))
        data_record.evidence_payload = evidence
        return data_record

    @staticmethod
    def harvest_process_facts(company_id: int, period_start: date, period_end: date):
        indicators = Indicator.query.filter_by(
            company_id=company_id, source_module='processo', is_active=True
        ).all()
        # fallback for 'process' slug
        indicators += Indicator.query.filter_by(
            company_id=company_id, source_module='process', is_active=True
        ).all()

        for ind in indicators:
            q = ProcessInstance.query.filter(
                ProcessInstance.company_id == company_id,
                ProcessInstance.status == 'completed',
                func.cast(ProcessInstance.completed_at, sa.Date) >= period_start,
                func.cast(ProcessInstance.completed_at, sa.Date) <= period_end,
            )
            if ind.source_id:
                q = q.filter(ProcessInstance.process_id == ind.source_id)
            instances = q.all()

            by_emp: Dict[int, list] = {}
            for inst in instances:
                emp = inst.executor_id or inst.responsible_id or inst.owner_employee_id
                if emp:
                    by_emp.setdefault(emp, []).append(inst)

            for emp_id, insts in by_emp.items():
                agg = ind.aggregation_function or 'score_ratio'
                if agg == 'score_ratio':
                    possible = sum(float(i.score_weight or 1) for i in insts)
                    obtained = sum(
                        float(i.score_weight or 1) * (0.5 if (i.due_date and i.completed_at and (i.completed_at.date() if isinstance(i.completed_at, datetime) else i.completed_at) > (i.due_date.date() if isinstance(i.due_date, datetime) else i.due_date)) else 1.0)
                        for i in insts
                    )
                    value = (obtained / possible) if possible > 0 else 0.0
                elif agg == 'count':
                    value = float(len(insts))
                else:  # sum
                    value = float(sum(float(i.score_weight or 1) for i in insts))

                IncentiveService._upsert_fact(
                    company_id, ind.id, emp_id, period_start, period_end, value,
                    {"module": "processo", "instances": len(insts),
                     "source_id": ind.source_id, "aggregation": agg}
                )

        db.session.commit()

    @staticmethod
    def harvest_project_facts(company_id: int, period_start: date, period_end: date):
        from models import ProjectTask
        indicators = Indicator.query.filter_by(
            company_id=company_id, source_module='projeto', is_active=True
        ).all()
        indicators += Indicator.query.filter_by(
            company_id=company_id, source_module='project', is_active=True
        ).all()

        proj_ids = [p.id for p in Project.query.filter_by(company_id=company_id).all()]
        if not proj_ids:
            return

        for ind in indicators:
            q = ProjectTask.query.filter(
                ProjectTask.project_id.in_(proj_ids),
                ProjectTask.status == 'completed',
            )
            if ind.source_id:
                q = q.filter(ProjectTask.project_id == ind.source_id)
            if period_start:
                q = q.filter(func.coalesce(ProjectTask.completion_date, ProjectTask.due_date) >= period_start)
            if period_end:
                q = q.filter(func.coalesce(ProjectTask.completion_date, ProjectTask.due_date) <= period_end)
            tasks = q.all()

            by_emp: Dict[int, list] = {}
            for t in tasks:
                if t.employee_id:
                    by_emp.setdefault(t.employee_id, []).append(t)

            for emp_id, emp_tasks in by_emp.items():
                agg = ind.aggregation_function or 'score_ratio'
                if agg == 'score_ratio':
                    possible = sum(float(t.score_weight or 1) for t in emp_tasks)
                    obtained = sum(
                        float(t.score_weight or 1) * (0.5 if (t.due_date and t.completion_date and (t.completion_date.date() if isinstance(t.completion_date, datetime) else t.completion_date) > (t.due_date.date() if isinstance(t.due_date, datetime) else t.due_date)) else 1.0)
                        for t in emp_tasks
                    )
                    value = (obtained / possible) if possible > 0 else 0.0
                elif agg == 'count':
                    value = float(len(emp_tasks))
                else:
                    value = float(sum(float(t.score_weight or 1) for t in emp_tasks))

                IncentiveService._upsert_fact(
                    company_id, ind.id, emp_id, period_start, period_end, value,
                    {"module": "projeto", "tasks": len(emp_tasks),
                     "source_id": ind.source_id, "aggregation": agg}
                )

        db.session.commit()

    @staticmethod
    def harvest_occurrence_facts(company_id: int, period_start: date, period_end: date):
        indicators = Indicator.query.filter_by(
            company_id=company_id, source_module='ocorrencia', is_active=True
        ).all()
        indicators += Indicator.query.filter_by(
            company_id=company_id, source_module='occurrence', is_active=True
        ).all()

        for ind in indicators:
            max_per_period = float((ind.description or "").find("max:") != -1 and 10 or 10) # Placeholder logic

            q = db.session.query(
                Occurrence.employee_id,
                func.count(Occurrence.id).label('cnt'),
                func.coalesce(func.sum(Occurrence.score), 0).label('total_score')
            ).filter(
                Occurrence.company_id == company_id,
                sa.cast(Occurrence.created_at, sa.Date) >= period_start,
                sa.cast(Occurrence.created_at, sa.Date) <= period_end,
            ).group_by(Occurrence.employee_id)

            for emp_id, cnt, total_score in q.all():
                if not emp_id:
                    continue
                agg = ind.aggregation_function or 'count'
                if agg == 'score_ratio':
                    value = max(0.0, 1.0 - (cnt / max_per_period))
                elif agg == 'sum':
                    value = float(total_score)
                else:
                    value = float(cnt)

                IncentiveService._upsert_fact(
                    company_id, ind.id, emp_id, period_start, period_end, value,
                    {"module": "ocorrencia", "count": cnt,
                     "total_score": float(total_score), "aggregation": agg}
                )
        db.session.commit()

    @staticmethod
    def harvest_manual_pending(company_id: int, period_start: date, period_end: date) -> list:
        manual_inds = Indicator.query.filter_by(
            company_id=company_id, collection_mode='manual', is_active=True
        ).all()
        pending = []
        for ind in manual_inds:
            count = IndicatorData.query.filter_by(
                company_id=company_id, indicator_id=ind.id,
                period_start=period_start, period_end=period_end
            ).count()
            if count == 0:
                pending.append({
                    "indicator_id": ind.id,
                    "indicator_name": ind.name,
                    "indicator_code": ind.code,
                    "unit": ind.unit,
                })
        return pending

    @classmethod
    def harvest_all_modules(cls, company_id: int, period_start: date, period_end: date) -> dict:
        logger.info(f"[Harvest] Iniciando · company={company_id} · {period_start}→{period_end}")
        summary: Dict[str, int] = {"processo": 0, "projeto": 0, "ocorrencia": 0, "manual_pendente": 0}

        auto_inds = Indicator.query.filter_by(
            company_id=company_id, collection_mode='auto_interno', is_active=True
        ).all()
        modules_to_run = {ind.source_module for ind in auto_inds}

        def count_facts():
            return IndicatorData.query.filter_by(
                company_id=company_id, period_start=period_start, period_end=period_end
            ).count()

        if modules_to_run & {'processo', 'process'}:
            before = count_facts()
            cls.harvest_process_facts(company_id, period_start, period_end)
            summary["processo"] = count_facts() - before

        if modules_to_run & {'projeto', 'project'}:
            before = count_facts()
            cls.harvest_project_facts(company_id, period_start, period_end)
            summary["projeto"] = count_facts() - before

        if modules_to_run & {'ocorrencia', 'occurrence'}:
            before = count_facts()
            cls.harvest_occurrence_facts(company_id, period_start, period_end)
            summary["ocorrencia"] = count_facts() - before

        pending = cls.harvest_manual_pending(company_id, period_start, period_end)
        summary["manual_pendente"] = len(pending)

        total = summary["processo"] + summary["projeto"] + summary["ocorrencia"]
        logger.info(f"[Harvest] Concluído · fatos={total} · pendentes_manual={len(pending)}")
        return {"summary": summary, "manual_pending": pending}

    @staticmethod
    def calculate_incentive(company_id: int, rule_set_id: int, period_start: date, period_end: date):
        rule_set = IncentiveRuleSet.query.get(rule_set_id)
        if not rule_set or rule_set.company_id != company_id:
            return {"error": "Plano de Incentivo inválido"}

        rules = IncentiveRule.query.filter_by(rule_set_id=rule_set_id).order_by(IncentiveRule.order_index).all()
        participants = IncentiveParticipant.query.filter_by(
            rule_set_id=rule_set_id, company_id=company_id, elegivel=True
        ).all()

        if not participants:
            return {"error": "Nenhum participante elegível configurado para este plano."}

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
            if not emp: continue

            base_bonus = Decimal(str(part.valor_base or 0))
            total_base_discounts = Decimal('0.00')
            sum_multipliers = Decimal('0.00')
            sum_reductions = Decimal('0.00')
            bloqueado = False
            
            steps = []
            
            for rule in rules:
                emp_filter = emp.id if rule.incidencia == 'individual' else None
                
                # Retrieval from the unified IndicatorData table
                data_record = IndicatorData.query.filter_by(
                    company_id=company_id,
                    indicator_id=rule.indicator_id,
                    employee_id=emp_filter,
                    period_start=period_start,
                    period_end=period_end
                ).first()
                
                realized = data_record.measured_value if data_record else Decimal('0.00')
                target = rule.target_value or Decimal('1.00')
                impact = rule.impact_value or Decimal('0.00')

                achievement = (realized / target) if target > 0 else Decimal('0.00')

                if rule.max_cap and achievement > rule.max_cap:
                    achievement = rule.max_cap

                if rule.vetor_type == 'desconto_base':
                    contribution = achievement * impact
                    total_base_discounts += contribution
                    display_contribution = -contribution
                
                elif rule.vetor_type == 'bloqueador':
                    piso = rule.min_threshold or Decimal('0.00')
                    if realized < piso:
                        bloqueado = True
                    contribution = Decimal('0.00')
                    display_contribution = contribution

                elif rule.vetor_type == 'redutor':
                    penalty_factor = max(Decimal('0.00'), Decimal('1.00') - achievement)
                    contribution = impact * penalty_factor
                    if rule.max_reduction and contribution > rule.max_reduction:
                        contribution = rule.max_reduction
                    sum_reductions += contribution
                    display_contribution = -contribution
                
                else: # multiplicador / bonus
                    contribution = impact * achievement
                    sum_multipliers += contribution
                    display_contribution = contribution

                steps.append({
                    "rule_id": rule.id,
                    "indicator_id": rule.indicator_id,
                    "indicator_name": rule.indicator.name,
                    "vetor_type": rule.vetor_type,
                    "impact": float(impact),
                    "realized": float(realized),
                    "target": float(target),
                    "achievement": float(achievement),
                    "contribution": float(display_contribution),
                    "blocked": bloqueado
                })

            final_base = max(Decimal('0.00'), base_bonus - total_base_discounts)
            sum_multipliers = max(Decimal('1.00'), sum_multipliers)
            
            if rule_set.max_red_total is not None and sum_reductions > rule_set.max_red_total:
                sum_reductions = rule_set.max_red_total
                
            unclamped_multiplier = sum_multipliers - sum_reductions
            final_multiplier = max(Decimal('0.00'), unclamped_multiplier)
            
            if bloqueado:
                final_multiplier = Decimal('0.00')

            unclamped_bonus = final_base * unclamped_multiplier
            final_bonus = final_base * final_multiplier
            
            participant_result = {
                "participant_id": part.id,
                "employee_id": emp.id,
                "name": emp.name,
                "base_value": str(final_base),
                "base_target": str(final_base),
                "total_score": float(final_multiplier),
                "bonus": str(final_bonus.quantize(Decimal('0.01'))),
                "unclamped_bonus": str(unclamped_bonus.quantize(Decimal('0.01'))),
                "unclamped_multiplier": float(unclamped_multiplier),
                "sum_multipliers": float(sum_multipliers),
                "sum_reductions": float(sum_reductions),
                "steps": steps,
                "bloqueado": bloqueado
            }
            results.append(participant_result)
            total_distributed += final_bonus

        calc.total_distributed = total_distributed
        calc.participants_count = len(results)
        calc.status = 'calculated'
        calc.results_payload = {"participants": results}
        
        db.session.commit()
        return {
            "calculation_id": calc.id,
            "total_payout": str(total_distributed.quantize(Decimal('0.01'))),
            "participants": results
        }

    @staticmethod
    def get_governability_report(company_id: int):
        # Simplificando governabilidade para olhar direto para indicadores vinculados a regras
        # (A Matriz de Governabilidade legada será unificada gradualmente)
        rules = db.session.query(
            IncentiveRule, Indicator.name, Role.title
        ).join(Indicator, Indicator.id == IncentiveRule.indicator_id
        ).join(IncentiveRuleSet, IncentiveRuleSet.id == IncentiveRule.rule_set_id
        ).filter(IncentiveRuleSet.company_id == company_id).all()
        
        report = []
        for rule, ind_name, role_title in rules:
             report.append({
                 "role": role_title,
                 "indicator": ind_name,
                 "level": "Direto" if rule.incidencia == 'individual' else "Indireto"
             })
        return report
