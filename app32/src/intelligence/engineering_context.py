"""Immutable local context contracts. Identity descriptors never grant access."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, StrictInt, StringConstraints, model_validator
from src.intelligence.engineering_assessment import AssessmentModel, TaskAssessment


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class ContextIdentity(AssessmentModel):
    repository_id: str = Field(min_length=1, max_length=400)
    context_scope: Literal['repository', 'company'] = 'repository'
    company_id: StrictInt | None = Field(default=None, gt=0)
    user_id: StrictInt | None = Field(default=None, gt=0)
    permission_revision: str = Field(default='local-unprivileged', min_length=1, max_length=120)
    runtime_profile: Literal['engineering'] = 'engineering'
    harness_key: str = 'harness_coordenador_engenharia_v1'
    surface: Literal['ops', 'admin', 'analytics'] = 'ops'

    @model_validator(mode='after')
    def scoped_identity(self):
        if self.context_scope == 'company':
            if self.company_id is None or self.user_id is None or self.permission_revision == 'local-unprivileged':
                raise ValueError('Contexto empresarial exige empresa, usuário e revisão de autorização.')
        elif self.company_id is not None:
            raise ValueError('Contexto de repositório não pode conter company_id.')
        return self

    @property
    def fingerprint(self) -> str:
        return digest(canonical(self.model_dump(mode='json')))


class ContextItem(AssessmentModel):
    item_id: str = Field(min_length=1, max_length=120, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')
    identity: ContextIdentity
    kind: Literal['file', 'document', 'module', 'decision', 'assumption', 'question', 'test']
    source: str = Field(min_length=1, max_length=400)
    version: str = Field(min_length=1, max_length=120)
    content: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=100000)
    state: Literal['ACTIVE', 'WARM', 'DROPPED'] = 'ACTIVE'
    reason: str = Field(min_length=3, max_length=400)
    dependencies: tuple[str, ...] = Field(default=(), max_length=128)
    priority: StrictInt = Field(default=50, ge=0, le=100)

    @model_validator(mode='after')
    def valid_reference(self):
        if self.item_id == 'registry' or self.item_id in self.dependencies:
            raise ValueError('ID reservado ou dependência de si mesmo.')
        if '..' in self.source.replace('\\', '/').split('/'):
            raise ValueError('Referência com travessia de diretório.')
        return self

    @property
    def fingerprint(self) -> str:
        return digest(canonical([self.kind, self.source, self.version, self.content]))


class EngineeringWorkingSet(AssessmentModel):
    schema_version: Literal['engineering.working_set.v1'] = 'engineering.working_set.v1'
    assessment: TaskAssessment
    identity: ContextIdentity
    revision: StrictInt = Field(default=1, ge=1)
    registry_json: str
    items: tuple[ContextItem, ...] = Field(default=(), max_length=128)

    @model_validator(mode='after')
    def consistent_scope(self):
        if (self.assessment.context_scope, self.assessment.company_id) != (self.identity.context_scope, self.identity.company_id):
            raise ValueError('Assessment e identidade pertencem a escopos diferentes.')
        by_id = {item.item_id: item for item in self.items}
        if len(by_id) != len(self.items) or any(i.identity != self.identity for i in self.items):
            raise ValueError('ID duplicado ou item de outra identidade.')
        sources = {}
        for item in self.items:
            if item.source in sources and sources[item.source] != item.fingerprint:
                raise ValueError('Versões conflitantes da mesma fonte.')
            sources[item.source] = item.fingerprint
        complete = set()
        def visit(key, trail):
            if key not in by_id:
                raise ValueError('Dependência ausente.')
            if key in trail:
                raise ValueError('Ciclo de dependências.')
            if key in complete:
                return
            for dependency in by_id[key].dependencies:
                visit(dependency, trail | {key})
            complete.add(key)
        for key in by_id:
            visit(key, set())
        return self


class ContextPacket(AssessmentModel):
    schema_version: Literal['engineering.context_packet.v1'] = 'engineering.context_packet.v1'
    task_id: str
    identity_fingerprint: str
    registry_fingerprint: str
    working_set_revision: int
    ready: bool
    payload: str | None
    selected_ids: tuple[str, ...]
    deferred_ids: tuple[str, ...]
    stale_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    estimated_tokens: int
    budget_tokens: int
    estimation_method: Literal['utf8_bytes_div4_ceil_v1'] = 'utf8_bytes_div4_ceil_v1'

    @property
    def fingerprint(self):
        return digest(canonical(self.model_dump(mode='json')))

    def telemetry(self) -> dict:
        return {
            'event': 'engineering.context_composed',
            'status': 'ready_for_review' if self.ready else 'blocked_by_budget',
            'working_set_revision': self.working_set_revision,
            'selected_count': len(self.selected_ids),
            'deferred_count': len(self.deferred_ids),
            'stale_count': len(self.stale_ids),
            'estimated_tokens': self.estimated_tokens,
            'budget_tokens': self.budget_tokens,
            'estimation_method': self.estimation_method,
            'actual_provider_tokens': None,
        }
