"""Advisory QA over caller-supplied evidence, never operational authorization."""
from typing import Literal
from pydantic import Field, StrictInt
from src.intelligence.engineering_assessment import AssessmentModel
from services.engineering_session_service import validate_packet

Check = Literal['pass', 'fail', 'unknown']
Failure = Literal['none', 'implementation', 'requirement', 'environment', 'test', 'security', 'uncertain_mutation']


class QualityEvidence(AssessmentModel):
    task_id: str = Field(min_length=1, max_length=120)
    identity_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    packet_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    requirements: Check = 'unknown'
    limited_diff: Check = 'unknown'
    tests: Check = 'unknown'
    regression: Check = 'unknown'
    documentation: Check = 'unknown'
    tenant_policy: Check = 'unknown'
    architecture: Check = 'unknown'
    database_review: Check = 'unknown'
    operational: Check = 'unknown'
    evidence_refs: tuple[str, ...] = Field(default=(), max_length=32)
    failure: Failure = 'none'
    retries_used: StrictInt = Field(default=0, ge=0)
    escalations_used: StrictInt = Field(default=0, ge=0)


class QualityPolicy(AssessmentModel):
    max_retries: StrictInt = Field(default=2, ge=0, le=5)
    max_escalations: StrictInt = Field(default=1, ge=0, le=3)


class QualityDecision(AssessmentModel):
    status: Literal['blocked', 'local_validated', 'remote_validation_pending', 'done']
    action: str
    reasons: tuple[str, ...]
    automatic_execution: Literal[False] = False
    evidence_verified: Literal[False] = False
    provider_escalation: Literal[False] = False


class EngineeringQualityGateService:
    @staticmethod
    def evaluate(state, packet, evidence: QualityEvidence, *,
                 target: Literal['local', 'operational'] = 'local', policy: QualityPolicy | None = None):
        validate_packet(state, packet)
        if target not in ('local', 'operational'):
            raise ValueError('Alvo inválido.')
        if (evidence.task_id, evidence.identity_fingerprint, evidence.packet_fingerprint) != (
            state.assessment.task_id, state.identity.fingerprint, packet.fingerprint,
        ):
            raise ValueError('Evidência de outra tarefa, identidade ou pacote.')
        policy = policy or QualityPolicy()
        def result(status, action, *reasons):
            return QualityDecision(status=status, action=action, reasons=reasons)
        if evidence.failure in ('security', 'uncertain_mutation') or evidence.tenant_policy == 'fail':
            return result('blocked', 'stop_and_request_human_review', 'security_or_uncertain_effect')
        if evidence.failure != 'none':
            actions = {'requirement':'clarify_with_coordinator', 'environment':'repair_environment',
                       'test':'diagnose_test_vs_regression'}
            if evidence.failure in actions:
                return result('blocked', actions[evidence.failure], evidence.failure)
            if evidence.retries_used < policy.max_retries:
                return result('blocked', 'diagnose_before_manual_retry', 'implementation_failure')
            if evidence.escalations_used < policy.max_escalations:
                return result('blocked', 'request_specialist_review', 'retry_limit_reached')
            return result('blocked', 'stop_and_request_human_review', 'all_limits_reached')
        if state.assessment.requires_clarification:
            return result('blocked', 'clarify_with_coordinator', 'assessment_unresolved')
        if not packet.ready or packet.stale_ids or packet.deferred_ids:
            return result('blocked', 'review_context', 'context_incomplete')
        required = ['requirements', 'limited_diff', 'tests', 'regression', 'documentation']
        if state.identity.context_scope == 'company' or state.assessment.requires_architect:
            required += ['tenant_policy']
        if state.assessment.requires_architect:
            required += ['architecture']
        if state.assessment.requires_dba:
            required += ['database_review']
        missing = tuple(name for name in required if getattr(evidence, name) != 'pass')
        if missing or not evidence.evidence_refs or any(not ref.strip() or len(ref)>400 for ref in evidence.evidence_refs):
            return result('blocked', 'collect_or_correct_evidence', *(missing or ('evidence_refs_missing_or_invalid',)))
        if target == 'local':
            return result('local_validated', 'review_local_result', 'declared_local_checks_passed')
        if evidence.operational == 'fail':
            return result('blocked', 'diagnose_operational_failure', 'operational_failed')
        # This adapter cannot authenticate or fetch MCP evidence, even if caller says pass.
        return result('remote_validation_pending', 'request_authenticated_operational_validation',
                      'operational_evidence_not_independently_verified')
