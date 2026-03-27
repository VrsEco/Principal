import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import func
from utils.indicator_ranges import normalize_performance_ranges
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
    def _get_active_goal(company_id: int, indicator_id: int, reference_date: date) -> Optional[IndicatorGoal]:
        """Busca a meta ativa para o indicador no período da referência."""
        return IndicatorGoal.query.filter(
            IndicatorGoal.company_id == company_id,
            IndicatorGoal.indicator_id == indicator_id,
            IndicatorGoal.status == 'active',
            IndicatorGoal.period_start <= reference_date,
            IndicatorGoal.period_end >= reference_date
        ).first()

    @staticmethod
    def _calculate_achievement(realized: Decimal, target: Decimal, polarity: str = 'positive') -> Decimal:
        """Calcula o aproveitamento considerando a polaridade."""
        if target == 0:
            return Decimal('1.00') if realized == 0 else Decimal('0.00')
        
        if polarity == 'negative':
            # Para indicadores negativos (ex: reclamações), se realizado > meta, aproveitamento < 100%
            # Achievement = Target / Realized (simplificado) ou 1 + (Target - Realized) / Target
            if realized == 0: return Decimal('2.00') # Excelente desempenho
            return Decimal(str(target / realized))
        else:
            return Decimal(str(realized / target))

    @staticmethod
    def _upsert_fact(company_id, indicator_id, employee_id, period_start, period_end,
                     value, evidence):
        """Cria ou atualiza um IndicatorData (substitui IncentiveFact)."""
        data_record = IndicatorData.query.filter_by(
            company_id=company_id, indicator_id=indicator_id,
            employee_id=employee_id, period_start=period_start, period_end=period_end
        ).first()
        
        if not data_record:
            # Tentar associar com a Meta (novo padrão)
            goal = IncentiveService._get_active_goal(company_id, indicator_id, period_end)
            data_record = IndicatorData(
                company_id=company_id, indicator_id=indicator_id,
                goal_id=goal.id if goal else None,
                employee_id=employee_id, period_start=period_start, period_end=period_end,
                measured_date=period_end,
                status='verified',
                is_manual=False
            )
            db.session.add(data_record)
        
        # Proteção contra sobrescrita de dados manuais
        if data_record.is_manual or data_record.status == 'manual_override':
            logger.info(f"Skipping update for manual record {data_record.id}")
            return data_record
            
        data_record.measured_value = Decimal(str(round(value, 4)))
        data_record.evidence_payload = evidence
        return data_record

    @staticmethod
    def harvest_process_facts(company_id: int, period_start: date, period_end: date):
        indicators = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.source_module.in_(['processo', 'process']),
            Indicator.is_active == True
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
                elif agg == 'avg':
                    value = float(sum(float(i.score_weight or 0) for i in insts) / len(insts))
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
        indicators = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.source_module.in_(['projeto', 'project']),
            Indicator.is_active == True
        ).all()

        proj_ids = [p.id for p in Project.query.filter_by(company_id=company_id).all()]
        if not proj_ids: return

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
        indicators = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.source_module.in_(['ocorrencia', 'occurrence']),
            Indicator.is_active == True
        ).all()

        for ind in indicators:
            # Polaridade automática para ocorrências se não definida
            if not ind.polarity: ind.polarity = 'negative'
            
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
                if not emp_id: continue
                agg = ind.aggregation_function or 'count'
                if agg == 'sum':
                    value = float(total_score)
                else:
                    value = float(cnt)

                IncentiveService._upsert_fact(
                    company_id, ind.id, emp_id, period_start, period_end, value,
                    {"module": "ocorrencia", "count": cnt,
                     "total_score": float(total_score), "aggregation": agg}
                )
        db.session.commit()

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
        logger.info(f"[Harvest] Concluído · fatos={total}")
        return {"summary": summary, "manual_pending": pending}

    @staticmethod
    def calculate_incentive(company_id: int, rule_set_id: int, period_start: date, period_end: date):
        rule_set = IncentiveService.get_rule_set(company_id, rule_set_id)
        if not rule_set:
            return {"error": "Plano de Incentivo inválido"}

        rules = IncentiveService.get_active_rules_query(
            company_id, rule_set_id
        ).order_by(IncentiveRule.order_index).all()
        participants = IncentiveService.get_active_participants_query(
            company_id, rule_set_id
        ).filter(IncentiveParticipant.elegivel == True).all()

        if not participants:
            return {"error": "Nenhum participante elegível configurado."}

        calc = IncentiveCalculation(
            company_id=company_id, rule_set_id=rule_set_id,
            period_start=period_start, period_end=period_end, status='preview'
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
                ind = rule.indicator
                emp_filter = emp.id if rule.incidencia == 'individual' else None
                
                # Retrieval from IndicatorData
                data_record = IndicatorData.query.filter_by(
                    company_id=company_id, indicator_id=rule.indicator_id,
                    employee_id=emp_filter, period_start=period_start, period_end=period_end
                ).first()
                
                realized = data_record.measured_value if data_record else Decimal('0.00')
                
                # DYNAMIC GOAL SELECTION
                goal = None
                if rule.use_indicator_goal:
                    goal = IncentiveService._get_active_goal(company_id, rule.indicator_id, period_end)
                
                target = Decimal(str(goal.goal_value if goal else (rule.target_value or 1.0)))
                impact = rule.impact_value or Decimal('0.00')
                polarity = ind.polarity or 'positive'

                achievement = IncentiveService._calculate_achievement(realized, target, polarity)

                # RANGE BASED CALCULATION
                if rule.calculation_mode == 'ranges' and goal and goal.performance_ranges:
                    ranges = normalize_performance_ranges(goal.performance_ranges)
                    red = Decimal(str(ranges.get('red', 80))) / 100
                    yellow = Decimal(str(ranges.get('yellow', 90))) / 100
                    green = Decimal(str(ranges.get('green', 110))) / 100
                    
                    # Logic: if achievement < red -> multiplier = 0?
                    # This depends on business logic, keeping linear for now but aware of ranges
                    if achievement < red: achievement = achievement * Decimal('0.5')
                
                if rule.max_cap and achievement > rule.max_cap:
                    achievement = rule.max_cap

                display_contribution = Decimal('0.00')
                if rule.vetor_type == 'desconto_base':
                    contribution = achievement * impact
                    total_base_discounts += contribution
                    display_contribution = -contribution
                
                elif rule.vetor_type == 'bloqueador':
                    piso = Decimal(str(rule.min_threshold or 0.0))
                    if realized < piso: bloqueado = True
                
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
                    "indicator_name": ind.name,
                    "vetor_type": rule.vetor_type,
                    "impact": float(impact),
                    "realized": float(realized),
                    "target": float(target),
                    "achievement": float(achievement),
                    "contribution": float(display_contribution),
                    "blocked": bloqueado,
                    "goal_id": goal.id if goal else None,
                    "is_manual": data_record.is_manual if data_record else False
                })

            final_base = max(Decimal('0.00'), base_bonus - total_base_discounts)
            sum_multipliers = max(Decimal('1.00'), sum_multipliers)
            
            if rule_set.max_red_total is not None and sum_reductions > rule_set.max_red_total:
                sum_reductions = rule_set.max_red_total
                
            unclamped_multiplier = sum_multipliers - sum_reductions
            final_multiplier = max(Decimal('0.00'), unclamped_multiplier)
            if bloqueado: final_multiplier = Decimal('0.00')

            final_bonus = final_base * final_multiplier
            
            results.append({
                "participant_id": part.id, "employee_id": emp.id, "name": emp.name,
                "base_value": str(final_base), "total_score": float(final_multiplier),
                "bonus": str(final_bonus.quantize(Decimal('0.01'))),
                "steps": steps, "bloqueado": bloqueado
            })
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
        rules = db.session.query(
            IncentiveRule, Indicator.name, Role.title
        ).join(Indicator, Indicator.id == IncentiveRule.indicator_id
        ).join(IncentiveRuleSet, IncentiveRuleSet.id == IncentiveRule.rule_set_id
        ).outerjoin(IncentiveParticipant, IncentiveParticipant.rule_set_id == IncentiveRuleSet.id
        ).outerjoin(Employee, Employee.id == IncentiveParticipant.employee_id
        ).outerjoin(Role, Role.id == Employee.role_id
        ).filter(
            IncentiveRuleSet.company_id == company_id,
            IncentiveRuleSet.deleted_at.is_(None),
            IncentiveRule.deleted_at.is_(None),
            sa.or_(
                IncentiveParticipant.id.is_(None),
                IncentiveParticipant.deleted_at.is_(None),
            ),
        ).all()
        
        report = []
        seen = set()
        for rule, ind_name, role_title in rules:
             key = (role_title, ind_name)
             if key not in seen:
                 report.append({
                     "role": role_title or "N/A",
                     "indicator": ind_name,
                     "level": "Direto" if rule.incidencia == 'individual' else "Indireto"
                 })
                 seen.add(key)
        return report

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
                    "indicator_id": ind.id, "indicator_name": ind.name,
                    "indicator_code": ind.code, "unit": ind.unit
                })
        return pending
    @staticmethod
    def get_active_rule_sets_query(company_id: int):
        return IncentiveRuleSet.query.filter(
            IncentiveRuleSet.company_id == company_id,
            IncentiveRuleSet.deleted_at.is_(None),
        )

    @staticmethod
    def get_rule_set(company_id: int, rule_set_id: int) -> Optional[IncentiveRuleSet]:
        return IncentiveRuleSet.query.filter(
            IncentiveRuleSet.id == rule_set_id,
            IncentiveRuleSet.company_id == company_id,
            IncentiveRuleSet.deleted_at.is_(None),
        ).first()

    @staticmethod
    def get_active_participants_query(company_id: int, rule_set_id: Optional[int] = None):
        query = IncentiveParticipant.query.filter(
            IncentiveParticipant.company_id == company_id,
            IncentiveParticipant.deleted_at.is_(None),
        )
        if rule_set_id is not None:
            query = query.filter(IncentiveParticipant.rule_set_id == rule_set_id)
        return query

    @staticmethod
    def get_active_rules_query(company_id: int, rule_set_id: Optional[int] = None):
        query = IncentiveRule.query.filter(IncentiveRule.deleted_at.is_(None))
        if rule_set_id is not None:
            query = query.join(
                IncentiveRuleSet,
                IncentiveRuleSet.id == IncentiveRule.rule_set_id,
            ).filter(
                IncentiveRule.rule_set_id == rule_set_id,
                IncentiveRuleSet.company_id == company_id,
                IncentiveRuleSet.deleted_at.is_(None),
            )
        else:
            query = query.filter(
                sa.or_(
                    IncentiveRule.company_id == company_id,
                    IncentiveRule.company_id.is_(None),
                )
            )
        return query

    @staticmethod
    def _rule_set_has_calculations(company_id: int, rule_set_id: int) -> bool:
        return (
            IncentiveService.get_active_calculations_query(company_id).filter_by(
                rule_set_id=rule_set_id,
            ).count()
            > 0
        )

    @staticmethod
    def get_active_calculations_query(company_id: int):
        return IncentiveCalculation.query.filter(
            IncentiveCalculation.company_id == company_id,
            IncentiveCalculation.deleted_at.is_(None),
        )

    @staticmethod
    def get_calculation(company_id: int, calc_id: int) -> Optional[IncentiveCalculation]:
        return IncentiveCalculation.query.filter(
            IncentiveCalculation.id == calc_id,
            IncentiveCalculation.company_id == company_id,
            IncentiveCalculation.deleted_at.is_(None),
        ).first()

    @classmethod
    def validate_rule_set_soft_delete(cls, company_id: int, rule_set_id: int) -> tuple[bool, str]:
        active_rules = cls.get_active_rules_query(company_id, rule_set_id).count()
        if active_rules:
            return False, "Não é possível excluir o plano porque existem vetores vinculados."

        active_participants = cls.get_active_participants_query(company_id, rule_set_id).count()
        if active_participants:
            return False, "Não é possível excluir o plano porque existem participantes vinculados."

        if cls._rule_set_has_calculations(company_id, rule_set_id):
            return False, "Não é possível excluir o plano porque já existem apurações vinculadas."

        return True, ""

    @classmethod
    def soft_delete_rule_set(cls, company_id: int, rule_set_id: int) -> tuple[bool, str]:
        rule_set = cls.get_rule_set(company_id, rule_set_id)
        if not rule_set:
            return False, "Plano de incentivo não encontrado."

        allowed, reason = cls.validate_rule_set_soft_delete(company_id, rule_set_id)
        if not allowed:
            return False, reason

        rule_set.is_active = False
        rule_set.deleted_at = datetime.utcnow()
        db.session.commit()
        return True, ""

    @classmethod
    def inactivate_rule_set(cls, company_id: int, rule_set_id: int) -> tuple[bool, str]:
        rule_set = cls.get_rule_set(company_id, rule_set_id)
        if not rule_set:
            return False, "Plano de incentivo não encontrado."

        rule_set.is_active = False
        db.session.commit()
        return True, ""

    @classmethod
    def soft_delete_participant(cls, company_id: int, participant: IncentiveParticipant) -> tuple[bool, str]:
        if participant.company_id != company_id or participant.deleted_at is not None:
            return False, "Participante não encontrado."

        if cls._rule_set_has_calculations(company_id, participant.rule_set_id):
            return False, "Não é possível excluir o participante porque o plano já possui apurações vinculadas."

        participant.elegivel = False
        participant.deleted_at = datetime.utcnow()
        db.session.commit()
        return True, ""

    @classmethod
    def soft_delete_rule(cls, company_id: int, rule: IncentiveRule) -> tuple[bool, str]:
        rule_set = cls.get_rule_set(company_id, rule.rule_set_id)
        if not rule_set or rule.deleted_at is not None:
            return False, "Vetor não encontrado."

        if cls._rule_set_has_calculations(company_id, rule.rule_set_id):
            return False, "Não é possível excluir o vetor porque o plano já possui apurações vinculadas."

        if rule.company_id is None:
            rule.company_id = company_id
        rule.deleted_at = datetime.utcnow()
        db.session.commit()
        return True, ""

    @classmethod
    def update_calculation(
        cls,
        company_id: int,
        calc_id: int,
        *,
        period_start=None,
        period_end=None,
        status=None,
    ) -> tuple[bool, str, Optional[IncentiveCalculation]]:
        calc = cls.get_calculation(company_id, calc_id)
        if not calc:
            return False, "Fechamento não encontrado.", None

        if period_start is not None:
            calc.period_start = period_start
        if period_end is not None:
            calc.period_end = period_end
        if status is not None:
            calc.status = status

        db.session.commit()
        return True, "", calc

    @classmethod
    def soft_delete_calculation(
        cls,
        company_id: int,
        calc_id: int,
        *,
        allow_protected: bool = False,
    ) -> tuple[bool, str]:
        calc = cls.get_calculation(company_id, calc_id)
        if not calc:
            return False, "Fechamento não encontrado."

        calc.deleted_at = datetime.utcnow()
        db.session.commit()
        return True, ""

    @classmethod
    def soft_delete_rule_set_with_closings(
        cls,
        company_id: int,
        rule_set_id: int,
        *,
        allow_protected: bool = False,
    ) -> tuple[bool, str]:
        rule_set = cls.get_rule_set(company_id, rule_set_id)
        if not rule_set:
            return False, "Plano de incentivo não encontrado."

        if not allow_protected:
            return False, "A exclusão encadeada do plano exige modo protegido."

        calculations = cls.get_active_calculations_query(company_id).filter_by(rule_set_id=rule_set_id).all()
        for calc in calculations:
            deleted, reason = cls.soft_delete_calculation(company_id, calc.id, allow_protected=True)
            if not deleted:
                db.session.rollback()
                return False, reason

        participants = cls.get_active_participants_query(company_id, rule_set_id).all()
        for participant in participants:
            deleted, reason = cls.soft_delete_participant(company_id, participant)
            if not deleted:
                db.session.rollback()
                return False, reason

        rules = cls.get_active_rules_query(company_id, rule_set_id).all()
        for rule in rules:
            deleted, reason = cls.soft_delete_rule(company_id, rule)
            if not deleted:
                db.session.rollback()
                return False, reason

        allowed, reason = cls.validate_rule_set_soft_delete(company_id, rule_set_id)
        if not allowed:
            return False, reason

        rule_set.deleted_at = datetime.utcnow()
        rule_set.is_active = False
        db.session.commit()
        return True, ""
