"""Deterministic, side-effect-free SE-COORD router. Suggestions are not grants."""
from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath

from src.intelligence.engineering_assessment import EngineeringTaskRequest, TaskAssessment
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


def _normalize(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


_SIGNALS = {
    'arquiteto': ('arquitetura', 'architecture', 'boundary', 'boundaries'),
    'frontend': ('css', 'jinja', 'tailwind', 'layout', 'botao', 'frontend'),
    'backend_api': ('api', 'endpoint', 'rota', 'rotas', 'schema', 'contrato rest', 'contrato mcp'),
    'backend_service': ('regra de negocio', 'calculo', 'acumulado', 'service', 'servico'),
    'ai_engineer': ('rag', 'langgraph', 'embeddings', 'agente', 'agentes'),
    'dba': ('sql', 'postgresql', 'query', 'indice', 'migration', 'migracao', 'alembic'),
    'qa_automation': ('pytest', 'regressao', 'smoke', 'testes', 'tests'),
}
_SECURITY = ('auth', 'oauth', 'login', 'autenticacao', 'autorizacao', 'permissao', 'permissoes', 'tenant', 'multi-tenancy', 'company_id', 'seguranca', 'rbac')
_MIGRATION = ('migration', 'migrations', 'migracao', 'alembic')
_PLANNING = ('planejar', 'planejamento', 'concepcao', 'desenhar arquitetura', 'architecture design')


def _matches(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', text) for word in words)


class EngineeringTaskRouterService:
    @staticmethod
    def assess(request: EngineeringTaskRequest | dict) -> TaskAssessment:
        request = EngineeringTaskRequest.model_validate(request)
        text = _normalize(request.objective)
        incident = _matches(text, ('incidente', 'indisponibilidade', 'vazamento', 'outage'))
        task_type = request.task_type
        if task_type is None:
            task_type = 'diagnosis'
            for candidate, words in (
                ('incident', ('incidente', 'indisponibilidade', 'vazamento', 'outage')),
                ('documentation', ('documentar', 'documentacao', 'especificacao')),
                ('maintenance', ('corrigir', 'ajustar', 'trocar', 'refatorar')),
                ('feature', ('criar', 'implementar', 'adicionar')),
            ):
                if _matches(text, words):
                    task_type = candidate
                    break
        task_intent = request.task_intent
        if task_intent is None:
            if _matches(text, _PLANNING):
                task_intent = 'planning'
            elif task_type == 'maintenance':
                task_intent = 'correction'
            else:
                task_intent = 'execution'
        files = tuple(sorted({_normalize(p.replace('\\', '/')) for p in request.files}))
        domains = set(request.domain_hints)
        reasons = ['entry:SE-COORD', 'policy:advisory_only', f'task_type:{task_type}']
        for domain, words in _SIGNALS.items():
            if _matches(text, words):
                domains.add(domain)
                reasons.append(f'signal:{domain}')
        for path in files:
            parts = PurePosixPath(path).parts
            suffix = PurePosixPath(path).suffix
            if 'tests' in parts or PurePosixPath(path).name.startswith('test_'):
                domains.add('qa_automation')
            elif suffix in ('.css', '.js', '.html', '.jinja', '.jinja2') or 'templates' in parts:
                domains.add('frontend')
            elif 'migrations' in parts or 'models' in parts or suffix == '.sql':
                domains.add('dba')
            elif 'routes' in parts or 'api' in parts or 'mcp_contracts' in parts:
                domains.add('backend_api')
            elif 'services' in parts:
                domains.add('backend_service')
        security = _matches(text, _SECURITY) or any(
            _matches(p.replace('/', ' ').replace('.', ' ').replace('_', ' '), _SECURITY)
            or 'security' in PurePosixPath(p).parts for p in files
        )
        migration = _matches(text, _MIGRATION) or any('migrations' in PurePosixPath(p).parts for p in files)
        if security:
            domains.add('arquiteto')
            reasons.append('gate:security_or_tenant')
        if migration:
            domains.add('dba')
            reasons.append('gate:migration')
        # Fixed ordering avoids nondeterminism from set iteration or input order.
        ordered = tuple(d for d in _SIGNALS if d in domains)
        primary = tuple(d for d in ordered if d != 'qa_automation')
        ambiguous = len(primary) > 1 and not (security or migration or 'arquiteto' in domains)
        if security or 'arquiteto' in domains:
            leader = 'arquiteto'
        elif migration:
            leader = 'dba'
        elif len(primary) == 1:
            leader = primary[0]
        elif not primary and 'qa_automation' in domains:
            leader = 'qa_automation'
        else:
            leader = 'unknown'
        unknowns = ()
        if not ordered:
            unknowns = ('Informar domínio técnico ou arquivos afetados.',)
        elif ambiguous:
            unknowns = ('Confirmar domínio líder: há sinais de múltiplas especialidades.',)
        reasons.extend(f'hint:{d}' for d in sorted(set(request.domain_hints)))
        if files:
            reasons.append('signal:file_references')
        spec = get_runtime_profile_spec('engineering')
        if spec is None:
            raise ValueError('Runtime engineering indisponível.')
        available = {h.key for h in spec.harnesses}
        selected = []
        if leader != 'unknown':
            selected.append(f'harness_{leader}_engenharia_v1')
            if migration and leader != 'dba':
                selected.append('harness_dba_engenharia_v1')
            if task_type in ('maintenance', 'feature', 'incident') and leader != 'qa_automation':
                selected.append('harness_qa_automation_engenharia_v1')
        if any(h not in available for h in selected):
            raise ValueError('Harness selecionado não registrado em engineering.')
        scope = 'cross_module' if len(primary) > 1 else ('file' if len(files) == 1 else 'module')
        high = security or migration or incident or task_type == 'incident'
        risk = 'high' if high else ('medium' if leader == 'unknown' or scope == 'cross_module' else 'low')
        complexity = 'high' if high or task_intent == 'planning' or len(files) > 10 else (
            'medium' if task_intent == 'correction' or len(files) > 3 or scope == 'cross_module' or leader == 'unknown' else 'low'
        )
        return TaskAssessment(
            task_id=request.task_id, objective=request.objective, task_type=task_type,
            task_intent=task_intent,
            context_scope=request.context_scope, company_id=request.company_id,
            domain=leader, complexity=complexity, risk=risk, scope=scope,
            specialists=tuple(selected), context_domains=ordered,
            requires_architect='arquiteto' in domains, requires_dba='dba' in domains,
            requires_clarification=bool(unknowns), reasons=tuple(reasons), unknowns=unknowns,
        )
