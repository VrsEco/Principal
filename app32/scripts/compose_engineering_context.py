"""Compose a local repository packet from explicit snapshots; never read files."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import Field, StrictInt
from src.intelligence.engineering_assessment import AssessmentModel, EngineeringTaskRequest
from src.intelligence.engineering_context import ContextIdentity, ContextItem
from services.engineering_task_router_service import EngineeringTaskRouterService
from services.engineering_context_governor_service import EngineeringContextGovernorService as Governor


class ComposeRequest(AssessmentModel):
    task: EngineeringTaskRequest
    identity: ContextIdentity
    items: tuple[ContextItem, ...] = Field(default=(), max_length=128)
    budget_tokens: StrictInt = Field(default=16000, gt=0)


def main() -> int:
    try:
        raw = sys.stdin.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('Request too large')
        request = ComposeRequest.model_validate_json(raw)
        # This executable has no authenticated operational adapter. Company
        # scopes are available only via the service with caller-verified data.
        if request.identity.context_scope != 'repository' or request.task.context_scope != 'repository':
            raise ValueError('Only local repository snapshots are supported')
        from flask import has_app_context
        if has_app_context():
            raise ValueError('Do not execute this local CLI inside an application')
        from services.instruction_registry_service import InstructionRegistryService
        bundle = InstructionRegistryService.resolve_bundle(
            runtime_profile='engineering', harness_key=request.identity.harness_key,
        )
        assessment = EngineeringTaskRouterService.assess(request.task)
        state = Governor.create(assessment, request.identity, bundle)
        # References with dependencies must be supplied after their dependencies.
        for item in request.items:
            state = Governor.upsert(state, request.identity, item)
        packet = Governor.compose(state, request.identity, bundle,
            verified_sources={i.item_id: i.fingerprint for i in request.items},
            budget_tokens=request.budget_tokens)
    except ValueError:
        print(json.dumps({'success':False, 'error':'invalid_context_request'}))
        return 2
    print(json.dumps({'success':packet.ready, 'packet':packet.model_dump(mode='json'), 'telemetry':packet.telemetry(),
                      'freshness_mode':'supplied_snapshots_not_disk_verified'}, ensure_ascii=True))
    return 0 if packet.ready else 3


if __name__ == '__main__':
    raise SystemExit(main())
