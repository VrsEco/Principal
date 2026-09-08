"""Local squad status/context/why/model/handoff, plus decide/resume; JSON stdin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from pydantic import Field, StrictBool, StrictInt
from src.intelligence.engineering_assessment import AssessmentModel, EngineeringTaskRequest
from src.intelligence.engineering_context import ContextIdentity, ContextItem
from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from services.engineering_context_governor_service import EngineeringContextGovernorService as Governor
from services.engineering_session_service import EngineeringSessionService as Sessions
from services.engineering_handoff_service import EngineeringHandoffService as Handoffs
from services.engineering_quality_gate_service import EngineeringQualityGateService as QualityGate, QualityEvidence, QualityPolicy
from services.engineering_model_broker_service import EngineeringModelBrokerService as ModelBroker, ModelPreference


class Request(AssessmentModel):
    task: EngineeringTaskRequest
    identity: ContextIdentity
    items: tuple[ContextItem, ...] = Field(default=(), max_length=128)
    budget_tokens: StrictInt = Field(default=16000, gt=0)
    next_task: EngineeringTaskRequest | None = None
    depends_on: tuple[str, ...] = ()
    name: str | None = None
    summary: str | None = None
    reviewed_for_export: StrictBool = False
    decisions: tuple[str, ...] = ()
    test_evidence: tuple[str, ...] = ()
    pending: tuple[str, ...] = ()
    quality_evidence: QualityEvidence | None = None
    quality_target: Literal['local', 'operational'] = 'local'
    quality_policy: QualityPolicy = Field(default_factory=QualityPolicy)
    broker_preference: ModelPreference = Field(default_factory=ModelPreference)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['status','context','why','model','handoff','decide','resume','qa'])
    args=parser.parse_args(argv)
    try:
        raw=sys.stdin.read(1048577)
        if len(raw)>1048576:
            raise ValueError('Input too large')
        request=Request.model_validate_json(raw)
        if request.identity.context_scope!='repository' or request.task.context_scope!='repository':
            raise ValueError('CLI has no authenticated company adapter')
        from flask import has_app_context
        if has_app_context():
            raise ValueError('No application context allowed')
        from services.instruction_registry_service import InstructionRegistryService
        bundle=InstructionRegistryService.resolve_bundle(runtime_profile='engineering',harness_key=request.identity.harness_key)
        state=Governor.create(Router.assess(request.task),request.identity,bundle)
        for item in request.items:
            state=Governor.upsert(state,request.identity,item)
        verified={i.item_id:i.fingerprint for i in state.items}
        packet=Governor.compose(state,request.identity,bundle,verified_sources=verified,budget_tokens=request.budget_tokens)
        binding={'task_id':state.assessment.task_id,'identity_fingerprint':state.identity.fingerprint,'packet_fingerprint':packet.fingerprint}
        quality=None
        if request.quality_evidence is not None or args.command=='qa':
            if args.command not in ('qa','status','why'):
                raise ValueError('Quality evidence only accepted by QA inspection commands')
            evidence=request.quality_evidence or QualityEvidence(**binding)
            quality=QualityGate.evaluate(state,packet,evidence,target=request.quality_target,policy=request.quality_policy).model_dump(mode='json')
        if args.command=='model':
            data=ModelBroker.recommend(state,packet,request.broker_preference).model_dump(mode='json')
        elif args.command=='qa':
            data={'quality_gate':quality,'evidence_binding':binding}
        elif args.command=='decide':
            if request.next_task is None:
                raise ValueError('next_task required')
            data=Sessions.decide(state,Router.assess(request.next_task),request.identity,depends_on=request.depends_on,packet=packet).model_dump(mode='json')
        elif args.command=='handoff':
            handoff=Handoffs.create(state,packet,summary=request.summary,reviewed_for_export=request.reviewed_for_export,
                decisions=request.decisions,test_evidence=request.test_evidence,pending=request.pending)
            path=Handoffs.save(APP_ROOT,request.name or '',handoff)
            data={'path':str(path),'status':'checkpoint_saved_not_resumed'}
        elif args.command=='resume':
            handoff=Handoffs.load(APP_ROOT,request.name or '',identity=request.identity,
                registry_fingerprint=packet.registry_fingerprint,verified_sources=verified)
            if handoff.task_id != state.assessment.task_id or handoff.objective != state.assessment.objective:
                raise ValueError('Resume task mismatch')
            data={'handoff':handoff.model_dump(mode='json'),'status':'validated_for_human_review_not_executed'}
        else:
            data=Sessions.inspect(args.command,state,packet)
            if args.command=='context':
                data['evidence_binding']=binding
            if args.command in ('status','why'):
                data['quality_gate']=quality
    except (ValueError,OSError,TypeError):
        print(json.dumps({'success':False,'error':'invalid_or_unavailable_local_session_request'}))
        return 2
    print(json.dumps({'success':True,'data':data,'freshness_mode':'supplied_snapshots_not_disk_verified'},ensure_ascii=True))
    if args.command=='qa':
        return {'blocked':3,'remote_validation_pending':4}.get(quality['status'],0)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
