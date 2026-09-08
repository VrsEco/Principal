"""Provider-neutral logical recommendation. Manual runtime adapter only."""
from typing import Literal
from queue import Empty
from pydantic import Field, StrictInt
from src.intelligence.engineering_assessment import AssessmentModel
from services.engineering_quality_gate_service import Failure
from services.engineering_session_service import validate_packet
from services.engineering_runtime_catalog_service import read_codex_catalog

Profile = Literal['ECONOMY', 'STANDARD', 'DEEP']


class ModelPreference(AssessmentModel):
    profile: Profile | None = None
    failure: Failure = 'none'
    retries_used: StrictInt = Field(default=0, ge=0, le=100)


class ModelRecommendation(AssessmentModel):
    profile: Profile | None
    suggested_profile: Profile | None
    reason: str
    user_preference_preserved: bool = False
    preference_risk_warning: bool = False
    provider: None = None
    model: None = None
    effort: None = None
    automatic_switch: Literal[False] = False
    capabilities_verified: Literal[False] = False
    fallback: Literal['manual_selection_in_runtime'] = 'manual_selection_in_runtime'


class RuntimeSelection(AssessmentModel):
    requested_model: str = Field(min_length=1, max_length=200)
    requested_effort: str | None = Field(default=None, min_length=1, max_length=40)


class RuntimeSelectionResult(AssessmentModel):
    recommendation: ModelRecommendation
    selection: RuntimeSelection
    status: Literal['listed_for_manual_selection', 'manual_fallback', 'blocked']
    reason: str
    catalog_observed_at: str | None = None
    catalog_match: bool = False
    generation_access_verified: Literal[False] = False
    automatic_switch: Literal[False] = False


class EngineeringModelBrokerService:
    @classmethod
    def resolve_selection(cls, state, packet, selection: RuntimeSelection, *, rpc,
                          preference: ModelPreference | None = None):
        """Caller supplies a fresh, trusted RPC connection, never a saved catalog.

        Listing is not QA approval, generation authorization, or model observation.
        No mapping from profile to commercial model is inferred.
        """
        recommendation=cls.recommend(state,packet,preference)
        def result(status, reason, **kwargs):
            return RuntimeSelectionResult(recommendation=recommendation,selection=selection,
                status=status,reason=reason,**kwargs)
        if state.identity.context_scope != 'repository':
            return result('blocked','authenticated_company_adapter_required')
        if recommendation.suggested_profile is None:
            return result('blocked','resolve_task_or_context_before_catalog')
        try:
            catalog=read_codex_catalog(rpc)
        except (ValueError,OSError,Empty):
            return result('manual_fallback','runtime_catalog_unavailable')
        observed={'catalog_observed_at':catalog['observed_at']}
        entry=next((entry for entry in catalog['models'] if entry['model']==selection.requested_model),None)
        if entry is None:
            return result('manual_fallback','requested_model_not_listed',**observed)
        if selection.requested_effort is not None and selection.requested_effort not in entry['supported_efforts']:
            return result('manual_fallback','requested_effort_not_listed',**observed)
        return result('listed_for_manual_selection','explicit_choice_matches_observed_catalog',catalog_match=True,**observed)

    @staticmethod
    def recommend(state, packet, preference: ModelPreference | None = None):
        validate_packet(state, packet)
        preference = preference or ModelPreference()
        task = state.assessment
        blocked = None
        if preference.failure in ('security', 'uncertain_mutation'):
            blocked = 'human_review_before_model_selection'
        elif preference.failure in ('environment', 'requirement', 'test'):
            blocked = 'diagnose_cause_not_model_capacity'
        elif task.requires_clarification:
            blocked = 'clarify_task_before_model_selection'
        elif not packet.ready or packet.stale_ids or packet.deferred_ids:
            blocked = 'repair_context_before_model_selection'
        if blocked:
            return ModelRecommendation(profile=preference.profile, suggested_profile=None, reason=blocked,
                                       user_preference_preserved=preference.profile is not None)
        if task.risk == 'high' or task.complexity == 'high' or task.requires_architect or task.requires_dba:
            suggested, reason = 'DEEP', 'risk_or_specialist_review'
        elif preference.failure == 'implementation' and preference.retries_used >= 2:
            suggested, reason = 'DEEP', 'implementation_diagnosis_requires_review'
        elif task.task_type == 'documentation' and task.risk == 'low' and task.complexity == 'low':
            suggested, reason = 'ECONOMY', 'bounded_low_risk_documentation'
        else:
            suggested, reason = 'STANDARD', 'default_engineering_work'
        ranks = {'ECONOMY':0, 'STANDARD':1, 'DEEP':2}
        chosen = preference.profile or suggested
        return ModelRecommendation(profile=chosen, suggested_profile=suggested, reason=reason,
            user_preference_preserved=preference.profile is not None,
            preference_risk_warning=ranks[chosen] < ranks[suggested])
