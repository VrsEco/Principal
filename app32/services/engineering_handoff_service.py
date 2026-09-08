"""Reviewed, reference-only local handoffs. Hashes detect corruption, not authorship."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Literal
from pydantic import Field

from src.intelligence.engineering_assessment import AssessmentModel
from src.intelligence.engineering_context import ContextIdentity, canonical, digest
from services.engineering_session_service import validate_packet


class HandoffReference(AssessmentModel):
    item_id: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=400)
    version: str = Field(min_length=1, max_length=120)
    fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')


class EngineeringHandoff(AssessmentModel):
    schema_version: Literal['engineering.handoff.v1'] = 'engineering.handoff.v1'
    identity: ContextIdentity
    task_id: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=3, max_length=4000)
    summary: str = Field(min_length=3, max_length=1200)
    decisions: tuple[str, ...] = Field(default=(), max_length=12)
    test_evidence: tuple[str, ...] = Field(default=(), max_length=12)
    pending: tuple[str, ...] = Field(default=(), max_length=12)
    registry_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    references: tuple[HandoffReference, ...] = Field(default=(), max_length=128)
    reviewed_for_export: Literal[True]
    execution_status: Literal['not_resumed'] = 'not_resumed'


def _safe(handoff):
    text = canonical(handoff.model_dump(mode='json'))
    if len(text.encode('utf-8')) > 32768:
        raise ValueError('Handoff excede 32 KiB.')
    if re.search(r'-----BEGIN .*PRIVATE KEY|\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{12,}|(?:password|senha|api_key|secret|token)\s*[=:]\s*\S+', text, re.I):
        raise ValueError('Possível segredo; revisar exportação.')
    return text


class EngineeringHandoffService:
    @staticmethod
    def create(state, packet, *, summary, reviewed_for_export, decisions=(), test_evidence=(), pending=()):
        validate_packet(state, packet)
        if not packet.ready:
            raise ValueError('Compor pacote válido antes de exportar referências.')
        if reviewed_for_export is not True:
            raise ValueError('Revisão explícita necessária antes da exportação.')
        selected = set(packet.selected_ids)
        handoff = EngineeringHandoff(
            identity=state.identity, task_id=state.assessment.task_id, objective=state.assessment.objective,
            summary=summary, decisions=decisions, test_evidence=test_evidence, pending=pending,
            registry_fingerprint=packet.registry_fingerprint, reviewed_for_export=True,
            references=tuple(HandoffReference(item_id=i.item_id,source=i.source,version=i.version,fingerprint=i.fingerprint)
                             for i in state.items if i.item_id in selected),
        )
        _safe(handoff)
        return handoff

    @staticmethod
    def _path(root: Path, name: str, *, create=False):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.json', name):
            raise ValueError('Nome de handoff inválido.')
        root = root.resolve(strict=True)
        folder = root / '.ai' / 'handoffs'
        for path in (root / '.ai', folder, folder / name):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('Path de handoff fora do repositório ou simbólico.')
        if create:
            folder.mkdir(parents=True, exist_ok=True)
        return folder / name

    @classmethod
    def save(cls, root, name, handoff):
        if handoff.identity.context_scope != 'repository':
            raise ValueError('Persistência empresarial exige armazenamento autenticado; não disponível.')
        text = _safe(handoff)
        path = cls._path(Path(root), name, create=True)
        envelope = canonical({'checksum':digest(text),'handoff':json.loads(text)})
        with path.open('x', encoding='utf-8') as file:
            file.write(envelope)
        return path

    @classmethod
    def load(cls, root, name, *, identity, registry_fingerprint, verified_sources):
        path = cls._path(Path(root), name)
        with path.open('rb') as file:
            raw = file.read(40001)
        if len(raw)>40000:
            raise ValueError('Arquivo de handoff excessivo.')
        envelope = json.loads(raw)
        if not isinstance(envelope,dict) or set(envelope) != {'checksum','handoff'}:
            raise ValueError('Envelope inválido.')
        handoff = EngineeringHandoff.model_validate(envelope['handoff'])
        if digest(_safe(handoff)) != envelope['checksum']:
            raise ValueError('Checksum divergente.')
        if handoff.identity != identity or handoff.registry_fingerprint != registry_fingerprint:
            raise ValueError('Identidade/registry mudou; não reutilizar handoff.')
        if any(verified_sources.get(r.item_id) != r.fingerprint for r in handoff.references):
            raise ValueError('Fonte ausente/obsoleta; revalidar antes de retomar.')
        return handoff  # Data only: no execution, policy changes or task creation.
