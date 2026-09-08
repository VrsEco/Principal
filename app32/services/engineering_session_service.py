"""Logical session lifecycle. No provider calls, task creation or native compact."""
from __future__ import annotations

from typing import Literal

from src.intelligence.engineering_assessment import AssessmentModel, TaskAssessment
from src.intelligence.engineering_context import ContextIdentity, ContextPacket, EngineeringWorkingSet, digest


class SessionDecision(AssessmentModel):
    policy: Literal['SAME', 'EXTEND', 'ROTATE']
    reason: str
    carries_context: bool
    automatic_session_creation: Literal[False] = False


def validate_packet(state: EngineeringWorkingSet, packet: ContextPacket):
    if (packet.task_id, packet.identity_fingerprint, packet.registry_fingerprint, packet.working_set_revision) != (
        state.assessment.task_id, state.identity.fingerprint, digest(state.registry_json), state.revision,
    ):
        raise ValueError('Pacote não corresponde à revisão/escopo do Working Set.')


class EngineeringSessionService:
    @staticmethod
    def decide(state: EngineeringWorkingSet, next_task: TaskAssessment, identity: ContextIdentity,
               *, depends_on: tuple[str, ...] = (), packet: ContextPacket | None = None) -> SessionDecision:
        if (next_task.company_id, next_task.context_scope) != (identity.company_id, identity.context_scope):
            raise ValueError('Nova tarefa e identidade incompatíveis.')
        if identity != state.identity:
            return SessionDecision(policy='ROTATE', reason='identity_changed:no_context_transfer', carries_context=False)
        if packet is not None:
            validate_packet(state, packet)
            if not packet.ready or any('budget' in reason for reason in packet.reasons):
                return SessionDecision(policy='ROTATE', reason='estimated_budget_pressure', carries_context=False)
        old = state.assessment
        if next_task.task_id == old.task_id and next_task.objective == old.objective and next_task.context_domains == old.context_domains:
            return SessionDecision(policy='SAME', reason='same_task_objective_and_domains', carries_context=True)
        if old.task_id in depends_on and next_task.task_id != old.task_id:
            return SessionDecision(policy='EXTEND', reason='explicit_dependency:select_only_required_delta', carries_context=True)
        return SessionDecision(policy='ROTATE', reason='independent_or_changed_objective', carries_context=False)

    @staticmethod
    def inspect(command: str, state: EngineeringWorkingSet, packet: ContextPacket | None = None) -> dict:
        if packet is not None:
            validate_packet(state, packet)
        if command == 'status':
            return {'task_id':state.assessment.task_id, 'revision':state.revision,
                    'specialists':state.assessment.specialists, 'status':'local_advisory_not_executed',
                    'requires_clarification':state.assessment.requires_clarification,
                    'tests':'unknown', 'remote_validation':'not_performed'}
        if command == 'context':
            return {'states':{s:[i.item_id for i in state.items if i.state == s] for s in ('ACTIVE','WARM','DROPPED')},
                    'packet':packet.telemetry() if packet else None,
                    'native_context_usage':None}
        if command == 'why':
            return {'routing_reasons':state.assessment.reasons,'unknowns':state.assessment.unknowns,
                    'context_reasons':packet.reasons if packet else (),
                    'deferred_ids':packet.deferred_ids if packet else ()}
        if command == 'model':
            return {'model':None,'provider':None,'reason':'runtime_model_not_observed',
                    'automatic_switch':False,'fallback':'manual_selection_in_runtime'}
        raise ValueError('Consulta não suportada; handoff exige exportação revisada.')
