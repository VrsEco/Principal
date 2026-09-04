import ast
import calendar
import logging
import operator
import re
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Iterable
from models import db, Indicator, IndicatorData, IndicatorGoal

logger = logging.getLogger(__name__)

ALLOWED_FORMULA_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}

ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def goal_is_effective(goal: IndicatorGoal, reference_date: date) -> bool:
    """Retorna se a definição da meta cobre a data, inclusive historicamente."""
    created_at = getattr(goal, "created_at", None)
    start = goal.period_start or (created_at.date() if created_at else date.min)
    end = goal.period_end or goal.goal_date
    if goal.status == "cancelled" or (goal.status == "inactive" and end is None):
        return False
    return start <= reference_date and (end is None or reference_date <= end)


def get_goal_cycle_bounds(goal: IndicatorGoal, reference_date: date) -> tuple[date, date]:
    """Resolve a competência da meta sem materializar uma nova meta a cada ciclo."""
    effective_start = goal.period_start or reference_date
    effective_end = goal.period_end or goal.goal_date
    goal_type = goal.goal_type or "monthly"

    if goal_type == "single":
        cycle_start = effective_start
        cycle_end = effective_end or effective_start
    elif goal_type == "weekly":
        cycle_start = reference_date - timedelta(days=reference_date.weekday())
        cycle_end = cycle_start + timedelta(days=6)
    elif goal_type in {"bimonthly", "quarterly"}:
        size = 2 if goal_type == "bimonthly" else 3
        month_distance = (reference_date.year - effective_start.year) * 12 + reference_date.month - effective_start.month
        block = max(month_distance, 0) // size
        cycle_start = _add_months(effective_start.replace(day=1), block * size)
        cycle_end = _add_months(cycle_start, size) - timedelta(days=1)
    elif goal_type == "annual":
        years = max(reference_date.year - effective_start.year, 0)
        cycle_year = effective_start.year + years
        cycle_start = date(
            cycle_year,
            effective_start.month,
            min(effective_start.day, calendar.monthrange(cycle_year, effective_start.month)[1]),
        )
        next_year = cycle_start.year + 1
        next_cycle = date(
            next_year,
            effective_start.month,
            min(effective_start.day, calendar.monthrange(next_year, effective_start.month)[1]),
        )
        cycle_end = next_cycle - timedelta(days=1)
    else:  # monthly
        cycle_start = reference_date.replace(day=1)
        cycle_end = _add_months(cycle_start, 1) - timedelta(days=1)

    cycle_start = max(cycle_start, effective_start)
    if effective_end:
        cycle_end = min(cycle_end, effective_end)
    return cycle_start, cycle_end


def aggregate_measurement_values(values: Iterable[Decimal], aggregation_function: str) -> Optional[Decimal]:
    values = [Decimal(str(value)) for value in values]
    if not values:
        return None
    if aggregation_function == "avg":
        return sum(values, Decimal("0")) / Decimal(len(values))
    if aggregation_function == "last":
        return values[-1]
    if aggregation_function == "count":
        return Decimal(len(values))
    return sum(values, Decimal("0"))


