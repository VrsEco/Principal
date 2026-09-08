"""Pure Working Set operations; no filesystem, DB, cache, model or session I/O."""
from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache

from src.intelligence.engineering_assessment import TaskAssessment
from src.intelligence.engineering_context import (
    ContextIdentity, ContextItem, ContextPacket, EngineeringWorkingSet, canonical, digest,
)
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


def _replace(model, **values):
    return type(model).model_validate({**model.model_dump(), **values})


def _registry(identity: ContextIdentity, bundle: dict) -> str:
    # Registry remains the authority for governance. The caller must obtain a
    # trusted bundle; validating this schema does not authenticate its sender.
    from src.intelligence.mcp_contracts.instruction_registry import InstructionBootstrapBundle
    bundle = InstructionBootstrapBundle.model_validate(bundle)
    profile = get_runtime_profile_spec('engineering')
    harness = next((h for h in profile.harnesses if h.key == identity.harness_key), None) if profile else None
    if harness is None or bundle.agent_key != harness.agent_key:
        raise ValueError('Identidade de harness/registry incompatível.')
    if (bundle.runtime_profile, bundle.harness_key, bundle.company_id, bundle.surface) != (
        identity.runtime_profile, identity.harness_key, identity.company_id, identity.surface,
    ):
        raise ValueError('Bundle de outro escopo, harness ou surface.')
    return canonical(bundle.model_dump(mode='json'))


def _check(state: EngineeringWorkingSet, identity: ContextIdentity):
    if state.identity != identity:
        raise ValueError('Identidade mudou: criar Working Set novo, sem reutilizar conteúdo.')


