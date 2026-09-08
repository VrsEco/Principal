"""Pure contracts for advisory SE-COORD triage; no operational authority."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Domain = Literal['arquiteto', 'frontend', 'backend_api', 'backend_service', 'ai_engineer', 'dba', 'qa_automation']
Level = Literal['low', 'medium', 'high']
TaskType = Literal['diagnosis', 'documentation', 'maintenance', 'feature', 'incident']
TaskIntent = Literal['execution', 'correction', 'planning']


class AssessmentModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, frozen=True)


class EngineeringTaskRequest(AssessmentModel):
    task_id: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=3, max_length=4000)
    task_type: TaskType | None = None
    task_intent: TaskIntent | None = None
    context_scope: Literal['repository', 'company'] = 'repository'
    company_id: StrictInt | None = Field(default=None, gt=0)
    files: tuple[str, ...] = Field(default=(), max_length=100)
    domain_hints: tuple[Domain, ...] = ()

    @model_validator(mode='after')
    def validate_scope(self):
        if self.context_scope == 'company' and self.company_id is None:
            raise ValueError('company_id obrigatório para contexto de empresa.')
        if self.context_scope == 'repository' and self.company_id is not None:
            raise ValueError('Use context_scope=company quando houver company_id.')
        for path in self.files:
            if not path.strip() or len(path) > 400 or '..' in path.replace('\\', '/').split('/'):
                raise ValueError('Referência de arquivo inválida.')
        return self


class TaskAssessment(AssessmentModel):
    schema_version: Literal['engineering.assessment.v1'] = 'engineering.assessment.v1'
    rule_version: Literal['se-coord.rules.v1'] = 'se-coord.rules.v1'
    runtime_profile: Literal['engineering'] = 'engineering'
    entry_agent: Literal['SE-COORD'] = 'SE-COORD'
    task_id: str
    objective: str
    context_scope: Literal['repository', 'company']
    company_id: StrictInt | None
    task_type: TaskType
    task_intent: TaskIntent
    domain: Domain | Literal['unknown']
    complexity: Level
    risk: Level
    scope: Literal['file', 'module', 'cross_module']
    specialists: tuple[str, ...]
    context_domains: tuple[Domain, ...]
    requires_architect: bool
    requires_dba: bool
    requires_clarification: bool
    reasons: tuple[str, ...]
    unknowns: tuple[str, ...]
    advisory_only: Literal[True] = True

    def telemetry(self) -> dict:
        """Return minimal metrics, never objective, paths, credentials or payloads."""
        return {
            'event': 'engineering.task_assessed',
            'schema_version': self.schema_version,
            'rule_version': self.rule_version,
            'runtime_profile': self.runtime_profile,
            'context_scope': self.context_scope,
            'company_id': self.company_id,
            'domain': self.domain,
            'task_type': self.task_type,
            'complexity': self.complexity,
            'risk': self.risk,
            'specialist_count': len(self.specialists),
            'requires_clarification': self.requires_clarification,
            'model': None,
            'provider': None,
            'tokens': None,
            'status': 'assessed_not_executed',
        }