class IndicatorGoalService:
    """Regras de vigência, versionamento e composição de metas."""

    @staticmethod
    def _query():
        return IndicatorGoal.query

    @staticmethod
    def _measurement_query():
        return IndicatorData.query

    @staticmethod
    def _employee_query():
        from models import Employee
        return Employee.query

    @staticmethod
    def _routine_query():
        from models import Routine
        return Routine.query

    @staticmethod
    def prepare_measurement_payload(company_id: int, data: Dict) -> Dict:
        """Normaliza o fato medido e impede cruzamento de indicador/consultor/tenant."""
        payload = dict(data)
        goal_id = payload.get("goal_id")
        indicator_id = payload.get("indicator_id")
        if goal_id:
            goal = IndicatorGoalService._query().filter_by(
                id=int(goal_id),
                company_id=company_id,
            ).first()
            if not goal:
                raise ValueError("Meta não encontrada para a empresa ativa.")
            if indicator_id and int(indicator_id) != goal.indicator_id:
                raise ValueError("A meta não pertence ao indicador informado.")
            payload["indicator_id"] = goal.indicator_id
            if goal.responsible_id:
                if payload.get("employee_id") and int(payload["employee_id"]) != goal.responsible_id:
                    raise ValueError("A medição deve usar o consultor definido na meta individual.")
                payload["employee_id"] = goal.responsible_id

        if payload.get("employee_id"):
            employee = IndicatorGoalService._employee_query().filter_by(
                id=int(payload["employee_id"]),
                company_id=company_id,
            ).first()
            if not employee:
                raise ValueError("Consultor não encontrado para a empresa ativa.")
        return payload

    @staticmethod
    def validate_tenant_references(company_id: int, indicator_id: int, responsible_id: Optional[int] = None) -> Indicator:
        indicator = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first()
        if not indicator:
            raise ValueError("Indicador não encontrado para a empresa ativa.")
        if responsible_id:
            from models import Employee
            employee = Employee.query.filter_by(id=responsible_id, company_id=company_id).first()
            if not employee:
                raise ValueError("Responsável não encontrado para a empresa ativa.")
        return indicator

    @staticmethod
    def sync_routines(goal: IndicatorGoal, company_id: int, routine_ids: Iterable[int]) -> None:
        """Substitui os workflows da meta após validar todos no tenant ativo."""
        from models import IndicatorGoalRoutine, Routine

        normalized_ids = []
        for raw_id in routine_ids or []:
            try:
                routine_id = int(raw_id)
            except (TypeError, ValueError):
                raise ValueError("Rotina vinculada inválida.")
            if routine_id not in normalized_ids:
                normalized_ids.append(routine_id)

        if normalized_ids:
            valid_ids = {
                item.id
                for item in IndicatorGoalService._routine_query()
                .filter_by(company_id=company_id)
                .filter(Routine.id.in_(normalized_ids))
                .all()
            }
            if valid_ids != set(normalized_ids):
                raise ValueError("Uma ou mais rotinas não pertencem à empresa ativa.")

        goal.routine_links = [
            IndicatorGoalRoutine(company_id=company_id, routine_id=routine_id)
            for routine_id in normalized_ids
        ]
        # Compatibilidade temporária com integrações que ainda consomem o vínculo 1:1.
        goal.routine_id = normalized_ids[0] if normalized_ids else None

    @staticmethod
    def apply_base_versioning(goal: IndicatorGoal, exclude_goal_id: Optional[int] = None) -> None:
        """Fecha a versão anterior e limita a nova pela próxima versão."""
        if goal.goal_kind != "base" or goal.goal_type == "single" or not goal.period_start:
            return

        query = IndicatorGoalService._query().filter_by(
            company_id=goal.company_id,
            indicator_id=goal.indicator_id,
            responsible_id=goal.responsible_id,
            goal_kind="base",
        )
        if exclude_goal_id:
            query = query.filter(IndicatorGoal.id != exclude_goal_id)
        versions = query.order_by(IndicatorGoal.period_start.asc()).all()

        if any(item.period_start == goal.period_start for item in versions):
            raise ValueError("Já existe uma meta-base com esta data de início.")

        previous = next(
            (item for item in reversed(versions) if item.period_start and item.period_start < goal.period_start),
            None,
        )
        following = next(
            (item for item in versions if item.period_start and item.period_start > goal.period_start),
            None,
        )

        if previous and (previous.period_end is None or previous.period_end >= goal.period_start):
            previous.period_end = goal.period_start - timedelta(days=1)
            previous.status = "superseded"

        if following:
            maximum_end = following.period_start - timedelta(days=1)
            if goal.period_end is None or goal.period_end > maximum_end:
                goal.period_end = maximum_end

        goal.composition_mode = "independent"
        goal.status = "active"

    @staticmethod
    def validate_goal(goal: IndicatorGoal) -> None:
        if not goal.period_start:
            raise ValueError("Informe a data de início da meta.")
        if goal.goal_value is None:
            raise ValueError("Informe o valor da meta.")
        try:
            goal_value = Decimal(str(goal.goal_value))
        except Exception as exc:
            raise ValueError("O valor da meta deve ser numérico.") from exc
        if not goal_value.is_finite():
            raise ValueError("O valor da meta deve ser um número finito.")
        if goal.goal_kind not in {"base", "campaign"}:
            raise ValueError("Tipo de meta inválido.")
        if goal.goal_scope not in {"team", "individual"}:
            raise ValueError("Escopo da meta inválido.")
        if goal.goal_scope == "team" and goal.responsible_id:
            raise ValueError("Metas de equipe não podem possuir um consultor responsável.")
        if goal.goal_scope == "individual" and not goal.responsible_id:
            raise ValueError("Selecione o consultor da meta individual.")
        if goal.composition_mode not in {"independent", "additive"}:
            raise ValueError("Modo de composição inválido.")
        if goal.goal_kind == "campaign":
            goal.goal_type = "single"
            if not goal.period_end:
                raise ValueError("Informe a data final da campanha.")
        if goal.period_end and goal.period_end < goal.period_start:
            raise ValueError("A data final não pode ser anterior ao início.")

    @staticmethod
    def resolve_effective_goals(company_id: int, indicator_id: int, reference_date: date, responsible_id: Optional[int] = None) -> Dict:
        query = IndicatorGoalService._query().filter_by(
            company_id=company_id,
            indicator_id=indicator_id,
            responsible_id=responsible_id,
            goal_scope="individual" if responsible_id is not None else "team",
        )
        goals = [goal for goal in query.all() if goal_is_effective(goal, reference_date)]
        base_goals = sorted(
            (goal for goal in goals if goal.goal_kind == "base"),
            key=lambda goal: goal.period_start or date.min,
            reverse=True,
        )
        campaigns = [goal for goal in goals if goal.goal_kind == "campaign"]
        return {
            "base": base_goals[0] if base_goals else None,
            "additive_campaigns": [goal for goal in campaigns if goal.composition_mode == "additive"],
            "independent_campaigns": [goal for goal in campaigns if goal.composition_mode == "independent"],
        }

    @staticmethod
    def performance_context(company_id: int, indicator: Indicator, reference_date: date) -> Dict:
        return IndicatorGoalService.performance_context_for_scope(
            company_id,
            indicator,
            reference_date,
            responsible_id=None,
        )

    @staticmethod
    def performance_context_for_scope(
        company_id: int,
        indicator: Indicator,
        reference_date: date,
        responsible_id: Optional[int],
    ) -> Dict:
        goals = IndicatorGoalService.resolve_effective_goals(
            company_id,
            indicator.id,
            reference_date,
            responsible_id=responsible_id,
        )
        base = goals["base"]
        if not base:
            return {
                **goals,
                "responsible_id": responsible_id,
                "target_value": None,
                "realized_value": None,
                "cycle_start": None,
                "cycle_end": None,
            }

        cycle_start, cycle_end = get_goal_cycle_bounds(base, reference_date)
        measurements_query = IndicatorGoalService._measurement_query().filter(
            IndicatorData.company_id == company_id,
            IndicatorData.indicator_id == indicator.id,
            IndicatorData.measured_date >= cycle_start,
            IndicatorData.measured_date <= cycle_end,
        ).order_by(IndicatorData.measured_date.asc(), IndicatorData.id.asc())
        if responsible_id is not None:
            measurements_query = measurements_query.filter(IndicatorData.employee_id == responsible_id)
        measurements = measurements_query.all()
        realized = aggregate_measurement_values(
            [item.measured_value for item in measurements],
            indicator.aggregation_function or "sum",
        )
        target = Decimal(str(base.goal_value)) + sum(
            (Decimal(str(goal.goal_value)) for goal in goals["additive_campaigns"]),
            Decimal("0"),
        )
        return {
            **goals,
            "responsible_id": responsible_id,
            "target_value": target,
            "realized_value": realized,
            "cycle_start": cycle_start,
            "cycle_end": cycle_end,
        }

    @staticmethod
    def individual_performance_contexts(company_id: int, indicator: Indicator, reference_date: date) -> List[Dict]:
        goals = IndicatorGoalService._query().filter_by(
            company_id=company_id,
            indicator_id=indicator.id,
            goal_scope="individual",
        ).all()
        responsible_ids = sorted({
            goal.responsible_id
            for goal in goals
            if goal.responsible_id and goal_is_effective(goal, reference_date)
        })
        contexts = [
            IndicatorGoalService.performance_context_for_scope(
                company_id,
                indicator,
                reference_date,
                responsible_id=responsible_id,
            )
            for responsible_id in responsible_ids
        ]
        for context in contexts:
            base = context.get("base")
            context["responsible"] = getattr(base, "responsible", None) if base else None
        return sorted(
            contexts,
            key=lambda context: (
                getattr(context.get("responsible"), "name", "") or "",
                context.get("responsible_id") or 0,
            ),
        )

    @staticmethod
    def consolidated_performance_context(company_id: int, indicator: Indicator, reference_date: date) -> Dict:
        team_context = IndicatorGoalService.performance_context(company_id, indicator, reference_date)
        individuals = IndicatorGoalService.individual_performance_contexts(company_id, indicator, reference_date)
        valid_individuals = [item for item in individuals if item.get("target_value") is not None]
        for item in individuals:
            item.update(IndicatorGoalService.classify_performance(
                indicator,
                item.get("base"),
                item.get("target_value"),
                item.get("realized_value"),
            ))
        if not valid_individuals:
            return {
                **team_context,
                "individual_contexts": individuals,
                "individual_target_sum": None,
                "allocation_gap": None,
                "target_source": "team" if team_context.get("target_value") is not None else None,
            }

        individual_target_sum = sum(
            (Decimal(str(item["target_value"])) for item in valid_individuals),
            Decimal("0"),
        )
        realized_values = [
            Decimal(str(item["realized_value"]))
            for item in valid_individuals
            if item.get("realized_value") is not None
        ]
        if not realized_values:
            consolidated_realized = None
        elif indicator.aggregation_function == "avg":
            consolidated_realized = sum(realized_values, Decimal("0")) / Decimal(len(realized_values))
        else:
            consolidated_realized = sum(realized_values, Decimal("0"))

        explicit_team_target = team_context.get("target_value")
        consolidated_target = (
            Decimal(str(explicit_team_target))
            if explicit_team_target is not None
            else individual_target_sum
        )
        allocation_gap = (
            consolidated_target - individual_target_sum
            if explicit_team_target is not None
            else Decimal("0")
        )
        cycle_context = team_context if team_context.get("cycle_start") else valid_individuals[0]
        return {
            **team_context,
            "target_value": consolidated_target,
            "realized_value": consolidated_realized,
            "cycle_start": cycle_context.get("cycle_start"),
            "cycle_end": cycle_context.get("cycle_end"),
            "individual_contexts": individuals,
            "individual_target_sum": individual_target_sum,
            "allocation_gap": allocation_gap,
            "target_source": "team" if explicit_team_target is not None else "individual_sum",
        }

    @staticmethod
    def classify_performance(
        indicator: Indicator,
        goal: Optional[IndicatorGoal],
        target_value,
        realized_value,
    ) -> Dict:
        from utils.indicator_ranges import normalize_performance_ranges

        if target_value is None:
            return {"performance_pct": None, "status_class": "no_goal"}
        if realized_value is None:
            return {"performance_pct": None, "status_class": "no_data"}

        target = float(target_value)
        realized = float(realized_value)
        if target == 0:
            return {
                "performance_pct": 100.0 if realized == 0 else None,
                "status_class": "on_target" if realized == 0 else "alert",
            }

        performance_pct = round((realized / target) * 100, 1)
        # Para metas negativas de indicadores em que maior é melhor (ex.: CCL),
        # o quociente puro inverte o sentido: -105 / -100 resultaria em 105%.
        # Espelhamos o percentual em torno de 100 para preservar a direção.
        if target < 0 and indicator.polarity != "negative":
            performance_pct = round(200 - performance_pct, 1)
        ranges = normalize_performance_ranges(getattr(goal, "performance_ranges", None))
        red_max = ranges.get("red", 80)
        yellow_max = ranges.get("yellow", 90)
        green_max = ranges.get("green", 110)

        if indicator.polarity == "negative":
            if realized <= target:
                status_class = "on_target"
            elif target < 0 and performance_pct >= (200 - green_max):
                status_class = "alert"
            elif target > 0 and realized <= target * (green_max / 100):
                status_class = "alert"
            else:
                status_class = "below"
        elif performance_pct >= green_max:
            status_class = "exceeded"
        elif performance_pct >= yellow_max:
            status_class = "on_target"
        elif performance_pct >= red_max:
            status_class = "alert"
        else:
            status_class = "below"
        return {"performance_pct": performance_pct, "status_class": status_class}


