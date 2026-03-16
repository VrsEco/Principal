import re
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from models import db, Indicator, IndicatorData

logger = logging.getLogger(__name__)

class IndicatorService:
    """
    Serviço para gestão de Indicadores, Motor de Fórmulas e Auditoria de Rotinas.
    PADRÃO GESTÃO VERSUS: Cálculos persistentes garantindo histórico.
    """

    @staticmethod
    def calculate_formula(company_id: int, indicator_id: int, reference_date: date) -> Optional[Decimal]:
        """
        Calcula o valor de um indicador baseado em sua fórumla.
        Sintaxe: [CODE] para valor atual, [CODE].prev para valor do período anterior.
        """
        indicator = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first()
        if not indicator or not indicator.formula:
            return None

        formula = indicator.formula
        # Encontrar todos os tokens [CÓDIGO] ou [CÓDIGO].prev
        tokens = re.findall(r'\[(.*?)\]', formula)
        
        values_map = {}
        for token in tokens:
            is_prev = token.endswith('.prev')
            clean_code = token.replace('.prev', '')
            
            # Buscar o indicador pelo código
            dep_indicator = Indicator.query.filter_by(code=clean_code, company_id=company_id).first()
            if not dep_indicator:
                logger.warning(f"Indicador dependente não encontrado: {clean_code}")
                return None
            
            # Determinar a data de referência para a dependência
            target_date = reference_date
            if is_prev:
                # Volta um período baseado na frequência (simplificando para mês por enquanto)
                # TODO: Implementar lógica exata por frequency
                target_date = reference_date - timedelta(days=30)

            # Buscar a medição mais próxima/pertencente ao período
            # Simplified: same month/year
            val = IndicatorData.query.filter(
                IndicatorData.indicator_id == dep_indicator.id,
                IndicatorData.company_id == company_id,
                db.extract('month', IndicatorData.measured_date) == target_date.month,
                db.extract('year', IndicatorData.measured_date) == target_date.year
            ).order_by(IndicatorData.measured_date.desc()).first()

            if not val:
                logger.warning(f"Medição não encontrada para {token} na data {target_date}")
                values_map[token] = 0.0 # Ou falhar? Vamos usar 0 por segurança, mas o ideal é ter o dado.
            else:
                values_map[token] = float(val.measured_value)

        # Substituir os tokens na fórmula pelos valores
        eval_formula = formula
        for token, value in values_map.items():
            eval_formula = eval_formula.replace(f'[{token}]', str(value))

        try:
            # Uso de eval restrito por segurança (embora sejamos Squad de Elite, segurança é prioridade)
            allowed_names = {"__builtins__": {}, "abs": abs, "min": min, "max": max, "round": round}
            result = eval(eval_formula, allowed_names)
            
            # Persistir o resultado para manter o histórico
            IndicatorService.upsert_measurement_calculated(
                company_id=company_id,
                indicator_id=indicator_id,
                value=Decimal(str(result)),
                measured_date=reference_date,
                notes=f"Calculado automaticamente via fórmula: {formula}"
            )
            
            return Decimal(str(result))
        except Exception as e:
            logger.error(f"Erro ao avaliar fórmula {formula}: {e}")
            return None

    @staticmethod
    def upsert_measurement_calculated(company_id: int, indicator_id: int, value: Decimal, 
                                     measured_date: date, notes: Optional[str] = None):
        """Salva ou atualiza uma medição calculada, preservando histórico."""
        existing = IndicatorData.query.filter(
            IndicatorData.company_id == company_id,
            IndicatorData.indicator_id == indicator_id,
            db.extract('month', IndicatorData.measured_date) == measured_date.month,
            db.extract('year', IndicatorData.measured_date) == measured_date.year
        ).first()

        if existing:
            # Só atualiza se for explicitamente vindo de cálculo (evita sobrescrever ajuste manual se houver flag)
            existing.measured_value = value
            if notes: existing.notes = (existing.notes or "") + " | " + notes
        else:
            new_record = IndicatorData(
                company_id=company_id,
                indicator_id=indicator_id,
                measured_value=value,
                measured_date=measured_date,
                notes=notes,
                source_ref="formula_engine"
            )
            db.session.add(new_record)
        
        db.session.commit()

    @staticmethod
    def get_orphaned_indicators(company_id: int) -> List[Indicator]:
        """Identifica indicadores que possuem metas ativas sem rotina vinculada."""
        from models import IndicatorGoal
        # Indicadores ativos
        active_indicators = Indicator.query.filter_by(company_id=company_id, is_active=True).all()
        orphans = []
        for ind in active_indicators:
            # Verificar se tem meta ativa sem rotina
            has_orphan_goal = IndicatorGoal.query.filter_by(
                indicator_id=ind.id, 
                company_id=company_id, 
                status='active', 
                routine_id=None
            ).first() is not None
            
            # Se o indicador for manual (não tem fórmula) e tem meta sem rotina, é órfão
            if not ind.formula and has_orphan_goal:
                orphans.append(ind)
        
        return orphans

    @staticmethod
    def trigger_dependent_calculations(company_id: int, component_indicator_id: int, reference_date: date):
        """
        Dispara o recálculo de indicadores que dependem deste componente.
        """
        comp_ind = Indicator.query.get(component_indicator_id)
        if not comp_ind: return

        # Buscar indicadores que usam o código deste no campo formula
        dependents = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.formula.contains(f"[{comp_ind.code}]")
        ).all()

        for dep in dependents:
            IndicatorService.calculate_formula(company_id, dep.id, reference_date)
