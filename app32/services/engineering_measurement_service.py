"""Compare caller-declared matched runs; no collection, storage or billing claims."""
from typing import Literal
from pydantic import Field, StrictInt
from src.intelligence.engineering_assessment import AssessmentModel


class EngineeringMeasurement(AssessmentModel):
    workload_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    identity_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    evaluation_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    runtime_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    variant: Literal['baseline','candidate']
    quality: Literal['pass','fail','unknown'] = 'unknown'
    estimated_context_tokens: StrictInt | None = Field(default=None,ge=0,le=10**15)
    estimate_method: Literal['utf8_bytes_div4_ceil_v1'] = 'utf8_bytes_div4_ceil_v1'
    usage_source: Literal['provider_reported','unknown'] = 'unknown'
    input_tokens: StrictInt | None = Field(default=None,ge=0,le=10**15)
    output_tokens: StrictInt | None = Field(default=None,ge=0,le=10**15)
    duration_ms: StrictInt | None = Field(default=None,ge=0,le=10**15)


class EngineeringMeasurementService:
    @staticmethod
    def compare(baseline: EngineeringMeasurement,candidate: EngineeringMeasurement):
        if baseline.variant!='baseline' or candidate.variant!='candidate':
            raise ValueError('Expected baseline/candidate pair')
        keys=('workload_fingerprint','identity_fingerprint','evaluation_fingerprint','runtime_fingerprint')
        if any(getattr(baseline,key)!=getattr(candidate,key) for key in keys):
            raise ValueError('Runs are not comparable')
        quality=baseline.quality==candidate.quality=='pass'
        def metric(before,after):
            if before is None or after is None:
                return {'baseline':before,'candidate':after,'reduction_percent':None}
            return {'baseline':before,'candidate':after,
                    'reduction_percent':round((before-after)*100/before,4) if before>0 and quality else None}
        actual=baseline.usage_source==candidate.usage_source=='provider_reported'
        def total(run):
            return run.input_tokens+run.output_tokens if run.input_tokens is not None and run.output_tokens is not None else None
        return {'status':'matched_declared_runs' if quality else 'quality_not_established',
            'evidence_verified':False,'quality_preserved_declared':quality,
            'estimated_context':metric(baseline.estimated_context_tokens,candidate.estimated_context_tokens),
            'reported_total_tokens':metric(total(baseline) if actual else None,total(candidate) if actual else None),
            'duration_ms':metric(baseline.duration_ms,candidate.duration_ms),
            'cost_savings':None,'causal_savings_proven':False,
            'limitations':['single_pair_not_statistical_evidence','declared_metrics_not_authenticated',
                           'estimated_context_is_not_provider_usage','token_totals_are_not_billing_cost']}