def _evaluate_formula_expression(expression: str) -> float:
    """Avalia fórmulas aritméticas de forma segura, via AST controlada."""

    def _evaluate_node(node):
        if isinstance(node, ast.Expression):
            return _evaluate_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Constante não suportada: {type(node.value).__name__}")

        if isinstance(node, ast.Num):  # pragma: no cover - compat legado do AST
            return float(node.n)

        if isinstance(node, ast.BinOp):
            operator_fn = ALLOWED_BINARY_OPERATORS.get(type(node.op))
            if operator_fn is None:
                raise ValueError(
                    f"Operador binário não suportado: {type(node.op).__name__}"
                )
            return operator_fn(_evaluate_node(node.left), _evaluate_node(node.right))

        if isinstance(node, ast.UnaryOp):
            operator_fn = ALLOWED_UNARY_OPERATORS.get(type(node.op))
            if operator_fn is None:
                raise ValueError(
                    f"Operador unário não suportado: {type(node.op).__name__}"
                )
            return operator_fn(_evaluate_node(node.operand))

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Apenas chamadas diretas de funções são permitidas")

            function_name = node.func.id
            function = ALLOWED_FORMULA_FUNCTIONS.get(function_name)
            if function is None:
                raise ValueError(f"Função não suportada: {function_name}")
            if node.keywords:
                raise ValueError("Argumentos nomeados não são permitidos em fórmulas")

            arguments = [_evaluate_node(argument) for argument in node.args]
            return float(function(*arguments))

        raise ValueError(f"Elemento não suportado na fórmula: {type(node).__name__}")

    parsed_expression = ast.parse(expression, mode="eval")
    return float(_evaluate_node(parsed_expression))

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
            result = _evaluate_formula_expression(eval_formula)
            
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