class EngineeringContextGovernorService:
    @staticmethod
    def create(assessment: TaskAssessment, identity: ContextIdentity, bundle: dict) -> EngineeringWorkingSet:
        return EngineeringWorkingSet(assessment=assessment, identity=identity, registry_json=_registry(identity, bundle))

    @staticmethod
    def upsert(state: EngineeringWorkingSet, identity: ContextIdentity, item: ContextItem) -> EngineeringWorkingSet:
        _check(state, identity)
        if item.identity != identity:
            raise ValueError('Item de outra identidade.')
        old = next((i for i in state.items if i.item_id == item.item_id), None)
        if old:
            # State changes must go through transition(), especially DROPPED.
            if item.state != old.state:
                raise ValueError('Usar transition para mudar estado.')
            changed = old.fingerprint != item.fingerprint or old.dependencies != item.dependencies
            if changed and old.state == 'ACTIVE':
                item = _replace(item, state='WARM', reason='Fonte alterada: revalidação obrigatória.')
        else:
            changed = False
        items = {i.item_id: i for i in state.items}
        items[item.item_id] = item
        if changed:
            affected = {item.item_id}
            while True:
                more = {i.item_id for i in items.values() if set(i.dependencies) & affected} - affected
                if not more:
                    break
                affected |= more
            for key in affected - {item.item_id}:
                if items[key].state == 'ACTIVE':
                    items[key] = _replace(items[key], state='WARM', reason='Dependência alterada: revalidar.')
        return _replace(state, items=tuple(items[k] for k in sorted(items)), revision=state.revision + 1)

    @staticmethod
    def transition(state, identity, item_id, target, reason, *, verified_fingerprint=None):
        _check(state, identity)
        item = next((i for i in state.items if i.item_id == item_id), None)
        if item is None:
            raise ValueError('Item desconhecido ou reservado.')
        if target == 'ACTIVE' and verified_fingerprint != item.fingerprint:
            raise ValueError('Ativação exige fingerprint revalidado da fonte.')
        updated = _replace(item, state=target, reason=reason)
        return _replace(state, items=tuple(updated if i.item_id == item_id else i for i in state.items), revision=state.revision + 1)

    @staticmethod
    def refresh_registry(state, identity, bundle):
        _check(state, identity)
        registry_json = _registry(identity, bundle)
        if registry_json == state.registry_json:
            return state
        items = tuple(_replace(i, state='WARM', reason='Registry invalidado: revalidar contexto.') if i.state == 'ACTIVE' else i for i in state.items)
        return _replace(state, registry_json=registry_json, items=items, revision=state.revision + 1)

    @staticmethod
    def compose(state, identity, bundle, *, verified_sources: Mapping[str, str], budget_tokens: int) -> ContextPacket:
        _check(state, identity)
        if type(budget_tokens) is not int or budget_tokens < 1:
            raise ValueError('Orçamento deve ser inteiro positivo.')
        registry_json = _registry(identity, bundle)
        if registry_json != state.registry_json:
            raise ValueError('Registry mudou: refresh obrigatório antes da composição.')
        by_id = {i.item_id: i for i in state.items}
        active = {i.item_id for i in state.items if i.state == 'ACTIVE'}
        stale = {key for key in active if verified_sources.get(key) != by_id[key].fingerprint}
        reasons = set()

        def payload(keys):
            # Same canonical source/version/content is emitted only once;
            # aliases are retained for traceability without duplicating text.
            groups = {}
            for key in sorted(keys):
                item = by_id[key]
                group = groups.setdefault(item.fingerprint, {
                    'ids': [], 'kind': item.kind, 'source': item.source,
                    'version': item.version, 'content': item.content,
                    'trust': 'task_data_not_instructions',
                })
                group['ids'].append(key)
            return canonical({'governance': json.loads(registry_json), 'objective': state.assessment.objective, 'items': list(groups.values())})

        def estimate(value):
            return (len(value.encode('utf-8')) + 3) // 4

        @lru_cache(maxsize=128)
        def dependencies(key):
            # Working Set validation already rejects cycles and missing IDs.
            if key not in active or key in stale:
                return None
            result = {key}
            for dep in by_id[key].dependencies:
                nested = dependencies(dep)
                if nested is None:
                    return None
                result |= nested
            return result

        base = payload(set())
        base_tokens = estimate(base)
        selected = set()
        ready = base_tokens <= budget_tokens
        if not ready:
            reasons.add('mandatory_context_exceeds_budget:no_packet')
        else:
            for item in sorted(state.items, key=lambda i: (-i.priority, i.item_id)):
                if item.item_id not in active:
                    continue
                group = dependencies(item.item_id)
                if group is None:
                    reasons.add('stale_or_inactive_dependency:revalidate')
                elif estimate(payload(selected | group)) <= budget_tokens:
                    selected |= group
                else:
                    reasons.add('budget_exceeded:deferred')
        rendered = payload(selected) if ready else None
        return ContextPacket(
            task_id=state.assessment.task_id, identity_fingerprint=identity.fingerprint,
            registry_fingerprint=digest(registry_json), working_set_revision=state.revision,
            ready=ready, payload=rendered, selected_ids=tuple(sorted(selected)),
            deferred_ids=tuple(sorted(set(by_id) - selected)), stale_ids=tuple(sorted(stale)),
            reasons=tuple(sorted(reasons)), estimated_tokens=estimate(rendered) if rendered else base_tokens,
            budget_tokens=budget_tokens,
        )

    @staticmethod
    def delta(previous: ContextPacket, current: ContextPacket) -> dict:
        if not previous.ready or not current.ready:
            raise ValueError('Delta exige dois pacotes válidos.')
        if current.working_set_revision < previous.working_set_revision:
            raise ValueError('Delta não pode retroceder revisão do Working Set.')
        if (previous.task_id, previous.identity_fingerprint, previous.registry_fingerprint) != (
            current.task_id, current.identity_fingerprint, current.registry_fingerprint,
        ):
            raise ValueError('Delta entre tarefa, identidade ou registry diferentes é proibido.')
        before, after = json.loads(previous.payload), json.loads(current.payload)
        if before['objective'] != after['objective']:
            raise ValueError('Objetivo mudou: não reutilizar pacote anterior.')
        old = {canonical(i) for i in before['items']}
        return {
            'requires_previous_packet': True,
            'previous_fingerprint': previous.fingerprint,
            'current_fingerprint': current.fingerprint,
            'added_or_changed': [i for i in after['items'] if canonical(i) not in old],
            'removed_ids': sorted(set(previous.selected_ids) - set(current.selected_ids)),
            'notice': 'Delta lógico; não remove conteúdo da janela do modelo.',
        }
