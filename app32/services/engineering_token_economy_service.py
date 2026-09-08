"""Deterministic Sapiens Engenharia context advice; no model or operational authority."""
from typing import Literal

from src.intelligence.engineering_assessment import AssessmentModel, Level, TaskAssessment


class TokenEconomyAdvice(AssessmentModel):
    schema_version: Literal['engineering.token_economy.v1'] = 'engineering.token_economy.v1'
    complexity: Level
    risk: Level
    task_intent: Literal['execution', 'correction', 'planning']
    strategy: Literal['minimal_active', 'symbol_and_delta', 'architecture_then_expand', 'clarify_before_expand']
    initial_active: tuple[str, ...]
    warm_by_default: tuple[str, ...]
    dropped_by_default: tuple[str, ...]
    next_action: str
    requires_authenticated_mcp: bool
    selects_model: Literal[False] = False
    estimated_token_savings: None = None
    advisory_only: Literal[True] = True

    def telemetry(self) -> dict:
        return {
            'event': 'engineering.token_economy_advised',
            'schema_version': self.schema_version,
            'complexity': self.complexity,
            'risk': self.risk,
            'task_intent': self.task_intent,
            'strategy': self.strategy,
            'selects_model': False,
            'estimated_token_savings': None,
        }


class EngineeringTokenEconomyService:
    """Translate assessed complexity into context-selection steps, never into model choice."""

    @staticmethod
    def advise(assessment: TaskAssessment) -> TokenEconomyAdvice:
        if assessment.requires_clarification:
            return TokenEconomyAdvice(
                complexity=assessment.complexity, risk=assessment.risk, task_intent=assessment.task_intent,
                strategy='clarify_before_expand',
                initial_active=('objetivo e critério de aceite',),
                warm_by_default=('referências de arquivos fornecidas',),
                dropped_by_default=('módulos não relacionados', 'documentação integral', 'logs brutos'),
                next_action='Confirmar domínio líder ou arquivo afetado antes de carregar contexto adicional.',
                requires_authenticated_mcp=assessment.context_scope == 'company',
            )
        if assessment.complexity == 'low':
            return TokenEconomyAdvice(
                complexity='low', risk=assessment.risk, task_intent=assessment.task_intent,
                strategy='minimal_active',
                initial_active=('objetivo e critério de aceite', 'função ou arquivo afetado', 'teste ou evidência direta'),
                warm_by_default=('interfaces diretas', 'decisões confirmadas'),
                dropped_by_default=('módulos não relacionados', 'documentação integral', 'histórico da conversa não relacionado'),
                next_action='Carregar somente a fonte afetada e enviar apenas o delta em continuidades.',
                requires_authenticated_mcp=assessment.context_scope == 'company',
            )
        if assessment.complexity == 'medium':
            return TokenEconomyAdvice(
                complexity='medium', risk=assessment.risk, task_intent=assessment.task_intent,
                strategy='symbol_and_delta',
                initial_active=('objetivo e critério de aceite', 'símbolo afetado e contrato', 'dependências diretas', 'teste de regressão'),
                warm_by_default=('resumo versionado do módulo', 'interfaces adjacentes', 'decisões confirmadas'),
                dropped_by_default=('módulos distantes', 'logs completos', 'documentação integral'),
                next_action='Começar por símbolos e contratos; expandir uma dependência por vez somente se a evidência exigir.',
                requires_authenticated_mcp=assessment.context_scope == 'company',
            )
        return TokenEconomyAdvice(
            complexity='high', risk=assessment.risk, task_intent=assessment.task_intent,
            strategy='architecture_then_expand',
            initial_active=('objetivo e restrições', 'resumo arquitetural versionado', 'decisões confirmadas', 'interfaces e invariantes'),
            warm_by_default=('módulos candidatos', 'testes e evidências adicionais', 'histórico de decisões'),
            dropped_by_default=('árvore completa do repositório', 'código integral não solicitado', 'dados operacionais brutos'),
            next_action='Validar arquitetura, escopo e riscos; carregar trechos específicos em etapas, sem remover guardrails.',
            requires_authenticated_mcp=assessment.context_scope == 'company' or assessment.risk == 'high',
        )
